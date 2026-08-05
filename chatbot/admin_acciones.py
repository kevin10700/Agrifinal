"""
Ejecutores de las acciones administrativas invocadas por Gemini.
Cada función recibe `request` primero y luego los argumentos que Gemini extrajo.
Todas devuelven un dict serializable a JSON con al menos la clave "respuesta".
"""
from django.utils.text import slugify
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db import transaction

from productos.models import Producto, Categoria, Favorito
from pedidos.models import (
    Pedido, Entrega, Pago, ComentarioProducto, Notificacion
)
from admin_panel.models import (
    Proveedor, RolPanel, UsuarioPanel,
    Compra, ItemCompra, MovimientoInventario,
)
from shipping.models import ZonaReparto
from usuarios.models import Usuario, DireccionEnvio, TokenRecuperacion, TokenVerificacion

Usuario = get_user_model()


def _slug_unico(modelo, texto, campo_slug="slug"):
    base = slugify(texto)[:45] or "item"
    slug = base
    i = 1
    while modelo.objects.filter(**{campo_slug: slug}).exists():
        slug = f"{base}-{i}"
        i += 1
    return slug


def _buscar_producto(nombre):
    if not nombre:
        return None
    return Producto.objects.filter(nombre__icontains=nombre).first()


def _buscar_pedido(numero):
    if numero is None:
        return None
    return Pedido.objects.filter(id_pedido=numero).first()


# ===================== CATEGORÍAS =====================

def accion_crear_categoria(request, nombre="", icono="", orden=0):
    if Categoria.objects.filter(nombre__iexact=nombre).exists():
        return {"respuesta": f"⚠️ Ya existe una categoría llamada '{nombre}'."}
    cat = Categoria.objects.create(
        nombre=nombre,
        slug=_slug_unico(Categoria, nombre),
        icono=icono or "",
        orden=orden or 0,
    )
    return {"respuesta": f"✅ Categoría '{cat.nombre}' creada correctamente."}


def accion_editar_categoria(request, categoria_actual="", nuevo_nombre=None, icono=None, orden=None):
    cat = Categoria.objects.filter(nombre__icontains=categoria_actual).first()
    if not cat:
        return {"respuesta": f"No encontré la categoría '{categoria_actual}'."}
    if nuevo_nombre:
        cat.nombre = nuevo_nombre
    if icono is not None:
        cat.icono = icono
    if orden is not None:
        cat.orden = orden
    cat.save()
    return {"respuesta": f"✅ Categoría actualizada: '{cat.nombre}'."}


def accion_eliminar_categoria(request, nombre_categoria=""):
    cat = Categoria.objects.filter(nombre__icontains=nombre_categoria).first()
    if not cat:
        return {"respuesta": f"No encontré la categoría '{nombre_categoria}'."}
    nombre = cat.nombre
    total_productos = cat.productos.count()
    cat.delete()
    return {
        "respuesta": f"🗑️ Categoría '{nombre}' eliminada (junto con {total_productos} producto(s) asociados)."
    }


def accion_listar_categorias(request):
    categorias = Categoria.objects.all()
    if not categorias.exists():
        return {"respuesta": "No hay categorías registradas todavía."}
    lista = ", ".join(c.nombre for c in categorias)
    return {"respuesta": f"Categorías existentes: {lista}."}


# ===================== PRODUCTOS =====================

def accion_crear_producto(
    request, nombre="", categoria="", descripcion_corta="", descripcion_larga="",
    precio=None, precio_oferta=None, stock=0, unidad_medida="kg",
    es_destacado=False, es_nuevo=False, es_organico=False,
    temporada="", origen="", certificaciones="",
):
    if precio is None:
        return {"respuesta": "Necesito el precio del producto para crearlo."}
    cat = Categoria.objects.filter(nombre__icontains=categoria).first()
    if not cat:
        return {"respuesta": f"No encontré la categoría '{categoria}'. Créala primero o revisa el nombre."}

    producto = Producto.objects.create(
        nombre=nombre,
        slug=_slug_unico(Producto, nombre),
        descripcion_corta=descripcion_corta or nombre,
        descripcion_larga=descripcion_larga or descripcion_corta or nombre,
        precio=precio,
        precio_oferta=precio_oferta,
        stock=stock or 0,
        unidad_medida=unidad_medida or "kg",
        id_categoria=cat,
        es_destacado=bool(es_destacado),
        es_nuevo=bool(es_nuevo),
        es_organico=bool(es_organico),
        temporada=temporada or "",
        origen=origen or "",
        certificaciones=certificaciones or "",
    )
    imagen = request.FILES.get("imagen")
    if imagen:
        producto.imagen_principal = imagen
        producto.save(update_fields=["imagen_principal"])
    return {
        "respuesta": (
            f"✅ Producto '{producto.nombre}' creado en la categoría '{cat.nombre}' "
            f"a ${producto.precio}."
        ),
        "producto_id": producto.id_producto,
    }


def accion_editar_producto(request, nombre_producto="", **campos):
    producto = _buscar_producto(nombre_producto)
    if not producto:
        return {"respuesta": f"No encontré un producto llamado '{nombre_producto}'."}

    if campos.get("nuevo_nombre"):
        producto.nombre = campos["nuevo_nombre"]
    if campos.get("categoria"):
        cat = Categoria.objects.filter(nombre__icontains=campos["categoria"]).first()
        if cat:
            producto.id_categoria = cat
    for campo in ["descripcion_corta", "descripcion_larga", "unidad_medida", "temporada", "origen", "certificaciones"]:
        if campos.get(campo) is not None:
            setattr(producto, campo, campos[campo])
    if campos.get("precio") is not None:
        producto.precio = campos["precio"]
    if campos.get("quitar_oferta"):
        producto.precio_oferta = None
    elif campos.get("precio_oferta") is not None:
        producto.precio_oferta = campos["precio_oferta"]
    if campos.get("stock") is not None:
        producto.stock = campos["stock"]
    for campo in ["es_destacado", "es_nuevo", "es_organico"]:
        if campos.get(campo) is not None:
            setattr(producto, campo, campos[campo])

    producto.save()
    return {"respuesta": f"✅ Producto '{producto.nombre}' actualizado correctamente."}


def accion_eliminar_producto(request, nombre_producto=""):
    producto = _buscar_producto(nombre_producto)
    if not producto:
        return {"respuesta": f"No encontré un producto llamado '{nombre_producto}'."}
    nombre = producto.nombre
    producto.delete()
    return {"respuesta": f"🗑️ Producto '{nombre}' eliminado permanentemente."}


def accion_subir_imagen_producto(request, nombre_producto=""):
    producto = _buscar_producto(nombre_producto)
    if not producto:
        return {"respuesta": f"No encontré un producto llamado '{nombre_producto}'."}
    imagen = request.FILES.get("imagen")
    if not imagen:
        return {"respuesta": "No recibí ninguna imagen adjunta en el mensaje. Adjunta una imagen e intenta de nuevo."}
    producto.imagen_principal = imagen
    producto.save()
    return {"respuesta": f"🖼️ Imagen actualizada para '{producto.nombre}'."}


def accion_cambiar_stock(request, nombre_producto="", nuevo_stock=None):
    producto = _buscar_producto(nombre_producto)
    if not producto:
        return {"respuesta": f"No encontré un producto llamado '{nombre_producto}'."}
    if nuevo_stock is None or nuevo_stock < 0:
        return {"respuesta": "El nuevo stock debe ser un número mayor o igual a 0."}
    producto.stock = nuevo_stock
    producto.save()
    return {"respuesta": f"✅ Stock de '{producto.nombre}' actualizado a {nuevo_stock}."}


def accion_buscar_productos(request, termino="", bajo_stock=False):
    qs = Producto.objects.all()
    if bajo_stock:
        qs = qs.filter(stock__lte=5)
    if termino:
        qs = qs.filter(nombre__icontains=termino)
    qs = qs[:15]
    if not qs.exists():
        return {"respuesta": "No encontré productos con esos criterios."}
    lineas = [f"#{p.id_producto} {p.nombre} — stock: {p.stock} — ${p.get_precio_actual()}" for p in qs]
    return {"respuesta": "Productos encontrados:\n" + "\n".join(lineas)}


# ===================== PEDIDOS =====================

def accion_cambiar_estado_pedido(request, numero_pedido=None, nuevo_estado="", mensaje_extra=""):
    pedido = _buscar_pedido(numero_pedido)
    if not pedido:
        return {"respuesta": f"No encontré el pedido #{numero_pedido}."}
    pedido.actualizar_estado(nuevo_estado, mensaje_extra=mensaje_extra or "")
    return {"respuesta": f"✅ Pedido #{pedido.id_pedido} actualizado a '{pedido.get_estado_display()}'. Cliente notificado."}


def accion_ver_pedido(request, numero_pedido=None):
    pedido = _buscar_pedido(numero_pedido)
    if not pedido:
        return {"respuesta": f"No encontré el pedido #{numero_pedido}."}
    items = pedido.items.all()
    detalle_items = "\n".join(f"  - {i.cantidad} × {i.id_producto.nombre} (${i.precio_unitario})" for i in items)
    return {
        "respuesta": (
            f"Pedido #{pedido.id_pedido} — {pedido.id_usuario.username}\n"
            f"Estado: {pedido.get_estado_display()}\n"
            f"Total: ${pedido.total}\n"
            f"Cancelación: {pedido.get_estado_cancelacion_display()}\n"
            f"Ítems:\n{detalle_items or '  (sin ítems)'}"
        )
    }


def accion_listar_pedidos(request, estado=None):
    qs = Pedido.objects.all()
    if estado:
        qs = qs.filter(estado=estado)
    qs = qs[:15]
    if not qs.exists():
        return {"respuesta": "No hay pedidos con ese criterio."}
    lineas = [f"#{p.id_pedido} — {p.id_usuario.username} — {p.get_estado_display()} — ${p.total}" for p in qs]
    return {"respuesta": "Pedidos:\n" + "\n".join(lineas)}


def accion_resumen_operativo(request):
    pendientes = Pedido.objects.filter(estado="pendiente").count()
    preparando = Pedido.objects.filter(estado="preparando").count()
    pagos_pendientes = Pedido.objects.filter(estado_pago="pendiente").count()
    cancelaciones = Pedido.objects.filter(estado_cancelacion="solicitado").count()
    sin_guia = Pedido.objects.filter(estado_pago="pagado", entrega__numero_guia__isnull=True).count()
    return {
        "respuesta": (
            "Resumen operativo:\n"
            f"• Pedidos pendientes: {pendientes}\n"
            f"• En preparación: {preparando}\n"
            f"• Pagos por revisar: {pagos_pendientes}\n"
            f"• Cancelaciones por resolver: {cancelaciones}\n"
            f"• Pagados sin guía: {sin_guia}\n\n"
            "Puedes decir, por ejemplo: 'procesa el pedido 12 como pagado y preparando' "
            "o 'cambia los pedidos 12, 15 y 18 a confirmado'."
        )
    }


def accion_actualizar_pedidos_lote(request, numeros_pedido=None, nuevo_estado="", mensaje_extra=""):
    numeros = list(dict.fromkeys(numeros_pedido or []))
    if not numeros:
        return {"respuesta": "Indica al menos un número de pedido para actualizar."}
    pedidos = list(Pedido.objects.filter(id_pedido__in=numeros))
    encontrados = {pedido.id_pedido for pedido in pedidos}
    faltantes = sorted(set(numeros) - encontrados)
    with transaction.atomic():
        for pedido in pedidos:
            pedido.actualizar_estado(nuevo_estado, mensaje_extra=mensaje_extra or "")
    respuesta = f"✅ {len(pedidos)} pedido(s) actualizado(s) a '{nuevo_estado}'."
    if faltantes:
        respuesta += " No encontré: " + ", ".join(f"#{numero}" for numero in faltantes) + "."
    return {"respuesta": respuesta}


def accion_procesar_pedido(
    request, numero_pedido=None, marcar_pagado=False, referencia="", nuevo_estado="",
    transportista="", servicio="", numero_guia="", estado_entrega="", notas="",
):
    pedido = _buscar_pedido(numero_pedido)
    if not pedido:
        return {"respuesta": f"No encontré el pedido #{numero_pedido}."}

    with transaction.atomic():
        if marcar_pagado:
            pago, _ = Pago.objects.get_or_create(id_pedido=pedido)
            pago.marcar_pagado(referencia=referencia or "")

        if any([transportista, servicio, numero_guia, estado_entrega, notas]):
            entrega, _ = Entrega.objects.get_or_create(id_pedido=pedido)
            if transportista:
                entrega.transportista = transportista
                entrega.paqueteria = transportista
            if servicio:
                entrega.servicio = servicio
            if numero_guia:
                entrega.numero_guia = numero_guia
                entrega.tracking_number = numero_guia
                pedido.numero_rastreo = numero_guia
                pedido.save(update_fields=["numero_rastreo"])
            if notas:
                entrega.notas_entrega = notas
            entrega.save()
            if estado_entrega:
                entrega.actualizar_estado(estado_entrega, notes=notas or "")

        if nuevo_estado:
            pedido.actualizar_estado(nuevo_estado)

    return {"respuesta": f"✅ Pedido #{pedido.id_pedido} procesado correctamente."}


def accion_resolver_cancelacion(request, numero_pedido=None, aprobar=True, razon=""):
    pedido = _buscar_pedido(numero_pedido)
    if not pedido:
        return {"respuesta": f"No encontré el pedido #{numero_pedido}."}
    if pedido.estado_cancelacion != "solicitado":
        return {"respuesta": f"El pedido #{pedido.id_pedido} no tiene una solicitud de cancelación pendiente."}

    if aprobar:
        pedido.estado_cancelacion = "aprobado"
        pedido.fecha_aprobacion_cancelacion = timezone.now()
        pedido.save()
        pedido.actualizar_estado("cancelado")
        return {"respuesta": f"✅ Cancelación del pedido #{pedido.id_pedido} aprobada."}
    else:
        pedido.estado_cancelacion = "rechazado"
        pedido.razon_rechazo = razon or "No especificada"
        pedido.save()
        Notificacion.objects.create(
            id_usuario=pedido.id_usuario,
            id_pedido=pedido,
            mensaje=f"Tu solicitud de cancelación fue rechazada. Motivo: {pedido.razon_rechazo}",
        )
        return {"respuesta": f"❌ Cancelación del pedido #{pedido.id_pedido} rechazada. Cliente notificado."}


# ===================== ENTREGAS =====================

def accion_actualizar_entrega(request, numero_pedido=None, paqueteria=None, numero_guia=None, estado=None, notas=None):
    pedido = _buscar_pedido(numero_pedido)
    if not pedido:
        return {"respuesta": f"No encontré el pedido #{numero_pedido}."}

    entrega, _creada = Entrega.objects.get_or_create(id_pedido=pedido)
    if paqueteria:
        entrega.paqueteria = paqueteria
    if numero_guia:
        entrega.numero_guia = numero_guia
    if notas:
        entrega.notas_entrega = notas
    entrega.save()

    if estado:
        entrega.actualizar_estado(estado, notes=notas or "")

    transportista = entrega.transportista or entrega.paqueteria or "sin asignar"
    return {"respuesta": f"🚚 Entrega del pedido #{pedido.id_pedido} actualizada ({transportista}, guía: {entrega.numero_guia or 'sin asignar'})."}


# ===================== PAGOS =====================

def accion_marcar_pago_pagado(request, numero_pedido=None, referencia=""):
    pedido = _buscar_pedido(numero_pedido)
    if not pedido:
        return {"respuesta": f"No encontré el pedido #{numero_pedido}."}
    pago, _creado = Pago.objects.get_or_create(id_pedido=pedido)
    pago.marcar_pagado(referencia=referencia or "")
    return {"respuesta": f"✅ Pago del pedido #{pedido.id_pedido} marcado como pagado. Cliente notificado."}


def accion_marcar_pago_fallido_o_reembolsado(request, numero_pedido=None, nuevo_estado=""):
    pedido = _buscar_pedido(numero_pedido)
    if not pedido:
        return {"respuesta": f"No encontré el pedido #{numero_pedido}."}
    pago, _creado = Pago.objects.get_or_create(id_pedido=pedido)
    pago.estado = nuevo_estado
    if nuevo_estado == "reembolsado":
        pedido.requiere_reembolso = True
        pedido.fecha_reembolso = timezone.now()
        pedido.save()
    pago.save()
    return {"respuesta": f"Pago del pedido #{pedido.id_pedido} actualizado a '{pago.get_estado_display()}'."}


# ===================== COMENTARIOS =====================

def accion_aprobar_comentario(request, id_comentario=None):
    comentario = ComentarioProducto.objects.filter(id_comentario=id_comentario).first()
    if not comentario:
        return {"respuesta": f"No encontré el comentario #{id_comentario}."}
    comentario.aprobar()
    return {"respuesta": f"✅ Comentario #{comentario.id_comentario} aprobado y ahora es público."}


def accion_responder_comentario(request, id_comentario=None, respuesta=""):
    comentario = ComentarioProducto.objects.filter(id_comentario=id_comentario).first()
    if not comentario:
        return {"respuesta": f"No encontré el comentario #{id_comentario}."}
    comentario.responder(respuesta)
    return {"respuesta": f"✅ Respuesta agregada al comentario #{comentario.id_comentario}."}


def accion_listar_comentarios_pendientes(request):
    pendientes = ComentarioProducto.objects.filter(aprobado=False)[:15]
    if not pendientes.exists():
        return {"respuesta": "No hay comentarios pendientes de aprobación."}
    lineas = [f"#{c.id_comentario} — {c.id_producto.nombre} — {c.calificacion}★ — {c.id_usuario.username}" for c in pendientes]
    return {"respuesta": "Comentarios pendientes:\n" + "\n".join(lineas)}


# ===================== USUARIOS =====================

def accion_buscar_usuario(request, termino=""):
    usuarios = (
        Usuario.objects.filter(username__icontains=termino)
        | Usuario.objects.filter(email__icontains=termino)
        | Usuario.objects.filter(nombre__icontains=termino)
    ).distinct()[:10]
    if not usuarios.exists():
        return {"respuesta": f"No encontré usuarios que coincidan con '{termino}'."}
    lineas = [
        f"{u.username} — {u.nombre_completo} — {u.email} — {'activo' if u.is_active else 'inactivo'}"
        for u in usuarios
    ]
    return {"respuesta": "Usuarios encontrados:\n" + "\n".join(lineas)}


def accion_cambiar_estado_usuario(request, termino="", activo=None, es_staff=None):
    usuario = (
        Usuario.objects.filter(username__icontains=termino).first()
        or Usuario.objects.filter(email__icontains=termino).first()
    )
    if not usuario:
        return {"respuesta": f"No encontré un usuario que coincida con '{termino}'."}
    if activo is not None:
        usuario.is_active = activo
    if es_staff is not None:
        usuario.is_staff = es_staff
    usuario.save()
    return {"respuesta": f"✅ Usuario '{usuario.username}' actualizado (activo={usuario.is_active}, staff={usuario.is_staff})."}


# ===================== PROVEEDORES =====================

def accion_crear_proveedor(request, empresa="", rfc="", contacto="", correo="",
                           telefono="", whatsapp="", calle="", numero_exterior="",
                           colonia="", municipio="", estado="", codigo_postal="",
                           pagina_web="", tiempo_entrega=7, descuento=0,
                           condiciones_pago="contado", observaciones=""):
    if Proveedor.objects.filter(rfc__iexact=rfc).exists():
        return {"respuesta": f"⚠️ Ya existe un proveedor con RFC '{rfc}'."}
    prov = Proveedor.objects.create(
        empresa=empresa, rfc=rfc, contacto=contacto, correo=correo,
        telefono=telefono, whatsapp=whatsapp,
        calle=calle, numero_exterior=numero_exterior, colonia=colonia,
        municipio=municipio, estado=estado, codigo_postal=codigo_postal,
        pagina_web=pagina_web, tiempo_entrega=tiempo_entrega,
        descuento=descuento, condiciones_pago=condiciones_pago,
        observaciones=observaciones,
    )
    return {"respuesta": f"✅ Proveedor '{prov.empresa}' creado correctamente."}


def accion_editar_proveedor(request, proveedor_id=None, **campos):
    if not proveedor_id:
        return {"respuesta": "Necesito el ID del proveedor para editarlo."}
    prov = Proveedor.objects.filter(id_proveedor=proveedor_id).first()
    if not prov:
        return {"respuesta": f"No encontré el proveedor #{proveedor_id}."}
    for campo, valor in campos.items():
        if valor is not None and hasattr(prov, campo):
            setattr(prov, campo, valor)
    prov.save()
    return {"respuesta": f"✅ Proveedor '{prov.empresa}' actualizado correctamente."}


def accion_eliminar_proveedor(request, proveedor_id=None):
    if not proveedor_id:
        return {"respuesta": "Necesito el ID del proveedor para eliminarlo."}
    prov = Proveedor.objects.filter(id_proveedor=proveedor_id).first()
    if not prov:
        return {"respuesta": f"No encontré el proveedor #{proveedor_id}."}
    nombre = prov.empresa
    prov.delete()
    return {"respuesta": f"🗑️ Proveedor '{nombre}' eliminado correctamente."}


def accion_buscar_proveedores(request, termino=""):
    qs = Proveedor.objects.all()
    if termino:
        qs = qs.filter(empresa__icontains=termino) | qs.filter(rfc__icontains=termino)
    qs = qs[:15]
    if not qs.exists():
        return {"respuesta": "No encontré proveedores con esos criterios."}
    lineas = [f"#{p.id_proveedor} {p.empresa} — RFC: {p.rfc} — Contacto: {p.contacto}" for p in qs]
    return {"respuesta": "Proveedores encontrados:\n" + "\n".join(lineas)}


# ===================== NOTIFICACIONES =====================

def accion_crear_notificacion(request, usuario_id=None, pedido_id=None, mensaje="", leida=False):
    if not usuario_id or not pedido_id or not mensaje:
        return {"respuesta": "Para crear una notificación necesito: usuario_id, pedido_id y mensaje."}
    usuario = Usuario.objects.filter(id_usuario=usuario_id).first()
    if not usuario:
        return {"respuesta": f"No encontré el usuario #{usuario_id}."}
    pedido = Pedido.objects.filter(id_pedido=pedido_id).first()
    if not pedido:
        return {"respuesta": f"No encontré el pedido #{pedido_id}."}
    notif = Notificacion.objects.create(
        id_usuario=usuario, id_pedido=pedido,
        mensaje=mensaje, leida=bool(leida),
    )
    return {"respuesta": f"✅ Notificación #{notif.id_notificacion} creada para '{usuario.nombre_completo}'."}


def accion_listar_notificaciones(request, filtro=""):
    qs = Notificacion.objects.all()
    if filtro == "leidas":
        qs = qs.filter(leida=True)
    elif filtro == "no_leidas":
        qs = qs.filter(leida=False)
    qs = qs[:15]
    if not qs.exists():
        return {"respuesta": "No hay notificaciones con ese criterio."}
    lineas = [f"#{n.id_notificacion} — {n.id_usuario.nombre_completo} — {'✅' if n.leida else '❌'} — {n.mensaje[:50]}" for n in qs]
    return {"respuesta": "Notificaciones:\n" + "\n".join(lineas)}


def accion_eliminar_notificacion(request, notificacion_id=None):
    if not notificacion_id:
        return {"respuesta": "Necesito el ID de la notificación para eliminarla."}
    notif = Notificacion.objects.filter(id_notificacion=notificacion_id).first()
    if not notif:
        return {"respuesta": f"No encontré la notificación #{notificacion_id}."}
    notif.delete()
    return {"respuesta": f"🗑️ Notificación #{notificacion_id} eliminada correctamente."}


# ===================== ZONAS DE REPARTO =====================

def accion_crear_zona_reparto(request, nombre="", municipio="", estado="",
                               codigo_postal_inicio="", codigo_postal_fin="",
                               costo_envio=0, tiempo_entrega="", activo=True):
    zona = ZonaReparto.objects.create(
        nombre=nombre, municipio=municipio, estado=estado,
        codigo_postal_inicio=codigo_postal_inicio,
        codigo_postal_fin=codigo_postal_fin,
        costo_envio=costo_envio, tiempo_entrega=tiempo_entrega,
        activo=bool(activo),
    )
    return {"respuesta": f"✅ Zona de reparto '{zona.nombre}' creada en {zona.municipio}, {zona.estado}."}


def accion_listar_zonas_reparto(request):
    zonas = ZonaReparto.objects.all()[:15]
    if not zonas.exists():
        return {"respuesta": "No hay zonas de reparto registradas."}
    lineas = [f"  - {z.nombre} | {z.municipio}, {z.estado} | CP: {z.codigo_postal_inicio}-{z.codigo_postal_fin} | ${z.costo_envio}" for z in zonas]
    return {"respuesta": "Zonas de reparto:\n" + "\n".join(lineas)}


# ===================== ROLES =====================

def accion_listar_roles(request):
    roles = RolPanel.objects.all()[:15]
    if not roles.exists():
        return {"respuesta": "No hay roles de panel registrados."}
    lineas = [f"#{r.id} {r.nombre} — {'activo' if r.activo else 'inactivo'} — {r.descripcion[:50] or 'sin descripción'}" for r in roles]
    return {"respuesta": "Roles de panel:\n" + "\n".join(lineas)}


# ===================== AYUDA =====================

def accion_ayuda_admin(request):
    return {
        "respuesta": (
            "Puedo ayudarte a administrar Agrivale por completo:\n\n"
            "📦 **Productos:** crear, editar, eliminar, subir imagen, cambiar stock, buscar\n"
            "🏷️ **Categorías:** crear, editar, eliminar, listar\n"
            "📋 **Pedidos:** ver, listar, cambiar estado, procesar completo, lote, resolver cancelaciones\n"
            "🚚 **Entregas:** asignar paquetería, número de guía, estado\n"
            "💰 **Pagos:** marcar pagado, fallido o reembolsado\n"
            "⭐ **Comentarios:** aprobar, responder, listar pendientes\n"
            "👥 **Usuarios:** buscar, activar/desactivar, dar/quitar staff\n"
            "🏢 **Proveedores:** crear, editar, eliminar, buscar\n"
            "🔔 **Notificaciones:** crear, listar, eliminar\n"
            "📍 **Zonas de Reparto:** crear, editar, eliminar, listar\n"
            "🛡️ **Roles de Panel:** crear, editar, eliminar, listar\n"
            "📦 **Compras:** listar, ver detalle, crear, eliminar\n"
            "📋 **Inventario/Kardex:** listar movimientos\n"
            "📊 **Dashboard:** resumen general con KPIs\n"
            "👥 **Usuarios:** listar y buscar\n"
            "🔑 **Tokens:** listar verificación y recuperación\n"
            "📍 **Direcciones de Envío:** listar\n"
            "📊 **Reportes:** exportar ventas y productos en PDF o Excel\n\n"
            "Ejemplos:\n"
            "• 'crea el producto Fertilizante Orgánico en Fertilizantes a $250'\n"
            "• 'procesa el pedido 12 como pagado y preparando'\n"
            "• 'crea una notificación para el usuario 1 del pedido 1 diciendo \"tu pedido está listo\"'\n"
            "• 'crea el proveedor Agroquímicos SA de CV con RFC XXXX123456XXX'\n"
            "• 'crea una zona de reparto Centro en Morelia Michoacán CP 58000-58999 a $99'\n"
            "• 'exporta reporte de ventas de la semana en pdf'"
        )
    }


def accion_ver_favoritos(request, usuario=None):
    if usuario:
        user_obj = Usuario.objects.filter(username__icontains=usuario).first()
        if not user_obj:
            return {"respuesta": f"No encontré un usuario llamado '{usuario}'."}
        favoritos = Favorito.objects.filter(id_usuario=user_obj).select_related('id_producto')
        if not favoritos.exists():
            return {"respuesta": f"El usuario '{user_obj.username}' no tiene productos favoritos."}
        lineas = [f"  - {f.id_producto.nombre} (agregado el {f.fecha_agregado.strftime('%d/%m/%Y')})" for f in favoritos]
        return {"respuesta": f"Favoritos de '{user_obj.username}':\n" + "\n".join(lineas)}
    else:
        total_favoritos = Favorito.objects.count()
        if total_favoritos == 0:
            return {"respuesta": "No hay productos favoritos registrados en el sistema."}
        from django.db.models import Count
        productos_populares = (
            Favorito.objects.values('id_producto__nombre')
            .annotate(total=Count('id_favorito'))
            .order_by('-total')[:10]
        )
        lineas = [f"  - {p['id_producto__nombre']}: {p['total']} usuarios" for p in productos_populares]
        return {
            "respuesta": (
                f"Total de favoritos en el sistema: {total_favoritos}\n"
                f"Productos más favoritados:\n" + "\n".join(lineas)
            )
        }


def accion_exportar_reportes(request, tipo_reporte="", periodo="mes", formato="excel"):
    from django.urls import reverse
    periodos_validos = ["dia", "semana", "mes", "anio"]
    if periodo not in periodos_validos:
        return {"respuesta": f"Periodo no válido. Usa: {', '.join(periodos_validos)}"}
    formatos_validos = ["pdf", "excel"]
    if formato not in formatos_validos:
        return {"respuesta": f"Formato no válido. Usa: {', '.join(formatos_validos)}"}
    if tipo_reporte == "ventas":
        if formato == "pdf":
            url = reverse('pedidos:exportar_ventas_pdf', kwargs={'periodo': periodo})
        else:
            url = reverse('pedidos:exportar_ventas_excel', kwargs={'periodo': periodo})
        return {"respuesta": f"📊 Reporte de ventas ({periodo}) en {formato}: {url}", "url": url}
    elif tipo_reporte == "productos":
        if formato == "pdf":
            url = reverse('pedidos:exportar_productos_mas_vendidos_pdf', kwargs={'periodo': periodo})
        else:
            url = reverse('pedidos:exportar_productos_mas_vendidos', kwargs={'periodo': periodo})
        return {"respuesta": f"📦 Productos más vendidos ({periodo}) en {formato}: {url}", "url": url}
    else:
        return {
            "respuesta": f"Tipo de reporte no válido. Opciones: 'ventas' (PDF/Excel) o 'productos' (PDF/Excel).\n"
            f"Ejemplo: 'exporta reporte de ventas del mes en excel'"
        }


# ===================== COMPRAS =====================

def accion_listar_compras(request, estado=""):
    qs = Compra.objects.select_related('proveedor').all()
    if estado:
        qs = qs.filter(estado=estado)
    qs = qs[:15]
    if not qs.exists():
        return {"respuesta": "No hay compras registradas."}
    lineas = [
        f"#{c.id_compra} — {c.proveedor.empresa if c.proveedor else 'Producto Propio'} — "
        f"{c.get_estado_display()} — ${c.total} — {c.fecha_compra}"
        for c in qs
    ]
    return {"respuesta": "Compras:\n" + "\n".join(lineas)}


def accion_detalle_compra(request, compra_id=None):
    if not compra_id:
        return {"respuesta": "Necesito el ID de la compra para ver el detalle."}
    try:
        compra = Compra.objects.get(id_compra=compra_id)
    except Compra.DoesNotExist:
        return {"respuesta": f"No encontré la compra #{compra_id}."}
    items = ItemCompra.objects.filter(compra=compra).select_related('producto')
    detalle_items = "\n".join(
        f"  - {i.cantidad} × {i.producto.nombre} (${i.precio_unitario}) = ${i.subtotal}"
        for i in items
    )
    return {
        "respuesta": (
            f"Compra #{compra.id_compra}\n"
            f"Proveedor: {compra.proveedor.empresa if compra.proveedor else 'Producto Propio'}\n"
            f"Fecha: {compra.fecha_compra}\n"
            f"Factura: {compra.numero_factura or 'N/A'}\n"
            f"Estado: {compra.get_estado_display()}\n"
            f"Total: ${compra.total}\n"
            f"Ítems:\n{detalle_items or '  (sin ítems)'}"
        )
    }


def accion_crear_compra(request, proveedor_id=None, fecha_compra="",
                        numero_factura="", observaciones=""):
    if not fecha_compra:
        return {"respuesta": "Necesito la fecha de la compra (formato AAAA-MM-DD)."}
    proveedor = None
    if proveedor_id:
        proveedor = Proveedor.objects.filter(id_proveedor=proveedor_id).first()
        if not proveedor:
            return {"respuesta": f"No encontré el proveedor #{proveedor_id}."}
    compra = Compra.objects.create(
        proveedor=proveedor,
        es_producto_propio=(proveedor is None),
        fecha_compra=fecha_compra,
        numero_factura=numero_factura or "",
        observaciones=observaciones or "",
        estado='pendiente',
    )
    return {
        "respuesta": (
            f"✅ Compra #{compra.id_compra} creada en estado pendiente. "
            f"Registra los productos desde el panel en /panel/compras/crear/ "
            f"para actualizar stock y Kardex automáticamente."
        )
    }


def accion_eliminar_compra(request, compra_id=None):
    if not compra_id:
        return {"respuesta": "Necesito el ID de la compra para eliminarla."}
    try:
        compra = Compra.objects.get(id_compra=compra_id)
    except Compra.DoesNotExist:
        return {"respuesta": f"No encontré la compra #{compra_id}."}
    if compra.estado == 'recibida':
        return {
            "respuesta": (
                f"⚠️ La compra #{compra.id_compra} ya fue recibida y afectó el inventario. "
                f"Elimínala desde el panel para revertir el stock correctamente."
            )
        }
    compra.delete()
    return {"respuesta": f"🗑️ Compra #{compra_id} eliminada."}


# ===================== INVENTARIO (KARDEX) =====================

def accion_listar_movimientos_inventario(request, producto_id=None, tipo=""):
    qs = MovimientoInventario.objects.select_related('producto').all()
    if producto_id:
        qs = qs.filter(producto_id=producto_id)
    if tipo:
        qs = qs.filter(tipo=tipo)
    qs = qs[:20]
    if not qs.exists():
        return {"respuesta": "No hay movimientos de inventario registrados."}
    lineas = [
        f"#{m.id_movimiento} — {m.get_tipo_display()} — {m.producto.nombre} — "
        f"cant: {m.cantidad} — stock: {m.stock_anterior}→{m.stock_posterior} — {m.fecha_movimiento.strftime('%d/%m/%Y %H:%M')}"
        for m in qs
    ]
    return {"respuesta": "Movimientos de inventario (Kardex):\n" + "\n".join(lineas)}


# ===================== DASHBOARD =====================

def accion_dashboard_resumen(request):
    from django.db.models import Sum, Count
    from django.utils import timezone
    from datetime import timedelta

    hoy = timezone.now().date()
    inicio_mes = hoy.replace(day=1)

    total_usuarios = Usuario.objects.count()
    total_productos = Producto.objects.count()
    total_pedidos = Pedido.objects.count()
    pedidos_mes = Pedido.objects.filter(fecha_pedido__date__gte=inicio_mes).count()

    ventas_total = Pedido.objects.filter(estado_pago='pagado').aggregate(
        total=Sum('total')
    )['total'] or 0
    ventas_mes = Pedido.objects.filter(
        estado_pago='pagado', fecha_pedido__date__gte=inicio_mes
    ).aggregate(total=Sum('total'))['total'] or 0

    productos_sin_stock = Producto.objects.filter(stock=0).count()
    productos_bajo_stock = Producto.objects.filter(stock__lte=10, stock__gt=0).count()
    proveedores_activos = Proveedor.objects.filter(activo=True).count()
    compras_total = Compra.objects.count()

    return {
        "respuesta": (
            "📊 Resumen del dashboard:\n"
            f"• Usuarios: {total_usuarios}\n"
            f"• Productos: {total_productos} (sin stock: {productos_sin_stock}, bajo stock: {productos_bajo_stock})\n"
            f"• Pedidos: {total_pedidos} (este mes: {pedidos_mes})\n"
            f"• Ventas totales (pagado): ${ventas_total}\n"
            f"• Ventas del mes: ${ventas_mes}\n"
            f"• Proveedores activos: {proveedores_activos}\n"
            f"• Compras registradas: {compras_total}"
        )
    }


# ===================== USUARIOS (listado general) =====================

def accion_listar_usuarios(request, activo=None):
    qs = Usuario.objects.all().order_by('-date_joined')
    if activo is not None:
        qs = qs.filter(is_active=activo)
    qs = qs[:20]
    if not qs.exists():
        return {"respuesta": "No hay usuarios registrados."}
    lineas = [
        f"#{u.id_usuario} — {u.username} — {u.nombre_completo} — {u.email} — "
        f"{'activo' if u.is_active else 'inactivo'}"
        for u in qs
    ]
    return {"respuesta": "Usuarios:\n" + "\n".join(lineas)}


# ===================== ZONAS DE REPARTO (editar/eliminar) =====================

def accion_editar_zona_reparto(request, zona_id=None, nombre=None, municipio=None,
                               estado=None, codigo_postal_inicio=None,
                               codigo_postal_fin=None, costo_envio=None,
                               tiempo_entrega=None, activo=None):
    if not zona_id:
        return {"respuesta": "Necesito el ID de la zona de reparto para editarla."}
    try:
        zona = ZonaReparto.objects.get(id=zona_id)
    except ZonaReparto.DoesNotExist:
        return {"respuesta": f"No encontré la zona de reparto #{zona_id}."}
    if nombre is not None:
        zona.nombre = nombre
    if municipio is not None:
        zona.municipio = municipio
    if estado is not None:
        zona.estado = estado
    if codigo_postal_inicio is not None:
        zona.codigo_postal_inicio = codigo_postal_inicio
    if codigo_postal_fin is not None:
        zona.codigo_postal_fin = codigo_postal_fin
    if costo_envio is not None:
        zona.costo_envio = costo_envio
    if tiempo_entrega is not None:
        zona.tiempo_entrega = tiempo_entrega
    if activo is not None:
        zona.activo = activo
    zona.save()
    return {"respuesta": f"✅ Zona de reparto '{zona.nombre}' actualizada."}


def accion_eliminar_zona_reparto(request, zona_id=None):
    if not zona_id:
        return {"respuesta": "Necesito el ID de la zona de reparto para eliminarla."}
    try:
        zona = ZonaReparto.objects.get(id=zona_id)
    except ZonaReparto.DoesNotExist:
        return {"respuesta": f"No encontré la zona de reparto #{zona_id}."}
    nombre = zona.nombre
    zona.delete()
    return {"respuesta": f"🗑️ Zona de reparto '{nombre}' eliminada."}


# ===================== ROLES (crear/editar/eliminar) =====================

def accion_crear_rol(request, nombre="", descripcion=""):
    if not nombre:
        return {"respuesta": "El nombre del rol es obligatorio."}
    if RolPanel.objects.filter(nombre__iexact=nombre).exists():
        return {"respuesta": f"⚠️ Ya existe un rol llamado '{nombre}'."}
    rol = RolPanel.objects.create(
        nombre=nombre,
        descripcion=descripcion or "",
    )
    return {"respuesta": f"✅ Rol '{rol.nombre}' creado correctamente."}


def accion_editar_rol(request, rol_id=None, nombre=None, descripcion=None, activo=None):
    if not rol_id:
        return {"respuesta": "Necesito el ID del rol para editarlo."}
    try:
        rol = RolPanel.objects.get(id=rol_id)
    except RolPanel.DoesNotExist:
        return {"respuesta": f"No encontré el rol #{rol_id}."}
    if nombre is not None:
        rol.nombre = nombre
    if descripcion is not None:
        rol.descripcion = descripcion
    if activo is not None:
        rol.activo = activo
    rol.save()
    return {"respuesta": f"✅ Rol '{rol.nombre}' actualizado."}


def accion_eliminar_rol(request, rol_id=None):
    if not rol_id:
        return {"respuesta": "Necesito el ID del rol para eliminarlo."}
    try:
        rol = RolPanel.objects.get(id=rol_id)
    except RolPanel.DoesNotExist:
        return {"respuesta": f"No encontré el rol #{rol_id}."}
    if rol.usuarios.exists():
        return {"respuesta": f"⚠️ No se puede eliminar el rol '{rol.nombre}' porque tiene usuarios asignados."}
    nombre = rol.nombre
    rol.delete()
    return {"respuesta": f"🗑️ Rol '{nombre}' eliminado."}


# ===================== TOKENS =====================

def accion_listar_tokens_verificacion(request):
    qs = TokenVerificacion.objects.select_related('id_usuario').all()[:15]
    if not qs.exists():
        return {"respuesta": "No hay tokens de verificación registrados."}
    lineas = [
        f"#{t.id_token} — {t.id_usuario.username} — token: {t.token[:8]}… — {t.creado_en.strftime('%d/%m/%Y %H:%M')}"
        for t in qs
    ]
    return {"respuesta": "Tokens de verificación:\n" + "\n".join(lineas)}


def accion_listar_tokens_recuperacion(request, usados=None):
    qs = TokenRecuperacion.objects.select_related('id_usuario').all()
    if usados is not None:
        qs = qs.filter(usado=usados)
    qs = qs[:15]
    if not qs.exists():
        return {"respuesta": "No hay tokens de recuperación registrados."}
    lineas = [
        f"#{t.id_token} — {t.id_usuario.username} — token: {t.token[:8]}… — "
        f"{'usado' if t.usado else 'sin usar'} — {t.creado_en.strftime('%d/%m/%Y %H:%M')}"
        for t in qs
    ]
    return {"respuesta": "Tokens de recuperación:\n" + "\n".join(lineas)}


# ===================== DIRECCIONES DE ENVÍO =====================

def accion_listar_direcciones_envio(request, usuario=""):
    qs = DireccionEnvio.objects.select_related('id_usuario').all()
    if usuario:
        qs = qs.filter(
            Q(id_usuario__username__icontains=usuario)
            | Q(id_usuario__nombre__icontains=usuario)
        )
    qs = qs[:20]
    if not qs.exists():
        return {"respuesta": "No hay direcciones de envío registradas."}
    lineas = [
        f"#{d.id_direccion} — {d.id_usuario.username} — {d.nombre_referencia} — "
        f"{d.calle} {d.numero_exterior}, {d.colonia}, {d.municipio}, {d.estado} CP {d.codigo_postal}"
        for d in qs
    ]
    return {"respuesta": "Direcciones de envío:\n" + "\n".join(lineas)}


ACCIONES_ADMIN = {
    "crear_categoria": accion_crear_categoria,
    "editar_categoria": accion_editar_categoria,
    "eliminar_categoria": accion_eliminar_categoria,
    "listar_categorias": accion_listar_categorias,
    "crear_producto": accion_crear_producto,
    "editar_producto": accion_editar_producto,
    "eliminar_producto": accion_eliminar_producto,
    "subir_imagen_producto": accion_subir_imagen_producto,
    "cambiar_stock": accion_cambiar_stock,
    "buscar_productos": accion_buscar_productos,
    "cambiar_estado_pedido": accion_cambiar_estado_pedido,
    "ver_pedido": accion_ver_pedido,
    "listar_pedidos": accion_listar_pedidos,
    "resumen_operativo": accion_resumen_operativo,
    "actualizar_pedidos_lote": accion_actualizar_pedidos_lote,
    "procesar_pedido": accion_procesar_pedido,
    "resolver_cancelacion": accion_resolver_cancelacion,
    "actualizar_entrega": accion_actualizar_entrega,
    "marcar_pago_pagado": accion_marcar_pago_pagado,
    "marcar_pago_fallido_o_reembolsado": accion_marcar_pago_fallido_o_reembolsado,
    "aprobar_comentario": accion_aprobar_comentario,
    "responder_comentario": accion_responder_comentario,
    "listar_comentarios_pendientes": accion_listar_comentarios_pendientes,
    "buscar_usuario": accion_buscar_usuario,
    "cambiar_estado_usuario": accion_cambiar_estado_usuario,
    "ver_favoritos": accion_ver_favoritos,
    "exportar_reportes": accion_exportar_reportes,
    "crear_proveedor": accion_crear_proveedor,
    "editar_proveedor": accion_editar_proveedor,
    "eliminar_proveedor": accion_eliminar_proveedor,
    "buscar_proveedores": accion_buscar_proveedores,
    "crear_notificacion": accion_crear_notificacion,
    "listar_notificaciones": accion_listar_notificaciones,
    "eliminar_notificacion": accion_eliminar_notificacion,
    "crear_zona_reparto": accion_crear_zona_reparto,
    "listar_zonas_reparto": accion_listar_zonas_reparto,
    "listar_roles": accion_listar_roles,
    "ayuda_admin": accion_ayuda_admin,
    # Compras
    "listar_compras": accion_listar_compras,
    "detalle_compra": accion_detalle_compra,
    "crear_compra": accion_crear_compra,
    "eliminar_compra": accion_eliminar_compra,
    # Inventario / Kardex
    "listar_movimientos_inventario": accion_listar_movimientos_inventario,
    # Dashboard
    "dashboard_resumen": accion_dashboard_resumen,
    # Usuarios
    "listar_usuarios": accion_listar_usuarios,
    # Zonas de reparto
    "editar_zona_reparto": accion_editar_zona_reparto,
    "eliminar_zona_reparto": accion_eliminar_zona_reparto,
    # Roles
    "crear_rol": accion_crear_rol,
    "editar_rol": accion_editar_rol,
    "eliminar_rol": accion_eliminar_rol,
    # Tokens
    "listar_tokens_verificacion": accion_listar_tokens_verificacion,
    "listar_tokens_recuperacion": accion_listar_tokens_recuperacion,
    # Direcciones de envío
    "listar_direcciones_envio": accion_listar_direcciones_envio,
}
