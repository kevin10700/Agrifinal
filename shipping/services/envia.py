"""Cliente mock/local para la Shipping API (Sin dependencia de Envia.com)."""

from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction

from pedidos.models import Entrega


class EnviaAPIError(Exception):
    """Error controlado para mantener compatibilidad con las vistas."""

    def __init__(self, message, status_code=None, response_data=None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data


def validar_codigo_postal(codigo_postal):
    """Valida el código postal localmente sin llamar a la API de Envia."""
    cp_str = str(codigo_postal).strip() if codigo_postal else ""
    if not cp_str.isdigit() or len(cp_str) != 5:
        raise ValidationError({"codigo_postal": "Ingresa un código postal mexicano de 5 dígitos."})

    # Devuelve una estructura compatible sin depender de Envia Geocodes
    return {
        "codigo_postal": cp_str,
        "estado": "México",
        "estado_codigo": "MEX",
        "municipio": "Localidad Standard",
        "colonias": [],
    }


def _valor_decimal(value, field_name):
    try:
        value = Decimal(str(value))
    except (TypeError, ValueError, ArithmeticError) as exc:
        raise ValidationError({field_name: "Debe ser un número válido."}) from exc

    if value <= 0:
        return Decimal("1.0")

    return value


def cotizar_envio(origen, destino, paquete, transportista=None):
    """
    Simulación de cotización externa.
    Al estar desactivado Envia, retorna una lista vacía de opciones externas.
    La vista principal manejará el reparto local.
    """
    return {
        "opciones": [],
        "respuesta_json": {"detail": "Servicio de Envia.com desactivado. Usando reparto local."}
    }


def crear_envio(pedido, transportista, servicio):
    """Genera un registro local de entrega sin consumir la API de Envia."""
    if not transportista or not servicio:
        raise ValidationError("Transportista y servicio son obligatorios.")

    tracking_number = f"AGR-{pedido.id if hasattr(pedido, 'id') else '000'}"
    price = getattr(pedido, "costo_envio", Decimal("0.00")) or Decimal("0.00")

    with transaction.atomic():
        entrega, _ = Entrega.objects.select_for_update().get_or_create(id_pedido=pedido)
        if entrega.tracking_number or entrega.numero_guia:
            raise EnviaAPIError("El pedido ya tiene una guía de envío generada.")

        entrega.paqueteria = transportista
        entrega.transportista = transportista
        entrega.servicio = servicio
        entrega.numero_guia = tracking_number
        entrega.tracking_number = tracking_number
        entrega.costo_envio = price
        entrega.respuesta_json = {"status": "Creado localmente sin Envia.com"}
        entrega.save()

        pedido.costo_envio = price
        pedido.numero_rastreo = tracking_number
        pedido.save(update_fields=["costo_envio", "numero_rastreo"])

    return entrega


def rastrear_envio(tracking_number):
    """Consulta simulada de rastreo."""
    if not tracking_number:
        raise ValidationError({"tracking_number": "Este campo es obligatorio."})

    return {
        "status": "En tránsito / Reparto local",
        "tracking_number": tracking_number,
        "eventos": []
    }