import json

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET, require_POST

from pedidos.models import Entrega, Pedido
from .services.envia import EnviaAPIError, cotizar_envio, crear_envio, validar_codigo_postal
from .services.local_shipping import buscar_zona_local


def _json_body(request):
    try:
        return json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise ValidationError("El cuerpo debe ser JSON válido.")


def _error_response(error):
    if isinstance(error, ValidationError):
        return JsonResponse({"error": error.message_dict if hasattr(error, "message_dict") else error.messages}, status=400)
    return JsonResponse(
        {"error": str(error), "detalle": error.response_data},
        status=error.status_code or 502,
    )


@require_GET
@login_required
def codigo_postal(request, codigo_postal):
    try:
        return JsonResponse(validar_codigo_postal(codigo_postal))
    except (ValidationError, EnviaAPIError) as error:
        return _error_response(error)


@require_POST
@login_required
def cotizar(request):
    try:
        payload = _json_body(request)
        destino = payload.get("destino") or {}
        
        # IMPRIMIR QUÉ PAQUETE Y DESTINO LLEGAN DESDE EL FRONTEND
        print("\n================ DATA RECIBIDA =============")
        print("DESTINO:", json.dumps(destino, indent=2))
        print("PAQUETE:", json.dumps(payload.get("paquete", {}), indent=2))
        print("============================================\n")

        reparto_local = buscar_zona_local(destino.get("codigo_postal"))
        if reparto_local:
            zona = reparto_local["zona"]
            opcion = {
                "tipo": "local",
                "transportista": "Agrivale",
                "servicio": "Reparto Local",
                "precio": float(reparto_local["costo"]),
                "dias_estimados": reparto_local["tiempo_entrega"],
                "zona_reparto": zona.nombre,
            }
            result = {"tipo": "local", "opciones": [opcion]}
        else:
            result = cotizar_envio(
                payload.get("origen"),
                destino,
                payload.get("paquete", {}),
                payload.get("transportista"),
            )
            result["tipo"] = "envia"

        #  IMPRIMIR QUÉ RESPONDE LA FUNCIÓN COTIZAR_ENVIO
        print("\n================ RESULTADO DE COTIZAR_ENVIO =============")
        print(json.dumps(result, indent=2, default=str))
        print("=========================================================\n")

        request.session["envia_cotizaciones"] = result["opciones"]
        return JsonResponse(result)
    except (ValidationError, EnviaAPIError) as error:
        return _error_response(error)


@require_POST
@login_required
def crear(request):
    try:
        payload = _json_body(request)
        pedido = get_object_or_404(
            Pedido, id_pedido=payload.get("pedido_id"), id_usuario=request.user
        )
        if pedido.estado_pago != "pagado":
            return JsonResponse(
                {"error": "El envío solo puede generarse cuando el pago esté confirmado."},
                status=409,
            )
        # Para reparto propio la entrega ya se registró al crear el pedido;
        # nunca intentamos generar una etiqueta de Envia.
        entrega_local = getattr(pedido, "entrega", None)
        if entrega_local and entrega_local.transportista == "Agrivale":
            return JsonResponse(
                {
                    "pedido_id": pedido.id_pedido,
                    "transportista": entrega_local.transportista,
                    "servicio": entrega_local.servicio,
                    "numero_guia": entrega_local.numero_guia,
                    "tracking_number": entrega_local.tracking_number,
                    "costo_envio": str(entrega_local.costo_envio),
                },
                status=200,
            )
        entrega = crear_envio(
            pedido,
            payload.get("transportista"),
            payload.get("servicio"),
        )
        return JsonResponse(
            {
                "pedido_id": pedido.id_pedido,
                "transportista": entrega.transportista,
                "servicio": entrega.servicio,
                "numero_guia": entrega.numero_guia,
                "tracking_number": entrega.tracking_number,
                "costo_envio": str(entrega.costo_envio),
            },
            status=201,
        )
    except (ValidationError, EnviaAPIError) as error:
        return _error_response(error)
