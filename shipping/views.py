import json
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .services.envia import EnviaAPIError, cotizar_envio, crear_envio


def _json_body(request):
    try:
        return json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise ValidationError("El cuerpo debe ser JSON válido.")


def _error_response(error):
    if isinstance(error, ValidationError):
        return JsonResponse({"error": error.message_dict if hasattr(error, "message_dict") else error.messages}, status=400)
    
    status_code = getattr(error, "status_code", None) or 502
    detalle = getattr(error, "response_data", None)
    return JsonResponse(
        {"error": str(error), "detalle": detalle},
        status=status_code,
    )


@require_POST
@login_required
def cotizar(request):
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

def codigo_postal(request, codigo_postal):
    return JsonResponse({"codigo_postal": codigo_postal, "status": "ok"})