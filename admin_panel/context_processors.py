from productos.models import Producto
from pedidos.models import Pedido, Notificacion


def alertas_sistema(request):
    """Context processor que expone las alertas del sistema en todas las plantillas.

    Las alertas ahora se basan en el modelo Notificacion (leida=False) en lugar
    de contar estados de la base de datos en cada render. Esto evita
    "notificaciones fantasma" que aparecen y desaparecen sin que el usuario las
    haya visto.
    """
    if not request.user.is_authenticated:
        return {'alertas': {}}

    #contar notificaciones no leidas del usuario actual
    notificaciones_no_leidas = Notificacion.objects.filter(
        id_usuario=request.user,
        leida=False
    ).count()

    #mantener los conteos de stock para el dashboard pero usar
    #notificacion como fuente única de verdad para el badge del bell
    alertas = {
        'productos_sin_stock': Producto.objects.filter(stock=0).count(),
        'productos_bajo_stock': Producto.objects.filter(stock__lte=10, stock__gt=0).count(),
        'pedidos_pendientes': Pedido.objects.filter(estado='pendiente').count(),
        'pedidos_cancelados': Pedido.objects.filter(estado='cancelado').count(),
        'notificaciones_no_leidas': notificaciones_no_leidas,
    }

    #el total del badge del bell solo notificaciones no leídas reales
    alertas['total'] = notificaciones_no_leidas

    return {'alertas': alertas}
