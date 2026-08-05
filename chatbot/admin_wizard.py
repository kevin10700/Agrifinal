"""Asistente determinista para altas de producto desde el chat de administración."""
from decimal import Decimal, InvalidOperation
import re

from productos.models import Categoria
from .admin_acciones import accion_crear_producto

SESSION_KEY = 'admin_producto_borrador'


def _respuesta(texto):
    return {'respuesta': texto}


def iniciar(request, nombre):
    request.session[SESSION_KEY] = {'nombre': nombre.strip(), 'paso': 'categoria'}
    categorias = list(Categoria.objects.values_list('nombre', flat=True))
    opciones = ', '.join(categorias) if categorias else 'Aún no hay categorías'
    return _respuesta(f"Vamos a crear '{nombre.strip()}' paso a paso.\n\n1/8 ¿En qué categoría va? Categorías disponibles: {opciones}.")


def activo(request):
    return request.session.get(SESSION_KEY)


def cancelar(request):
    request.session.pop(SESSION_KEY, None)
    return _respuesta('Creación de producto cancelada. No se guardó ningún cambio.')


def _si(texto):
    return texto.strip().lower() in {'si', 'sí', 's', 'yes'}


def _no(texto):
    return texto.strip().lower() in {'no', 'n', 'omitir', 'ninguno'}


def _proponer_descripciones(data):
    """Propuesta segura: útil sin inventar variedad, rendimiento o certificaciones."""
    nombre = data['nombre']
    categoria = data['categoria'].lower()
    nombre_l = nombre.lower()
    if 'semilla' in nombre_l:
        corta = f"{nombre} para siembra y establecimiento del cultivo."
        larga = (
            f"{nombre} destinada a la siembra. Selecciona la variedad y la densidad de siembra "
            "de acuerdo con las condiciones de tu parcela y las recomendaciones técnicas locales. "
            "Conserva el empaque en un lugar fresco, seco y protegido de la humedad hasta su uso."
        )
    elif 'fertiliz' in categoria or any(p in nombre_l for p in ('urea', 'sulfato', 'nitrato', 'fosfato')):
        corta = f"{nombre} para complementar la nutrición de tus cultivos."
        larga = (f"{nombre} para manejo de nutrición vegetal. Aplica únicamente conforme a un análisis de suelo, "
                 "la etapa del cultivo y la recomendación de un especialista. Almacena cerrado, seco y fuera del alcance de menores.")
    else:
        corta = f"{nombre} para uso agrícola en la categoría {categoria}."
        larga = (f"{nombre} para labores agrícolas. Revisa la ficha técnica, compatibilidad y recomendaciones de uso "
                 "antes de aplicarlo o instalarlo. Conserva el producto en condiciones secas y seguras.")
    return corta, larga


def continuar(request, mensaje):
    data = activo(request)
    if not data:
        return None
    texto = mensaje.strip()
    if texto.lower() in {'cancelar', 'cancelar producto', 'salir'}:
        return cancelar(request)

    paso = data['paso']
    if paso == 'categoria':
        categoria = Categoria.objects.filter(nombre__iexact=texto).first() or Categoria.objects.filter(nombre__icontains=texto).first()
        if not categoria:
            return _respuesta('No encuentro esa categoría. Escribe una de las categorías disponibles o escribe “cancelar”.')
        data['categoria'] = categoria.nombre
        data['paso'] = 'precio_decision'
        request.session[SESSION_KEY] = data
        return _respuesta('2/8 ¿Deseas agregar precio ahora? Responde sí o no.')

    if paso == 'precio_decision':
        if _si(texto):
            data['paso'] = 'precio'
            request.session[SESSION_KEY] = data
            return _respuesta('Indica el precio de venta, sólo número. Ejemplo: 250.00')
        if _no(texto):
            data['precio'] = '0'
            data['paso'] = 'descripcion_corta_modo'
            request.session[SESSION_KEY] = data
            return _respuesta('3/8 Descripción corta: escribe “manual”, “chatbot” o “omitir”.')
        return _respuesta('Responde sí o no: ¿deseas agregar precio ahora?')

    if paso == 'precio':
        try:
            precio = Decimal(texto.replace('$', '').replace(',', ''))
            if precio < 0:
                raise InvalidOperation
        except (InvalidOperation, ValueError):
            return _respuesta('El precio debe ser un número mayor o igual a 0. Ejemplo: 250.00')
        data['precio'] = str(precio)
        data['paso'] = 'descripcion_corta_modo'
        request.session[SESSION_KEY] = data
        return _respuesta('3/8 Descripción corta: escribe “manual”, “chatbot” o “omitir”.')

    if paso == 'descripcion_corta_modo':
        modo = texto.lower()
        if modo == 'manual':
            data['paso'] = 'descripcion_corta'
            request.session[SESSION_KEY] = data
            return _respuesta('Escribe la descripción corta (máximo 300 caracteres).')
        if modo == 'chatbot':
            corta, larga = _proponer_descripciones(data)
            data['descripcion_corta'] = corta
            data['propuesta_larga'] = larga
            data['paso'] = 'descripcion_larga_modo'
            request.session[SESSION_KEY] = data
            return _respuesta(f"Propuesta corta: “{data['descripcion_corta']}”\n\n4/9 Descripción detallada: escribe “manual”, “chatbot” u “omitir”.")
        if modo == 'omitir':
            data['descripcion_corta'] = ''
            data['paso'] = 'descripcion_larga_modo'
            request.session[SESSION_KEY] = data
            return _respuesta('4/9 Descripción detallada: escribe “manual”, “chatbot” u “omitir”.')
        return _respuesta('Elige una opción: manual, chatbot u omitir.')

    if paso == 'descripcion_corta':
        if len(texto) > 300:
            return _respuesta('La descripción corta excede 300 caracteres. Redúcela e inténtalo de nuevo.')
        data['descripcion_corta'] = texto
        data['paso'] = 'descripcion_larga_modo'
        request.session[SESSION_KEY] = data
        return _respuesta('4/8 Descripción detallada: escribe “manual”, “chatbot” u “omitir”.')

    if paso == 'descripcion_larga_modo':
        modo = texto.lower()
        if modo == 'manual':
            data['paso'] = 'descripcion_larga'
            request.session[SESSION_KEY] = data
            return _respuesta('Escribe la descripción detallada del producto.')
        if modo == 'chatbot':
            data['descripcion_larga'] = data.get('propuesta_larga') or _proponer_descripciones(data)[1]
        elif modo == 'omitir':
            data['descripcion_larga'] = ''
        else:
            return _respuesta('Elige una opción: manual, chatbot u omitir.')
        data['paso'] = 'unidad'
        request.session[SESSION_KEY] = data
        return _respuesta(f"Propuesta detallada: “{data['descripcion_larga']}”\n\n5/9 ¿Cómo se vende? Elige: kg, unidad, libra, docena o caja.")

    if paso == 'descripcion_larga':
        data['descripcion_larga'] = texto
        data['paso'] = 'unidad'
        request.session[SESSION_KEY] = data
        return _respuesta('5/9 ¿Cómo se vende? Elige: kg, unidad, libra, docena o caja.')

    if paso == 'unidad':
        unidad = texto.lower()
        if unidad not in {'kg', 'unidad', 'libra', 'docena', 'caja'}:
            return _respuesta('Unidad no válida. Elige: kg, unidad, libra, docena o caja.')
        data['unidad_medida'] = unidad
        data['paso'] = 'stock_decision'
        request.session[SESSION_KEY] = data
        return _respuesta('6/9 ¿Deseas registrar stock inicial ahora? Responde sí o no.')

    if paso == 'stock_decision':
        if _si(texto):
            data['paso'] = 'stock'
            request.session[SESSION_KEY] = data
            return _respuesta('Indica la cantidad disponible en inventario.')
        if _no(texto):
            data['stock'] = 0
            data['paso'] = 'oferta_decision'
            request.session[SESSION_KEY] = data
            return _respuesta('7/9 ¿Deseas agregar precio de oferta? Responde sí o no.')
        return _respuesta('Responde sí o no: ¿deseas registrar stock inicial?')

    if paso == 'stock':
        try:
            stock = int(texto)
            if stock < 0: raise ValueError
        except ValueError:
            return _respuesta('El stock debe ser un entero mayor o igual a 0.')
        data['stock'] = stock
        data['paso'] = 'oferta_decision'
        request.session[SESSION_KEY] = data
        return _respuesta('7/9 ¿Deseas agregar precio de oferta? Responde sí o no.')

    if paso == 'oferta_decision':
        if _si(texto):
            data['paso'] = 'oferta'
            request.session[SESSION_KEY] = data
            return _respuesta('Indica el precio de oferta.')
        if _no(texto):
            data['paso'] = 'imagen_decision'
            request.session[SESSION_KEY] = data
            return _respuesta('8/9 ¿Deseas agregar una imagen principal? Responde sí o no. Si respondes sí, podrás adjuntarla junto con la confirmación final.')
        return _respuesta('Responde sí o no: ¿deseas agregar precio de oferta?')

    if paso == 'oferta':
        try:
            oferta = Decimal(texto.replace('$', '').replace(',', ''))
            if oferta < 0: raise InvalidOperation
        except (InvalidOperation, ValueError):
            return _respuesta('El precio de oferta debe ser un número mayor o igual a 0.')
        data['precio_oferta'] = str(oferta)
        data['paso'] = 'imagen_decision'
        request.session[SESSION_KEY] = data
        return _respuesta('8/9 ¿Deseas agregar una imagen principal? Responde sí o no. Si respondes sí, podrás adjuntarla junto con la confirmación final.')

    if paso == 'imagen_decision':
        if _si(texto):
            data['requiere_imagen'] = True
        elif _no(texto):
            data['requiere_imagen'] = False
        else:
            return _respuesta('Responde sí o no: ¿deseas agregar una imagen principal?')
        data['paso'] = 'confirmar'
        request.session[SESSION_KEY] = data
        return _resumen(data)

    if paso == 'confirmar':
        if not _si(texto):
            return _respuesta('No se creó el producto. Escribe “cancelar” para descartar el borrador o responde “sí” para confirmarlo.')
        if data.get('requiere_imagen') and not request.FILES.get('imagen'):
            return _respuesta('Elegiste agregar imagen. Adjunta el archivo y responde “sí” para confirmar; no se ha creado el producto todavía.')
        campos = {k: v for k, v in data.items() if k not in {'paso', 'propuesta_larga', 'requiere_imagen'}}
        response = accion_crear_producto(request, **campos)
        request.session.pop(SESSION_KEY, None)
        response['respuesta'] = response['respuesta'].replace('Ahora puedes adjuntar una imagen y decirme', 'Producto confirmado. Puedes adjuntar una imagen y decirme')
        return response


def _resumen(data):
    return _respuesta(
        '9/9 Revisa el producto antes de crearlo:\n'
        f"• Nombre: {data['nombre']}\n• Categoría: {data['categoria']}\n• Precio: ${data['precio']}\n"
        f"• Unidad: {data['unidad_medida']}\n• Stock: {data.get('stock', 0)}\n"
        f"• Oferta: ${data.get('precio_oferta', 'sin oferta')}\n"
        f"• Imagen: {'adjunta el archivo con tu respuesta “sí”' if data.get('requiere_imagen') else 'no incluida'}\n\n"
        '¿Confirmas la creación? Responde sí o cancelar.'
    )


def extraer_inicio(mensaje):
    match = re.match(r'^\s*(?:crea|crear|agrega|agregar|añade|anade)\s+(?:(?:un|el)\s+)?producto\s+(.+?)\s*[.!]?\s*$', mensaje, re.IGNORECASE)
    return match.group(1).strip(" '\"") if match else None
