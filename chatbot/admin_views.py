"""
Vista del chatbot de administración de Agrivale.
Solo accesible para usuarios staff (is_staff=True). Acepta multipart/form-data
para permitir adjuntar una imagen junto con el mensaje de texto.
"""
from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST
import os
import re

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None

from .admin_tools import construir_tools_admin, INSTRUCCION_SISTEMA_ADMIN
from .admin_acciones import ACCIONES_ADMIN
from .admin_wizard import activo as wizard_activo, continuar as wizard_continuar, extraer_inicio as wizard_extraer_inicio, iniciar as wizard_iniciar
from .admin_confirmation import pendiente as confirmacion_pendiente, continuar as confirmacion_continuar, necesita_confirmacion, solicitar as solicitar_confirmacion

# Gemini 2.5 Flash fue retirado para proyectos nuevos. Este es el reemplazo
# estable y económico para interpretar instrucciones administrativas.
MODELO_GEMINI_ADMIN = os.getenv("GEMINI_ADMIN_MODEL", "gemini-3.5-flash-lite")


@staff_member_required
@xframe_options_sameorigin
def chatbot_admin_panel(request):
    """Renderiza la página del chat de administración."""
    return render(request, "chatbot/admin_chat.html")


def _get_gemini_client():
    api_key = getattr(settings, "GEMINI_API_KEY", None)
    if not api_key or genai is None:
        return None
    try:
        return genai.Client(api_key=api_key)
    except Exception:
        return None


def _interpretar_admin(mensaje, client):
    tool = construir_tools_admin()
    response = client.models.generate_content(
        model=MODELO_GEMINI_ADMIN,
        contents=mensaje,
        config=types.GenerateContentConfig(
            tools=[tool],
            system_instruction=INSTRUCCION_SISTEMA_ADMIN,
        ),
    )
    if not response.function_calls:
        return None
    llamada = response.function_calls[0]
    return llamada.name, dict(llamada.args or {})


@staff_member_required
@require_POST
@csrf_protect
def chatbot_admin_mensaje(request):
    """
    Espera multipart/form-data con:
      - mensaje: texto del administrador (obligatorio)
      - imagen: archivo opcional (usado por subir_imagen_producto)
    """
    mensaje = request.POST.get("mensaje", "").strip()
    if not mensaje:
        return JsonResponse(
            {"respuesta": "Escribe una instrucción, ej: 'crea la categoría Semillas'."},
            status=400,
        )

    # El alta de producto siempre es conversacional y requiere confirmación.
    # Nunca delegamos esta decisión a la IA ni creamos registros con defaults.
    if wizard_activo(request):
        return JsonResponse(wizard_continuar(request, mensaje))
    if confirmacion_pendiente(request):
        return JsonResponse(confirmacion_continuar(request, mensaje))
    nombre_producto = wizard_extraer_inicio(mensaje)
    if nombre_producto:
        return JsonResponse(wizard_iniciar(request, nombre_producto))

    # Esta orden común no necesita IA: sigue funcionando incluso si el servicio
    # externo está temporalmente caído.
    coincidencia_categoria = re.match(r"^\s*(?:crea|crear|agrega|añade)\s+(?:la\s+)?categor[ií]a\s+(.+?)\s*[.!]?\s*$", mensaje, re.IGNORECASE)
    if coincidencia_categoria:
        nombre = coincidencia_categoria.group(1).strip(" '\"")
        if nombre:
            return JsonResponse(solicitar_confirmacion(request, "crear_categoria", {"nombre": nombre}))

    client = _get_gemini_client()
    if client is None:
        return JsonResponse(
            {"respuesta": "El asistente de administración no está disponible ahora mismo (falta configurar GEMINI_API_KEY)."},
            status=503,
        )

    try:
        resultado_intent = _interpretar_admin(mensaje, client)
    except Exception as e:
        return JsonResponse({"respuesta": f"Ocurrió un error al interpretar tu instrucción: {e}"}, status=500)

    if not resultado_intent:
        return JsonResponse({"respuesta": "No entendí esa instrucción. Escribe 'ayuda' para ver qué puedo hacer."})

    nombre_funcion, args = resultado_intent
    # Defensa adicional: aunque el modelo ignore la instrucción, no puede crear
    # un producto directamente ni completar campos con valores inventados.
    if nombre_funcion == 'crear_producto':
        nombre = (args.get('nombre') or '').strip()
        if not nombre:
            return JsonResponse({'respuesta': '¿Cuál es el nombre del producto que deseas crear?'})
        return JsonResponse(wizard_iniciar(request, nombre))
    ejecutor = ACCIONES_ADMIN.get(nombre_funcion)
    if not ejecutor:
        return JsonResponse({"respuesta": "Esa acción no está implementada todavía."})
    if necesita_confirmacion(nombre_funcion):
        return JsonResponse(solicitar_confirmacion(request, nombre_funcion, args))

    try:
        respuesta = ejecutor(request, **args)
    except TypeError as e:
        return JsonResponse({"respuesta": f"Faltan datos para ejecutar esa acción: {e}"}, status=400)
    except Exception as e:
        return JsonResponse({"respuesta": f"Ocurrió un error al ejecutar la acción: {e}"}, status=500)

    return JsonResponse(respuesta)
