import json
import logging

from django.contrib import messages
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import redirect
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from .services.mercadopago import MercadoPagoError, procesar_webhook

logger = logging.getLogger(__name__)


@require_GET
def mercadopago_retorno(request):
    """El resultado visible es informativo; el webhook es la fuente de verdad."""
    pedido_id = request.GET.get("pedido_id") or request.GET.get("external_reference")
    if pedido_id:
        return redirect("pedidos:detalle_pedido", pedido_id=pedido_id)
    messages.info(request, "Estamos confirmando tu pago con Mercado Pago.")
    return redirect("pedidos:mis_pedidos")


@csrf_exempt
@require_POST
def mercadopago_webhook(request):
    """Recibe una notificación y consulta Mercado Pago antes de tocar la base de datos."""
    try:
        payload = json.loads(request.body or b"{}")
    except (ValueError, UnicodeDecodeError):
        return HttpResponseBadRequest("JSON inválido")

    try:
        procesar_webhook(payload, request.headers, request.GET)
    except MercadoPagoError as error:
        logger.warning("Webhook de Mercado Pago rechazado: %s", error)
        return HttpResponse(str(error), status=400)
    except Exception:
        logger.exception("Error inesperado procesando webhook de Mercado Pago")
        return HttpResponse("Error interno", status=500)
    return HttpResponse(status=200)
