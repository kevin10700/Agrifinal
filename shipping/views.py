import json
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from .services.envia import EnviaAPIError, cotizar_envio, crear_envio


def _json_body(request):
    try:
        return json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise ValidationError("El cuerpo debe ser JSON válido.")


def _error_response(error):
    if isinstance(error, ValidationError):
        # Manejo seguro de ValidationError tanto si es dict, list o str
        if hasattr(error, "message_dict"):
            data = error.message_dict
        elif hasattr(error, "messages"):
            data = error.messages
        else:
            data = str(error)
        return JsonResponse({"error": data}, status=400)
    
    status_code = getattr(error, "status_code", None) or 502
    detalle = getattr(error, "response_data", None)
    return JsonResponse(
        {"error": str(error), "detalle": detalle},
        status=status_code,
    )


@require_POST
@login_required
def crear(request):
    try:
        payload = _json_body(request)
        
        # TODO / Recomendación: Lógica para validar que el pedido esté pagado en Agrivale
        # pedido_id = payload.get("pedido_id")
        # pedido = get_object_or_404(Pedido, id=pedido_id, usuario=request.user)
        # if not pedido.pagado:
        #     return JsonResponse({"error": "El pedido aún no ha sido pagado."}, status=400)

        # Llama a la API para generar la guía y etiqueta de envío real
        respuesta_envio = crear_envio(payload)
        
        return JsonResponse({
            "status": "ok",
            "tracking_number": respuesta_envio.get("trackingNumber"),
            "label_url": respuesta_envio.get("label"),
            "detalle": respuesta_envio
        })
    except (ValidationError, EnviaAPIError) as error:
        return _error_response(error)


@require_POST
def cotizar(request):
    # Verificación explícita de autenticación para devolver JSON 401 en fetch/AJAX
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Debes iniciar sesión para cotizar el envío."}, status=401)

    try:
        payload = _json_body(request)
        origen = payload.get("origen", {
            "name": "Agrivale",
            "company": "Agrivale",
            "email": "contacto@agrivale.com",
            "phone": "5555555555",
            "street": "Av Principal",
            "number": "123",
            "district": "Centro",
            "city": "Toluca",
            "state": "MEX",
            "country": "MX",
            "postalCode": "50000"
        })
        destino = payload.get("destino")
        paquete = payload.get("paquete", {
            "content": "Productos Agrivale",
            "amount": 1,
            "type": "box",
            "weight": 1,
            "length": 10,
            "width": 10,
            "height": 10
        })

        if not destino or not destino.get("codigo_postal"):
            return JsonResponse({"error": "El código postal de destino es requerido."}, status=400)

        # Llamada directa a la API de Envia
        cotizaciones = cotizar_envio(origen, destino, paquete)

        # Formatear opciones para el frontend
        opciones = []
        for rate in cotizaciones:
            opciones.append({
                "tipo": "envia",
                "transportista": rate.get("carrierName"),
                "servicio": rate.get("serviceDescription"),
                "precio": float(rate.get("totalPrice", 0)),
                "dias_estimados": f"{rate.get('deliveryEstimate', 'N/A')} días",
            })

        request.session["envia_cotizaciones"] = opciones
        return JsonResponse({"tipo": "envia", "opciones": opciones})

    except (ValidationError, EnviaAPIError) as error:
        return _error_response(error)


@require_GET
def codigo_postal(request, codigo_postal):
    return JsonResponse({"codigo_postal": codigo_postal, "status": "ok"})