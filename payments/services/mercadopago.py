"""Cliente aislado para Mercado Pago Checkout Pro."""

import hashlib
import hmac
import logging
import threading
from urllib.parse import urlencode, urlparse

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from pedidos.models import Entrega, Pago, Pedido

try:
    import mercadopago
except ImportError:  # Se vuelve un error de configuración claro hasta instalar el SDK.
    mercadopago = None

logger = logging.getLogger(__name__)
TIMEOUT_SECONDS = 20


class MercadoPagoError(Exception):
    pass


class _ClienteHTTPMercadoPagoDirecto:
    """Adaptador del SDK que evita un proxy local inválido del entorno.

    El SDK oficial usa ``requests.Session`` y, por defecto, hereda las
    variables HTTP(S)_PROXY. En desarrollo este proyecto tiene un proxy en
    127.0.0.1:9 que no está escuchando; por eso las preferencias no llegaban
    a Mercado Pago. Se desactiva solo para este proveedor, sin afectar Stripe
    ni el resto de las integraciones.
    """

    def __new__(cls):
        # La clase base se importa de forma diferida para conservar el error
        # claro de configuración cuando el SDK no está instalado.
        import requests
        from mercadopago.http import HttpClient

        class ClienteDirecto(HttpClient):
            def request(self, method, url, maxretries=None, **kwargs):
                kwargs.setdefault("timeout", TIMEOUT_SECONDS)
                with requests.Session() as session:
                    session.trust_env = False
                    api_result = session.request(method, url, **kwargs)
                response = {"status": api_result.status_code, "response": None}
                if api_result.status_code != 204 and api_result.content:
                    try:
                        response["response"] = api_result.json()
                    except ValueError:
                        logger.warning("Mercado Pago devolvió una respuesta no JSON.")
                return response

        return ClienteDirecto()


def _cliente():
    token = getattr(settings, "MERCADOPAGO_ACCESS_TOKEN", "")
    if not token:
        raise MercadoPagoError("Falta configurar MERCADOPAGO_ACCESS_TOKEN.")
    if mercadopago is None:
        raise MercadoPagoError("Falta instalar el SDK oficial mercadopago.")
    return mercadopago.SDK(token, http_client=_ClienteHTTPMercadoPagoDirecto())


def _ejecutar_con_timeout(funcion):
    """Ejecuta el SDK sin dejar que una conexión bloquee el request Django."""
    resultado, error = {}, {}

    def ejecutar():
        try:
            resultado["valor"] = funcion()
        except Exception as exc:  # El SDK puede lanzar varias excepciones propias.
            error["excepcion"] = exc

    hilo = threading.Thread(target=ejecutar, daemon=True)
    hilo.start()
    hilo.join(TIMEOUT_SECONDS)
    if hilo.is_alive():
        logger.warning("Mercado Pago agotó el tiempo de espera de %ss", TIMEOUT_SECONDS)
        raise MercadoPagoError("Mercado Pago no respondió a tiempo.")
    if "excepcion" in error:
        logger.exception("Error al comunicarse con Mercado Pago", exc_info=error["excepcion"])
        raise MercadoPagoError("No fue posible comunicarse con Mercado Pago.") from error["excepcion"]
    return resultado["valor"]


def crear_preferencia(pedido, request):
    """Crea una preferencia Checkout Pro para un pedido ya persistido."""
    items = [
        {
            "id": str(item.id_producto_id),
            "title": item.id_producto.nombre,
            "quantity": int(item.cantidad),
            "currency_id": "MXN",
            "unit_price": float(item.precio_unitario),
        }
        for item in pedido.items.select_related("id_producto")
    ]
    if pedido.costo_envio:
        items.append(
            {
                "title": "Envío",
                "quantity": 1,
                "currency_id": "MXN",
                "unit_price": float(pedido.costo_envio),
            }
        )
    if not items:
        raise MercadoPagoError("El pedido no tiene artículos para cobrar.")

    # Mercado Pago no garantiza incluir external_reference en el retorno del
    # navegador. El identificador aquí es solo para mostrar el pedido; el
    # webhook siempre confirma el pago contra la API de Mercado Pago.
    retorno_path = reverse("payments:mercadopago_retorno")
    retorno = request.build_absolute_uri(
        f"{retorno_path}?{urlencode({'pedido_id': pedido.id_pedido})}"
    )
    webhook = request.build_absolute_uri(reverse("payments:webhook"))
    preferencia = {
        "items": items,
        "payer": {"email": pedido.id_usuario.email},
        "external_reference": str(pedido.id_pedido),
        "notification_url": webhook,
        "back_urls": {"success": retorno, "failure": retorno, "pending": retorno},
        "metadata": {"pedido_id": pedido.id_pedido},
    }
    # Mercado Pago solo acepta auto_return con una URL success pública HTTPS.
    # En desarrollo (127.0.0.1/http) se omite: el Checkout Pro funciona igual
    # y la confirmación real continúa dependiendo del webhook.
    if urlparse(retorno).scheme == "https":
        preferencia["auto_return"] = "approved"
    respuesta = _ejecutar_con_timeout(lambda: _cliente().preference().create(preferencia))
    if respuesta.get("status") not in (200, 201) or not respuesta.get("response", {}).get("init_point"):
        logger.error("Mercado Pago rechazó preferencia: %s", respuesta)
        raise MercadoPagoError("Mercado Pago no pudo crear la preferencia de pago.")
    return respuesta["response"]


def consultar_pago(payment_id):
    """Consulta el pago en Mercado Pago; nunca confía en los datos del webhook."""
    respuesta = _ejecutar_con_timeout(lambda: _cliente().payment().get(str(payment_id)))
    if respuesta.get("status") != 200 or not respuesta.get("response"):
        raise MercadoPagoError("No fue posible validar el pago en Mercado Pago.")
    return respuesta["response"]


def _consultar_orden(merchant_order_id):
    """Consulta una orden de Mercado Pago antes de usar sus pagos asociados."""
    respuesta = _ejecutar_con_timeout(
        lambda: _cliente().merchant_order().get(str(merchant_order_id))
    )
    if respuesta.get("status") != 200 or not respuesta.get("response"):
        raise MercadoPagoError("No fue posible validar la orden en Mercado Pago.")
    return respuesta["response"]


def _validar_firma(payload, headers, query):
    secreto = getattr(settings, "MERCADOPAGO_WEBHOOK_SECRET", "")
    if not secreto:
        logger.warning("MERCADOPAGO_WEBHOOK_SECRET no está configurado; no se valida firma en desarrollo.")
        return
    firma = headers.get("x-signature", "")
    request_id = headers.get("x-request-id", "")
    partes = dict(part.split("=", 1) for part in firma.split(",") if "=" in part)
    ts, v1 = partes.get("ts"), partes.get("v1")
    data_id = str((payload.get("data") or {}).get("id") or query.get("data.id") or "")
    if not ts or not v1 or not data_id:
        raise MercadoPagoError("Firma de webhook incompleta.")
    manifest = f"id:{data_id};request-id:{request_id};ts:{ts};"
    esperado = hmac.new(secreto.encode(), manifest.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(esperado, v1):
        raise MercadoPagoError("Firma de webhook inválida.")


def _crear_envio_aprobado(pedido):
    entrega = getattr(pedido, "entrega", None)
    if not entrega or entrega.transportista == "Agrivale":
        return
    if entrega.tracking_number or entrega.numero_guia:
        return
    if not entrega.transportista or not entrega.servicio:
        logger.warning("Pedido %s pagado sin servicio de Envia seleccionado.", pedido.id_pedido)
        return
    try:
        from shipping.services.envia import EnviaAPIError, crear_envio

        crear_envio(pedido, entrega.transportista, entrega.servicio)
    except (EnviaAPIError, ValidationError):
        logger.exception("No se pudo generar la guía Envia del pedido %s", pedido.id_pedido)


def _payment_id_de_orden(merchant_order_id):
    """Obtiene un pago de la orden tras consultarla en la API oficial.

    Una orden puede tener más de un intento de pago. Se prioriza el aprobado
    para evitar que un intento fallido posterior cambie un pedido ya pagado.
    """
    orden = _consultar_orden(merchant_order_id)
    pagos = [p for p in orden.get("payments", []) if p.get("id")]
    if not pagos:
        logger.info("Orden Mercado Pago %s sin pagos todavía.", merchant_order_id)
        return None
    aprobado = next((p for p in pagos if p.get("status") == "approved"), None)
    return (aprobado or pagos[-1])["id"]


def _actualizar_desde_pago(payment_id):
    """Consulta y persiste un pago de forma idempotente."""
    datos = consultar_pago(payment_id)
    pedido_id = datos.get("external_reference")
    if not pedido_id:
        raise MercadoPagoError("El pago no está asociado a un pedido.")

    with transaction.atomic():
        pedido = Pedido.objects.select_for_update().filter(id_pedido=pedido_id).first()
        if not pedido:
            raise MercadoPagoError("No existe el pedido asociado al pago.")
        pago, _ = Pago.objects.select_for_update().get_or_create(
            id_pedido=pedido,
            defaults={"metodo": "mercadopago", "proveedor_pago": "mercadopago"},
        )
        estado = datos.get("status")

        # Un pago aprobado es definitivo para el pedido. Una notificación
        # tardía de otro intento no puede degradar su estado.
        if pago.estado == "pagado" and estado != "approved":
            return pedido, True

        pago.proveedor_pago = "mercadopago"
        pago.metodo = "mercadopago"
        pago.mercadopago_payment_id = str(datos["id"])
        pago.referencia_pago = str(datos["id"])
        if estado == "approved":
            if pago.estado != "pagado":
                pago.marcar_pagado(referencia=str(datos["id"]))
            pago.save(
                update_fields=[
                    "proveedor_pago", "metodo", "mercadopago_payment_id", "referencia_pago"
                ]
            )
            return pedido, True

        pago.estado = "fallido" if estado in {"rejected", "cancelled"} else "pendiente"
        pago.save(
            update_fields=[
                "proveedor_pago", "metodo", "mercadopago_payment_id",
                "referencia_pago", "estado",
            ]
        )
        return pedido, False


def procesar_webhook(payload, headers, query):
    """Valida eventos permitidos y actualiza el pago de forma idempotente."""
    _validar_firma(payload, headers, query)
    evento = payload.get("type") or query.get("type")
    accion = payload.get("action") or query.get("action", "")
    if evento == "merchant_order":
        orden_id = (payload.get("data") or {}).get("id") or query.get("data.id")
        if not orden_id:
            raise MercadoPagoError("Webhook sin identificador de orden.")
        payment_id = _payment_id_de_orden(orden_id)
        if not payment_id:
            return
    elif evento == "payment" and accion in {"payment.created", "payment.updated"}:
        payment_id = (payload.get("data") or {}).get("id") or query.get("data.id")
        if not payment_id:
            raise MercadoPagoError("Webhook sin identificador de pago.")
    else:
        raise MercadoPagoError("Evento de Mercado Pago no admitido.")
    pedido, aprobado = _actualizar_desde_pago(payment_id)
    if aprobado:
        _crear_envio_aprobado(pedido)
