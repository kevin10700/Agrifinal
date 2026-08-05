import json
import re
from decimal import Decimal

from django.conf import settings
from django.db.models import Q
from django.http import JsonResponse
from django.urls import reverse
from django.views.decorators.http import require_POST

from productos.models import Producto, Categoria
from pedidos.models import CarritoItem

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None

RESPUESTA_DEFAULT = (
    "No entendí bien. Puedes preguntarme cosas como: "
    "'busco fertilizante orgánico', 'tengo pulgón en mi cultivo', "
    "'algo para la roya', 'calificación de humus de lombriz', "
    "'llévame a las ofertas', 'quiero pagar ahora', "
    "'cancela mi pedido' "
    "o '¿dónde veo mis pedidos?'"
)
RESPUESTA_LOGIN_REQUERIDO = "Para ver eso necesitas iniciar sesión primero. Te llevo a esa página."


# ===================== DICCIONARIO DE LENGUAJE AGRÍCOLA (respaldo sin Gemini) =====================
SINONIMOS_AGRICOLAS = {
    "fertilizante": [
        "abono", "nutriente", "nutrientes", "para la tierra", "para el suelo",
        "para que crezcan", "para engordar la planta", "alimento para planta",
        "alimento para plantas", "comida para planta", "para fertilizar",
        "para que den mas fruto", "para que produzcan mas",
    ],
    "organico": [
        "natural", "sin quimicos", "sin químicos", "ecologico", "ecológico",
        "libre de quimicos", "libre de químicos",
    ],
    "insecticida": [
        "plaga", "plagas", "insecto", "insectos", "bicho", "bichos",
        "pulgon", "pulgón", "gusano", "gusanos", "mosquita blanca",
        "para matar bichos", "para las plagas", "se estan comiendo las hojas",
        "se están comiendo las hojas",
    ],
    "fungicida": [
        "hongo", "hongos", "roya", "moho", "mancha en las hojas",
        "manchas en las hojas", "enfermedad de la planta", "se estan pudriendo",
        "se están pudriendo",
    ],
    "herbicida": [
        "maleza", "malezas", "hierba mala", "hierbas malas", "monte",
    ],
    "semilla": [
        "semillas", "siembra", "sembrar", "para sembrar",
    ],
    "riego": [
        "regar", "agua para planta", "sistema de riego", "para regar",
    ],
    "humus": [
        "lombricomposta", "composta", "tierra negra", "mejorador de suelo",
    ],
}


def _normalizar_lenguaje_agricola(texto):
    terminos_detectados = []
    for canonico, variantes in SINONIMOS_AGRICOLAS.items():
        for variante in variantes:
            if variante in texto:
                terminos_detectados.append(canonico)
                break
    if terminos_detectados:
        texto = texto + " " + " ".join(terminos_detectados)
    return texto


# ===================== UTILIDADES =====================

def _limpiar(texto):
    texto = texto.lower().strip()
    return re.sub(r"[¿?¡!.,]", "", texto)


def _extraer_termino(texto, disparadores):
    for d in disparadores:
        if d in texto:
            resto = texto.split(d, 1)[1].strip()
            if resto:
                return resto
    return None


def _extraer_numero(texto):
    match = re.search(r"\d+", texto)
    return int(match.group(0)) if match else None


def _serializar_producto(p):
    return {
        "id": p.id_producto,
        "nombre": p.nombre,
        "precio": float(p.get_precio_actual()),
        "precio_original": float(p.precio) if p.precio_oferta else None,
        "en_oferta": p.precio_oferta is not None,
        "calificacion": p.get_calificacion_promedio(),
        "total_resenas": p.get_total_comentarios(),
        "stock": p.stock,
        "imagen": p.imagen_principal.url if p.imagen_principal else None,
        "url": p.get_absolute_url(),
    }


# ===================== HANDLERS DE INFORMACIÓN (sistema de respaldo por reglas) =====================

def handler_calificacion(texto, request):
    termino = _extraer_termino(
        texto, ["calificacion de", "calificación de", "resenas de", "reseñas de", "opiniones de"]
    )
    if not termino:
        return None
    producto = Producto.objects.filter(nombre__icontains=termino).first()
    if not producto:
        return {"tipo": "texto", "respuesta": f"No encontré un producto llamado '{termino}'."}
    calif = producto.get_calificacion_promedio()
    total = producto.get_total_comentarios()
    texto_resp = (
        f"'{producto.nombre}' todavía no tiene reseñas."
        if total == 0
        else f"'{producto.nombre}' tiene {calif}⭐ de promedio con {total} reseña(s)."
    )
    return {"tipo": "productos", "respuesta": texto_resp, "productos": [_serializar_producto(producto)]}


def handler_precio(texto, request):
    termino = _extraer_termino(texto, ["precio de", "cuanto cuesta", "cuánto cuesta"])
    if not termino:
        return None
    producto = Producto.objects.filter(nombre__icontains=termino).first()
    if not producto:
        return {"tipo": "texto", "respuesta": f"No encontré un producto llamado '{termino}'."}
    return {
        "tipo": "productos",
        "respuesta": f"'{producto.nombre}' cuesta ${producto.get_precio_actual()} por {producto.get_unidad_medida_display()}.",
        "productos": [_serializar_producto(producto)],
    }


def handler_precios_generales(texto, request):
    """Da una muestra de precios cuando aún no se ha elegido un producto."""
    if not any(frase in texto for frase in ["ver precios", "saber los precios", "precios de productos"]):
        return None
    productos = Producto.objects.filter(stock__gt=0)[:6]
    if not productos.exists():
        return {"tipo": "texto", "respuesta": "Todavía no hay productos con precio disponible."}
    return {
        "tipo": "productos",
        "respuesta": "Estos son algunos precios. Si quieres, dime el nombre de un producto para ver su precio exacto.",
        "productos": [_serializar_producto(p) for p in productos],
    }


def handler_ofertas(texto, request):
    if any(p in texto for p in ["oferta", "descuento", "rebaja", "promocion"]):
        productos = Producto.objects.filter(precio_oferta__isnull=False)[:8]
        if not productos.exists():
            return {"tipo": "texto", "respuesta": "Ahora mismo no hay ofertas activas."}
        return {
            "tipo": "productos",
            "respuesta": "Estas son las ofertas disponibles:",
            "productos": [_serializar_producto(p) for p in productos],
        }
    return None


def handler_organicos(texto, request):
    if "organico" in texto or "orgánico" in texto:
        productos = Producto.objects.filter(es_organico=True)[:8]
        if not productos.exists():
            return {"tipo": "texto", "respuesta": "No hay productos orgánicos disponibles por ahora."}
        return {
            "tipo": "productos",
            "respuesta": "Productos orgánicos disponibles:",
            "productos": [_serializar_producto(p) for p in productos],
        }
    return None


def handler_filtrar_categoria(texto, request):
    for cat in Categoria.objects.all():
        if cat.nombre.lower() in texto:
            productos = Producto.objects.filter(id_categoria=cat)[:8]
            if not productos.exists():
                return {"tipo": "texto", "respuesta": f"No hay productos disponibles en '{cat.nombre}' por ahora."}
            return {
                "tipo": "productos",
                "respuesta": f"Productos en la categoría '{cat.nombre}':",
                "productos": [_serializar_producto(p) for p in productos],
            }
    return None


def handler_buscar_producto(texto, request):
    termino = _extraer_termino(
        texto,
        [
            "busco", "buscar", "encuentra", "quiero ver", "necesito",
            "recomiendas", "recomiendame", "recomiéndame", "algo para", "tengo",
        ],
    )
    if not termino:
        return None
    productos = Producto.objects.filter(
        Q(nombre__icontains=termino)
        | Q(descripcion_corta__icontains=termino)
        | Q(descripcion_larga__icontains=termino)
        | Q(id_categoria__nombre__icontains=termino)
    )[:6]
    if not productos.exists():
        return {"tipo": "texto", "respuesta": f"No encontré productos relacionados con '{termino}'."}
    return {
        "tipo": "productos",
        "respuesta": f"Encontré {productos.count()} producto(s) para '{termino}':",
        "productos": [_serializar_producto(p) for p in productos],
    }


def handler_lenguaje_agricola_generico(texto, request):
    terminos_detectados = []
    for canonico, variantes in SINONIMOS_AGRICOLAS.items():
        for variante in variantes:
            if variante in texto:
                terminos_detectados.append(canonico)
                break
    if not terminos_detectados:
        return None

    query = Q()
    for termino in terminos_detectados:
        query |= (
            Q(nombre__icontains=termino)
            | Q(descripcion_corta__icontains=termino)
            | Q(descripcion_larga__icontains=termino)
            | Q(id_categoria__nombre__icontains=termino)
        )
    productos = Producto.objects.filter(query).distinct()[:6]

    if not productos.exists():
        return {
            "tipo": "texto",
            "respuesta": f"Detecté que buscas algo relacionado con: {', '.join(terminos_detectados)}, pero no encontré productos así todavía.",
        }
    return {
        "tipo": "productos",
        "respuesta": f"Esto podría ayudarte (relacionado con {', '.join(terminos_detectados)}):",
        "productos": [_serializar_producto(p) for p in productos],
    }


# ===================== HANDLERS DE CARRITO (respaldo por reglas) =====================

def _extraer_cantidad_y_producto(texto):
    match = re.search(
        r"agrega(?:r)?\s+(\d+)?\s*(?:kg|unidades|libras|cajas)?\s*(?:de\s+)?(.+?)\s+al carrito",
        texto,
    )
    if not match:
        return None, None
    cantidad = int(match.group(1)) if match.group(1) else 1
    nombre_producto = match.group(2).strip()
    return cantidad, nombre_producto


def handler_agregar_carrito(texto, request):
    if "al carrito" not in texto or "agrega" not in texto:
        return None

    if not request.user.is_authenticated:
        return {"tipo": "redirigir", "respuesta": RESPUESTA_LOGIN_REQUERIDO, "url": reverse("usuarios:login")}

    cantidad, nombre_producto = _extraer_cantidad_y_producto(texto)
    if not nombre_producto:
        return {
            "tipo": "texto",
            "respuesta": "Dime qué producto quieres agregar, ej: 'agrega humus de lombriz al carrito'.",
        }

    producto = Producto.objects.filter(nombre__icontains=nombre_producto).first()
    if not producto:
        return {"tipo": "texto", "respuesta": f"No encontré un producto llamado '{nombre_producto}'."}

    if producto.stock <= 0:
        return {"tipo": "texto", "respuesta": f"No hay stock de '{producto.nombre}' por el momento."}

    item, creado = CarritoItem.objects.get_or_create(
        id_usuario=request.user,
        id_producto=producto,
        defaults={"cantidad": cantidad},
    )

    if not creado:
        nueva_cantidad = item.cantidad + cantidad
        if nueva_cantidad > producto.stock:
            return {
                "tipo": "texto",
                "respuesta": f"No hay suficiente stock de '{producto.nombre}'. Disponible: {producto.stock}.",
            }
        item.cantidad = nueva_cantidad
        item.save()

    return {
        "tipo": "productos",
        "respuesta": f"✅ Agregué {cantidad} de '{producto.nombre}' a tu carrito.",
        "productos": [_serializar_producto(producto)],
        "url": reverse("pedidos:ver_carrito"),
    }


def handler_actualizar_carrito(texto, request):
    match = re.search(
        r"(?:cambia|actualiza|modifica|pon)\s+(?:la cantidad de\s+)?(.+?)\s+a\s+(\d+)",
        texto,
    )
    if not match:
        return None
    if "carrito" not in texto and "cantidad" not in texto:
        return None

    if not request.user.is_authenticated:
        return {"tipo": "redirigir", "respuesta": RESPUESTA_LOGIN_REQUERIDO, "url": reverse("usuarios:login")}

    nombre_producto = match.group(1).strip()
    nueva_cantidad = int(match.group(2))

    producto = Producto.objects.filter(nombre__icontains=nombre_producto).first()
    if not producto:
        return {"tipo": "texto", "respuesta": f"No encontré un producto llamado '{nombre_producto}'."}

    item = CarritoItem.objects.filter(id_usuario=request.user, id_producto=producto).first()
    if not item:
        return {"tipo": "texto", "respuesta": f"'{producto.nombre}' no está en tu carrito todavía."}

    if nueva_cantidad <= 0:
        item.delete()
        return {
            "tipo": "texto",
            "respuesta": f"🗑️ Quité '{producto.nombre}' de tu carrito (cantidad 0).",
            "url": reverse("pedidos:ver_carrito"),
        }

    if nueva_cantidad > producto.stock:
        return {
            "tipo": "texto",
            "respuesta": f"No hay suficiente stock de '{producto.nombre}'. Disponible: {producto.stock}.",
        }

    item.cantidad = nueva_cantidad
    item.save()
    return {
        "tipo": "productos",
        "respuesta": f"✅ Actualicé '{producto.nombre}' a {nueva_cantidad} en tu carrito.",
        "productos": [_serializar_producto(producto)],
        "url": reverse("pedidos:ver_carrito"),
    }


def handler_eliminar_carrito(texto, request):
    disparadores = ["elimina", "eliminar", "quita", "quitar", "borra", "borrar"]
    if not any(d in texto for d in disparadores) or "carrito" not in texto:
        return None

    if not request.user.is_authenticated:
        return {"tipo": "redirigir", "respuesta": RESPUESTA_LOGIN_REQUERIDO, "url": reverse("usuarios:login")}

    nombre_producto = None
    for d in disparadores:
        if d in texto:
            resto = texto.split(d, 1)[1]
            resto = (
                resto.replace("del carrito", "")
                .replace("de mi carrito", "")
                .replace("al carrito", "")
                .strip()
            )
            if resto:
                nombre_producto = resto
            break

    if not nombre_producto:
        return {
            "tipo": "texto",
            "respuesta": "Dime qué producto quieres quitar, ej: 'elimina humus de lombriz del carrito'.",
        }

    producto = Producto.objects.filter(nombre__icontains=nombre_producto).first()
    if not producto:
        return {"tipo": "texto", "respuesta": f"No encontré '{nombre_producto}' en el catálogo."}

    item = CarritoItem.objects.filter(id_usuario=request.user, id_producto=producto).first()
    if not item:
        return {"tipo": "texto", "respuesta": f"'{producto.nombre}' no está en tu carrito."}

    item.delete()
    return {
        "tipo": "texto",
        "respuesta": f" Quité '{producto.nombre}' de tu carrito.",
        "url": reverse("pedidos:ver_carrito"),
    }


# ===================== HANDLER: IR A PÁGINAS (respaldo por reglas) =====================

def handler_ir_pagina(texto, request):
    mapa = [
        (
            ["ofertas especiales", "llevame a las ofertas", "llévame a las ofertas",
             "ir a ofertas", "ver pagina de ofertas", "ver página de ofertas",
             "pagina de ofertas", "página de ofertas", "dirigeme a las ofertas",
             "diríjeme a las ofertas"],
            "productos:ofertas",
            False,
        ),
        (
            ["catalogo", "catálogo", "todos los productos", "ver productos",
             "buscar productos", "ir a productos", "llevame a productos",
             "llévame a productos", "ver catalogo", "ver catálogo"],
            "productos:lista",
            False,
        ),
        (
            ["pagar ahora", "quiero pagar", "como pago", "cómo pago",
             "donde pago", "dónde pago", "finalizar compra", "ir a pagar",
             "llevame a pagar", "llévame a pagar", "checkout", "dirigeme para pagar",
             "diríjeme para pagar", "dirigeme a pagar", "diríjeme a pagar",
             "confirmar pedido", "confirmar mi pedido"],
            "pedidos:confirmar",
            True,
        ),
    ]
    for palabras, url_name, requiere_login in mapa:
        if any(p in texto for p in palabras):
            if requiere_login and not request.user.is_authenticated:
                return {"tipo": "redirigir", "respuesta": RESPUESTA_LOGIN_REQUERIDO, "url": reverse("usuarios:login")}
            try:
                return {"tipo": "redirigir", "respuesta": "Te llevo ahí.", "url": reverse(url_name)}
            except Exception:
                return None
    return None


# ===================== HANDLER: PEDIDOS (respaldo por reglas) =====================

def handler_cancelar_pedido(texto, request):
    if "cancel" not in texto or "pedido" not in texto:
        return None

    if not request.user.is_authenticated:
        return {"tipo": "redirigir", "respuesta": RESPUESTA_LOGIN_REQUERIDO, "url": reverse("usuarios:login")}

    pedido_id = _extraer_numero(texto)
    if not pedido_id:
        return {
            "tipo": "texto",
            "respuesta": "Dime el número de pedido que quieres cancelar, ej: 'cancela mi pedido 12'. "
                         "Puedes ver tus números de pedido en 'mis pedidos'.",
        }

    try:
        url = reverse("pedidos:solicitar_cancelacion", kwargs={"pedido_id": pedido_id})
    except Exception:
        return {"tipo": "texto", "respuesta": f"No pude generar la solicitud de cancelación para el pedido {pedido_id}."}

    return {
        "tipo": "redirigir",
        "respuesta": f"Te llevo a la solicitud de cancelación de tu pedido #{pedido_id}.",
        "url": url,
    }


def handler_detalle_pedido(texto, request):
    disparadores = ["detalle de mi pedido", "detalle del pedido", "estado de mi pedido",
                     "estado del pedido", "ver pedido", "ver mi pedido"]
    if not any(d in texto for d in disparadores):
        return None

    if not request.user.is_authenticated:
        return {"tipo": "redirigir", "respuesta": RESPUESTA_LOGIN_REQUERIDO, "url": reverse("usuarios:login")}

    pedido_id = _extraer_numero(texto)
    if not pedido_id:
        return {
            "tipo": "texto",
            "respuesta": "Dime el número de pedido, ej: 'ver detalle de mi pedido 12'.",
        }

    try:
        url = reverse("pedidos:detalle_pedido", kwargs={"pedido_id": pedido_id})
    except Exception:
        return {"tipo": "texto", "respuesta": f"No encontré el pedido #{pedido_id}."}

    return {
        "tipo": "redirigir",
        "respuesta": f"Te llevo al detalle de tu pedido #{pedido_id}.",
        "url": url,
    }


# ===================== HANDLERS DE NAVEGACIÓN GENERAL (respaldo por reglas) =====================

def handler_navegacion(texto, request):
    mapa = [
        (["carrito", "mi compra"], "pedidos:ver_carrito", True),
        (["mi pedido", "mis pedidos", "seguimiento"], "pedidos:mis_pedidos", True),
        (["notificaciones", "mis avisos"], "pedidos:notificaciones", True),
        (["registrar", "crear cuenta", "registro"], "usuarios:registro", False),
        (["iniciar sesion", "login", "acceder"], "usuarios:login", False),
        (["mi perfil", "mi cuenta"], "usuarios:perfil", True),
    ]
    for palabras, url_name, requiere_login in mapa:
        if any(p in texto for p in palabras):
            if requiere_login and not request.user.is_authenticated:
                return {"tipo": "redirigir", "respuesta": RESPUESTA_LOGIN_REQUERIDO, "url": reverse("usuarios:login")}
            try:
                return {"tipo": "redirigir", "respuesta": "Te llevo ahí.", "url": reverse(url_name)}
            except Exception:
                return None
    return None


def handler_ayuda(texto, request):
    if any(p in texto for p in ["ayuda", "que puedo hacer", "opciones", "menu"]):
        return {
            "tipo": "texto",
            "respuesta": (
                "Puedo: buscar productos por nombre o por problema ('tengo pulgón', 'algo para la roya'), "
                "filtrar por categoría, ofertas u orgánicos, decirte precio o calificación, "
                "agregar/actualizar/eliminar productos de tu carrito, llevarte a las ofertas especiales, "
                "al catálogo, a pagar ahora, a tus pedidos y notificaciones, "
                "o ayudarte a cancelar un pedido o ver su detalle."
            ),
        }
    return None


HANDLERS = [
    handler_eliminar_carrito,
    handler_actualizar_carrito,
    handler_agregar_carrito,
    handler_ir_pagina,
    handler_cancelar_pedido,
    handler_detalle_pedido,
    handler_calificacion,
    handler_precios_generales,
    handler_precio,
    handler_ofertas,
    handler_organicos,
    handler_filtrar_categoria,
    handler_buscar_producto,
    handler_lenguaje_agricola_generico,
    handler_navegacion,
    handler_ayuda,
]


# ===================== INTEGRACIÓN CON GEMINI (capa de comprensión de lenguaje natural) =====================

# Reemplazo estable de Gemini 2.5 Flash, retirado para proyectos nuevos.
MODELO_GEMINI = getattr(settings, "GEMINI_CHAT_MODEL", "gemini-3.5-flash-lite")


def _get_gemini_client():
    api_key = getattr(settings, "GEMINI_API_KEY", None)
    if not api_key or genai is None:
        return None
    try:
        return genai.Client(api_key=api_key)
    except Exception:
        return None


def _construir_tools_gemini():
    declaraciones = [
        types.FunctionDeclaration(
            name="buscar_producto",
            description="Busca productos en el catálogo por nombre, problema del cultivo (plaga, hongo, maleza) o necesidad general del agricultor.",
            parameters_json_schema={
                "type": "object",
                "properties": {
                    "termino": {"type": "string", "description": "Palabra o frase clave a buscar, ej: 'fertilizante', 'pulgón', 'roya', 'humus'."}
                },
                "required": ["termino"],
            },
        ),
        types.FunctionDeclaration(
            name="ver_precio",
            description="Consulta el precio de un producto específico.",
            parameters_json_schema={
                "type": "object",
                "properties": {"nombre_producto": {"type": "string"}},
                "required": ["nombre_producto"],
            },
        ),
        types.FunctionDeclaration(
            name="ver_calificacion",
            description="Consulta la calificación o reseñas de un producto específico.",
            parameters_json_schema={
                "type": "object",
                "properties": {"nombre_producto": {"type": "string"}},
                "required": ["nombre_producto"],
            },
        ),
        types.FunctionDeclaration(
            name="ver_ofertas",
            description="Muestra los productos que están actualmente en oferta o con descuento.",
            parameters_json_schema={"type": "object", "properties": {}},
        ),
        types.FunctionDeclaration(
            name="ver_organicos",
            description="Muestra los productos orgánicos o naturales disponibles.",
            parameters_json_schema={"type": "object", "properties": {}},
        ),
        types.FunctionDeclaration(
            name="filtrar_categoria",
            description="Muestra productos de una categoría específica del catálogo.",
            parameters_json_schema={
                "type": "object",
                "properties": {"categoria": {"type": "string"}},
                "required": ["categoria"],
            },
        ),
        types.FunctionDeclaration(
            name="agregar_carrito",
            description="Agrega una cantidad de un producto al carrito de compras del usuario.",
            parameters_json_schema={
                "type": "object",
                "properties": {
                    "nombre_producto": {"type": "string"},
                    "cantidad": {"type": "integer", "description": "Cantidad a agregar. Usa 1 si el usuario no especifica número."},
                },
                "required": ["nombre_producto"],
            },
        ),
        types.FunctionDeclaration(
            name="actualizar_carrito",
            description="Cambia la cantidad de un producto que YA está en el carrito del usuario a un número exacto (no suma, reemplaza el valor). Úsala cuando el usuario diga frases como 'solo quiero una', 'déjalo en 3', 'cambia la cantidad'.",
            parameters_json_schema={
                "type": "object",
                "properties": {
                    "nombre_producto": {"type": "string"},
                    "cantidad": {"type": "integer", "description": "Nueva cantidad exacta deseada. Convierte números en palabras a dígitos, ej: 'una' es 1, 'dos' es 2."},
                },
                "required": ["nombre_producto", "cantidad"],
            },
        ),
        types.FunctionDeclaration(
            name="eliminar_carrito",
            description="Quita por completo un producto del carrito del usuario.",
            parameters_json_schema={
                "type": "object",
                "properties": {"nombre_producto": {"type": "string"}},
                "required": ["nombre_producto"],
            },
        ),
        types.FunctionDeclaration(
            name="ir_a_pagina",
            description="Lleva al usuario a una página específica de la tienda: ofertas especiales, catálogo completo, o pagar/finalizar compra.",
            parameters_json_schema={
                "type": "object",
                "properties": {
                    "destino": {"type": "string", "enum": ["ofertas", "catalogo", "pagar"]}
                },
                "required": ["destino"],
            },
        ),
        types.FunctionDeclaration(
            name="cancelar_pedido",
            description="Lleva al usuario a la página para solicitar la cancelación de un pedido específico.",
            parameters_json_schema={
                "type": "object",
                "properties": {"numero_pedido": {"type": "integer"}},
                "required": ["numero_pedido"],
            },
        ),
        types.FunctionDeclaration(
            name="ver_detalle_pedido",
            description="Muestra el detalle o estado de un pedido específico del usuario.",
            parameters_json_schema={
                "type": "object",
                "properties": {"numero_pedido": {"type": "integer"}},
                "required": ["numero_pedido"],
            },
        ),
        types.FunctionDeclaration(
            name="agregar_favorito",
            description="Agrega un producto a la lista de favoritos del usuario para guardarlo y encontrarlo fácilmente más tarde.",
            parameters_json_schema={
                "type": "object",
                "properties": {"nombre_producto": {"type": "string"}},
                "required": ["nombre_producto"],
            },
        ),
        types.FunctionDeclaration(
            name="eliminar_favorito",
            description="Elimina un producto de la lista de favoritos del usuario.",
            parameters_json_schema={
                "type": "object",
                "properties": {"nombre_producto": {"type": "string"}},
                "required": ["nombre_producto"],
            },
        ),
        types.FunctionDeclaration(
            name="navegar",
            description="Lleva al usuario a una sección general de la tienda: su carrito, lista de sus pedidos, notificaciones, registro, login o su perfil, o su lista de favoritos.",
            parameters_json_schema={
                "type": "object",
                "properties": {
                    "destino": {
                        "type": "string",
                        "enum": ["carrito", "mis_pedidos", "notificaciones", "registro", "login", "perfil", "favoritos"],
                    }
                },
                "required": ["destino"],
            },
        ),
        types.FunctionDeclaration(
            name="ayuda",
            description="Explica qué puede hacer el chatbot. Úsala cuando el mensaje no encaje claramente en ninguna otra función.",
            parameters_json_schema={"type": "object", "properties": {}},
        ),
    ]
    return types.Tool(function_declarations=declaraciones)


INSTRUCCION_SISTEMA = (
    "Eres el asistente de Agrivale, una tienda en línea de productos agrícolas "
    "(fertilizantes, insecticidas, fungicidas, herbicidas, semillas, humus, riego, etc). "
    "Identifica qué acción quiere el usuario, incluso si usa lenguaje coloquial del campo "
    "(plagas, hongos, malezas, nombres regionales) o frases naturales con errores de tipeo. "
    "SIEMPRE debes responder llamando a una de las funciones disponibles, nunca solo con texto. "
    "Si el usuario menciona un problema de cultivo (plaga, hongo, maleza), usa buscar_producto "
    "con el término técnico más probable (insecticida, fungicida, herbicida, fertilizante). "
    "Si menciona cantidades en palabras ('una', 'dos', 'tres'), conviértelas a número. "
    "Si el mensaje no encaja en ninguna función, usa ayuda."
)


def _interpretar_con_gemini(mensaje, client):
    tool = _construir_tools_gemini()
    response = client.models.generate_content(
        model=MODELO_GEMINI,
        contents=mensaje,
        config=types.GenerateContentConfig(
            tools=[tool],
            system_instruction=INSTRUCCION_SISTEMA,
        ),
    )
    if not response.function_calls:
        return None
    llamada = response.function_calls[0]
    return llamada.name, dict(llamada.args or {})


# ===================== EJECUTORES DE ACCIONES (llamados por Gemini) =====================

def _buscar_producto_por_nombre(nombre):
    if not nombre:
        return None
    return Producto.objects.filter(nombre__icontains=nombre).first()


def accion_buscar_producto(request, termino=""):
    if not termino:
        return {"tipo": "texto", "respuesta": "¿Qué producto o problema de cultivo buscas?"}
    productos = Producto.objects.filter(
        Q(nombre__icontains=termino)
        | Q(descripcion_corta__icontains=termino)
        | Q(descripcion_larga__icontains=termino)
        | Q(id_categoria__nombre__icontains=termino)
    ).distinct()[:6]
    if not productos.exists():
        return {"tipo": "texto", "respuesta": f"No encontré productos relacionados con '{termino}'."}
    return {
        "tipo": "productos",
        "respuesta": f"Encontré {productos.count()} producto(s) para '{termino}':",
        "productos": [_serializar_producto(p) for p in productos],
    }


def accion_ver_precio(request, nombre_producto=""):
    producto = _buscar_producto_por_nombre(nombre_producto)
    if not producto:
        return {"tipo": "texto", "respuesta": f"No encontré un producto llamado '{nombre_producto}'."}
    return {
        "tipo": "productos",
        "respuesta": f"'{producto.nombre}' cuesta ${producto.get_precio_actual()} por {producto.get_unidad_medida_display()}.",
        "productos": [_serializar_producto(producto)],
    }


def accion_ver_calificacion(request, nombre_producto=""):
    producto = _buscar_producto_por_nombre(nombre_producto)
    if not producto:
        return {"tipo": "texto", "respuesta": f"No encontré un producto llamado '{nombre_producto}'."}
    calif = producto.get_calificacion_promedio()
    total = producto.get_total_comentarios()
    texto_resp = (
        f"'{producto.nombre}' todavía no tiene reseñas."
        if total == 0
        else f"'{producto.nombre}' tiene {calif}⭐ de promedio con {total} reseña(s)."
    )
    return {"tipo": "productos", "respuesta": texto_resp, "productos": [_serializar_producto(producto)]}


def accion_ver_ofertas(request):
    productos = Producto.objects.filter(precio_oferta__isnull=False)[:8]
    if not productos.exists():
        return {"tipo": "texto", "respuesta": "Ahora mismo no hay ofertas activas."}
    return {
        "tipo": "productos",
        "respuesta": "Estas son las ofertas disponibles:",
        "productos": [_serializar_producto(p) for p in productos],
    }


def accion_ver_organicos(request):
    productos = Producto.objects.filter(es_organico=True)[:8]
    if not productos.exists():
        return {"tipo": "texto", "respuesta": "No hay productos orgánicos disponibles por ahora."}
    return {
        "tipo": "productos",
        "respuesta": "Productos orgánicos disponibles:",
        "productos": [_serializar_producto(p) for p in productos],
    }


def accion_filtrar_categoria(request, categoria=""):
    cat = Categoria.objects.filter(nombre__icontains=categoria).first()
    if not cat:
        return {"tipo": "texto", "respuesta": f"No encontré la categoría '{categoria}'."}
    productos = Producto.objects.filter(id_categoria=cat)[:8]
    if not productos.exists():
        return {"tipo": "texto", "respuesta": f"No hay productos disponibles en '{cat.nombre}' por ahora."}
    return {
        "tipo": "productos",
        "respuesta": f"Productos en la categoría '{cat.nombre}':",
        "productos": [_serializar_producto(p) for p in productos],
    }


def accion_agregar_carrito(request, nombre_producto="", cantidad=1):
    if not request.user.is_authenticated:
        return {"tipo": "redirigir", "respuesta": RESPUESTA_LOGIN_REQUERIDO, "url": reverse("usuarios:login")}
    cantidad = int(cantidad) if cantidad else 1
    producto = _buscar_producto_por_nombre(nombre_producto)
    if not producto:
        return {"tipo": "texto", "respuesta": f"No encontré un producto llamado '{nombre_producto}'."}
    if producto.stock <= 0:
        return {"tipo": "texto", "respuesta": f"No hay stock de '{producto.nombre}' por el momento."}

    item, creado = CarritoItem.objects.get_or_create(
        id_usuario=request.user, id_producto=producto, defaults={"cantidad": cantidad}
    )
    if not creado:
        nueva_cantidad = item.cantidad + cantidad
        if nueva_cantidad > producto.stock:
            return {
                "tipo": "texto",
                "respuesta": f"No hay suficiente stock de '{producto.nombre}'. Disponible: {producto.stock}.",
            }
        item.cantidad = nueva_cantidad
        item.save()

    return {
        "tipo": "productos",
        "respuesta": f"✅ Agregué {cantidad} de '{producto.nombre}' a tu carrito.",
        "productos": [_serializar_producto(producto)],
        "url": reverse("pedidos:ver_carrito"),
    }


def accion_actualizar_carrito(request, nombre_producto="", cantidad=None):
    if not request.user.is_authenticated:
        return {"tipo": "redirigir", "respuesta": RESPUESTA_LOGIN_REQUERIDO, "url": reverse("usuarios:login")}
    if cantidad is None:
        return {"tipo": "texto", "respuesta": "Dime a qué cantidad quieres dejar el producto."}
    cantidad = int(cantidad)
    producto = _buscar_producto_por_nombre(nombre_producto)
    if not producto:
        return {"tipo": "texto", "respuesta": f"No encontré un producto llamado '{nombre_producto}'."}
    item = CarritoItem.objects.filter(id_usuario=request.user, id_producto=producto).first()
    if not item:
        return {"tipo": "texto", "respuesta": f"'{producto.nombre}' no está en tu carrito todavía."}
    if cantidad <= 0:
        item.delete()
        return {
            "tipo": "texto",
            "respuesta": f"🗑️ Quité '{producto.nombre}' de tu carrito (cantidad 0).",
            "url": reverse("pedidos:ver_carrito"),
        }
    if cantidad > producto.stock:
        return {
            "tipo": "texto",
            "respuesta": f"No hay suficiente stock de '{producto.nombre}'. Disponible: {producto.stock}.",
        }
    item.cantidad = cantidad
    item.save()
    return {
        "tipo": "productos",
        "respuesta": f"✅ Actualicé '{producto.nombre}' a {cantidad} en tu carrito.",
        "productos": [_serializar_producto(producto)],
        "url": reverse("pedidos:ver_carrito"),
    }


def accion_eliminar_carrito(request, nombre_producto=""):
    if not request.user.is_authenticated:
        return {"tipo": "redirigir", "respuesta": RESPUESTA_LOGIN_REQUERIDO, "url": reverse("usuarios:login")}
    producto = _buscar_producto_por_nombre(nombre_producto)
    if not producto:
        return {"tipo": "texto", "respuesta": f"No encontré '{nombre_producto}' en el catálogo."}
    item = CarritoItem.objects.filter(id_usuario=request.user, id_producto=producto).first()
    if not item:
        return {"tipo": "texto", "respuesta": f"'{producto.nombre}' no está en tu carrito."}
    item.delete()
    return {
        "tipo": "texto",
        "respuesta": f"🗑️ Quité '{producto.nombre}' de tu carrito.",
        "url": reverse("pedidos:ver_carrito"),
    }


def accion_ir_a_pagina(request, destino=""):
    mapa = {"ofertas": "productos:ofertas", "catalogo": "productos:lista", "pagar": "pedidos:confirmar"}
    url_name = mapa.get(destino)
    if not url_name:
        return {"tipo": "texto", "respuesta": "No reconocí a dónde quieres ir."}
    if destino == "pagar" and not request.user.is_authenticated:
        return {"tipo": "redirigir", "respuesta": RESPUESTA_LOGIN_REQUERIDO, "url": reverse("usuarios:login")}
    try:
        return {"tipo": "redirigir", "respuesta": "Te llevo ahí.", "url": reverse(url_name)}
    except Exception:
        return {"tipo": "texto", "respuesta": "No pude generar esa ruta."}


def accion_cancelar_pedido(request, numero_pedido=None):
    if not request.user.is_authenticated:
        return {"tipo": "redirigir", "respuesta": RESPUESTA_LOGIN_REQUERIDO, "url": reverse("usuarios:login")}
    if numero_pedido is None:
        return {"tipo": "texto", "respuesta": "Dime el número de pedido que quieres cancelar."}
    try:
        url = reverse("pedidos:solicitar_cancelacion", kwargs={"pedido_id": int(numero_pedido)})
    except Exception:
        return {"tipo": "texto", "respuesta": f"No pude generar la solicitud de cancelación para el pedido {numero_pedido}."}
    return {
        "tipo": "redirigir",
        "respuesta": f"Te llevo a la solicitud de cancelación de tu pedido #{numero_pedido}.",
        "url": url,
    }


def accion_ver_detalle_pedido(request, numero_pedido=None):
    if not request.user.is_authenticated:
        return {"tipo": "redirigir", "respuesta": RESPUESTA_LOGIN_REQUERIDO, "url": reverse("usuarios:login")}
    if numero_pedido is None:
        return {"tipo": "texto", "respuesta": "Dime el número de pedido que quieres consultar."}
    try:
        url = reverse("pedidos:detalle_pedido", kwargs={"pedido_id": int(numero_pedido)})
    except Exception:
        return {"tipo": "texto", "respuesta": f"No encontré el pedido #{numero_pedido}."}
    return {
        "tipo": "redirigir",
        "respuesta": f"Te llevo al detalle de tu pedido #{numero_pedido}.",
        "url": url,
    }


def accion_navegar(request, destino=""):
    mapa = {
        "carrito": ("pedidos:ver_carrito", True),
        "mis_pedidos": ("pedidos:mis_pedidos", True),
        "notificaciones": ("pedidos:notificaciones", True),
        "registro": ("usuarios:registro", False),
        "login": ("usuarios:login", False),
        "perfil": ("usuarios:perfil", True),
        "favoritos": ("productos:favoritos", True),
    }
    datos = mapa.get(destino)
    if not datos:
        return {"tipo": "texto", "respuesta": "No reconocí a dónde quieres ir."}
    url_name, requiere_login = datos
    if requiere_login and not request.user.is_authenticated:
        return {"tipo": "redirigir", "respuesta": RESPUESTA_LOGIN_REQUERIDO, "url": reverse("usuarios:login")}
    try:
        return {"tipo": "redirigir", "respuesta": "Te llevo ahí.", "url": reverse(url_name)}
    except Exception:
        return {"tipo": "texto", "respuesta": "No pude generar esa ruta."}


def accion_agregar_favorito(request, nombre_producto=""):
    if not request.user.is_authenticated:
        return {"tipo": "redirigir", "respuesta": RESPUESTA_LOGIN_REQUERIDO, "url": reverse("usuarios:login")}
    
    from productos.models import Favorito
    producto = _buscar_producto_por_nombre(nombre_producto)
    if not producto:
        return {"tipo": "texto", "respuesta": f"No encontré un producto llamado '{nombre_producto}'."}
    
    favorito, creado = Favorito.objects.get_or_create(
        id_usuario=request.user,
        id_producto=producto
    )
    
    if creado:
        return {
            "tipo": "productos",
            "respuesta": f"❤️ Agregué '{producto.nombre}' a tus favoritos.",
            "productos": [_serializar_producto(producto)],
        }
    else:
        return {
            "tipo": "texto",
            "respuesta": f"'{producto.nombre}' ya está en tus favoritos.",
        }


def accion_eliminar_favorito(request, nombre_producto=""):
    if not request.user.is_authenticated:
        return {"tipo": "redirigir", "respuesta": RESPUESTA_LOGIN_REQUERIDO, "url": reverse("usuarios:login")}
    
    from productos.models import Favorito
    producto = _buscar_producto_por_nombre(nombre_producto)
    if not producto:
        return {"tipo": "texto", "respuesta": f"No encontré un producto llamado '{nombre_producto}'."}
    
    favorito = Favorito.objects.filter(
        id_usuario=request.user,
        id_producto=producto
    ).first()
    
    if not favorito:
        return {
            "tipo": "texto",
            "respuesta": f"'{producto.nombre}' no está en tus favoritos.",
        }
    
    favorito.delete()
    return {
        "tipo": "texto",
        "respuesta": f"🗑️ Eliminé '{producto.nombre}' de tus favoritos.",
    }


def accion_ayuda(request):
    return {
        "tipo": "texto",
        "respuesta": (
            "Puedo: buscar productos por nombre o por problema ('tengo pulgón', 'algo para la roya'), "
            "filtrar por categoría, ofertas u orgánicos, decirte precio o calificación, "
            "agregar/actualizar/eliminar productos de tu carrito, agregary eliminar productos de favoritos, "
            "llevarte a las ofertas especiales, al catálogo, a pagar ahora, a tus pedidos, notificaciones y favoritos, "
            "o ayudarte a cancelar un pedido o ver su detalle."
        ),
    }


ACCIONES_GEMINI = {
    "buscar_producto": accion_buscar_producto,
    "ver_precio": accion_ver_precio,
    "ver_calificacion": accion_ver_calificacion,
    "ver_ofertas": accion_ver_ofertas,
    "ver_organicos": accion_ver_organicos,
    "filtrar_categoria": accion_filtrar_categoria,
    "agregar_carrito": accion_agregar_carrito,
    "actualizar_carrito": accion_actualizar_carrito,
    "eliminar_carrito": accion_eliminar_carrito,
    "ir_a_pagina": accion_ir_a_pagina,
    "cancelar_pedido": accion_cancelar_pedido,
    "ver_detalle_pedido": accion_ver_detalle_pedido,
    "navegar": accion_navegar,
    "agregar_favorito": accion_agregar_favorito,
    "eliminar_favorito": accion_eliminar_favorito,
    "ayuda": accion_ayuda,
}


# ===================== VISTA PRINCIPAL DEL CHATBOT =====================

@require_POST
def chatbot_mensaje(request):
    try:
        data = json.loads(request.body)
        mensaje_original = data.get("mensaje", "")
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({"tipo": "texto", "respuesta": RESPUESTA_DEFAULT})

    if not mensaje_original.strip():
        return JsonResponse({"tipo": "texto", "respuesta": RESPUESTA_DEFAULT})

    # Respuesta rápida para el atajo "Ver precios" y preguntas equivalentes.
    resultado_precios = handler_precios_generales(_limpiar(mensaje_original), request)
    if resultado_precios:
        return JsonResponse(resultado_precios)

    # 1) Intentamos primero con Gemini (entiende lenguaje natural real)
    client = _get_gemini_client()
    if client is not None:
        try:
            resultado_intent = _interpretar_con_gemini(mensaje_original, client)
            if resultado_intent:
                nombre_funcion, args = resultado_intent
                ejecutor = ACCIONES_GEMINI.get(nombre_funcion)
                if ejecutor:
                    respuesta = ejecutor(request, **args)
                    if respuesta:
                        return JsonResponse(respuesta)
        except Exception:
            # Si Gemini falla (sin cuota gratuita del día, sin internet, error de API, etc.)
            # NO rompemos el chatbot: caemos al sistema de reglas de respaldo.
            pass

    # 2) Respaldo: sistema de reglas por palabras clave (siempre disponible, sin costo)
    texto = _limpiar(mensaje_original)
    texto = _normalizar_lenguaje_agricola(texto)

    for handler in HANDLERS:
        resultado = handler(texto, request)
        if resultado:
            return JsonResponse(resultado)

    return JsonResponse({"tipo": "texto", "respuesta": RESPUESTA_DEFAULT})
