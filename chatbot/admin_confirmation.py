"""Confirmación obligatoria para mutaciones administrativas no cubiertas por el alta de producto."""
from .admin_acciones import ACCIONES_ADMIN

SESSION_KEY = 'admin_accion_pendiente'
LECTURAS = {
    'listar_categorias', 'buscar_productos', 'ver_pedido', 'listar_pedidos',
    'resumen_operativo', 'listar_comentarios_pendientes', 'buscar_usuario',
    'ayuda_admin', 'listar_compras', 'detalle_compra',
    'listar_movimientos_inventario', 'dashboard_resumen', 'listar_usuarios',
    'listar_zonas_reparto', 'listar_roles', 'listar_notificaciones',
    'listar_tokens_verificacion', 'listar_tokens_recuperacion',
    'listar_direcciones_envio', 'ver_favoritos', 'buscar_proveedores',
    'exportar_reportes',
}
SIN_CONFIRMACION = {'subir_imagen_producto'}  # el archivo sólo vive durante la petición actual


def necesita_confirmacion(nombre):
    return nombre not in LECTURAS and nombre not in SIN_CONFIRMACION


def solicitar(request, nombre, args):
    request.session[SESSION_KEY] = {'nombre': nombre, 'args': args}
    detalle = ', '.join(f'{campo}: {valor}' for campo, valor in args.items() if valor not in ('', None)) or 'sin detalles'
    return {'respuesta': f'Acción preparada: {nombre.replace("_", " ")} ({detalle}).\n¿Confirmas ejecutar este cambio? Responde sí o cancelar.'}


def pendiente(request):
    return request.session.get(SESSION_KEY)


def continuar(request, mensaje):
    data = pendiente(request)
    if not data:
        return None
    texto = mensaje.strip().lower()
    if texto in {'cancelar', 'no', 'n', 'salir'}:
        request.session.pop(SESSION_KEY, None)
        return {'respuesta': 'Acción cancelada. No se aplicó ningún cambio.'}
    if texto not in {'si', 'sí', 's', 'confirmar'}:
        return {'respuesta': 'Responde sí para ejecutar la acción preparada o cancelar para descartarla.'}
    request.session.pop(SESSION_KEY, None)
    return ACCIONES_ADMIN[data['nombre']](request, **data['args'])
