from django.contrib import admin
from .models import Pedido, ItemPedido, CarritoItem, Notificacion, Entrega, ComentarioProducto, Pago

# 1. Registro de Pedido
@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ["id_pedido", "id_usuario", "subtotal", "costo_envio", "total", "estado_pago", "transportista", "guia", "tracking", "fecha_pedido"]
    list_filter = ["estado", "estado_pago", "entrega__transportista", "fecha_pedido"]
    search_fields = ["id_pedido", "id_usuario__username"]
    readonly_fields = ["fecha_pedido", "subtotal", "costo_envio", "total"]

    @admin.display(description="Transportista", ordering="entrega__transportista")
    def transportista(self, obj):
        return getattr(obj.entrega, "transportista", "—")

    @admin.display(description="Guía", ordering="entrega__numero_guia")
    def guia(self, obj):
        return getattr(obj.entrega, "numero_guia", "—")

    @admin.display(description="Tracking", ordering="entrega__tracking_number")
    def tracking(self, obj):
        return getattr(obj.entrega, "tracking_number", "—")

# 2. Registro de Entrega
@admin.register(Entrega)
class EntregaAdmin(admin.ModelAdmin):
    list_display = ["id_pedido", "transportista", "servicio", "numero_guia", "tracking_number", "estado"]
    list_editable = ["transportista", "servicio", "numero_guia", "tracking_number", "estado"]
    list_filter = ["transportista", "estado"]
    search_fields = ["id_pedido__id_pedido", "numero_guia", "tracking_number"]
    fields = ["id_pedido", "transportista", "servicio", "paqueteria", "numero_guia", "tracking_number", "costo_envio", "respuesta_json", "estado", "ubicacion_actual", "notas_entrega"]

# 3. Registro de Pago (¡MUY IMPORTANTE PARA TU FLUJO!)
@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    list_display = ["id_pago", "id_pedido", "proveedor_pago", "referencia_pago", "metodo", "estado", "fecha_pago"]
    list_editable = ["estado"]
    list_filter = ["estado", "metodo"]
    search_fields = ["id_pedido__id_pedido", "referencia", "referencia_pago", "mercadopago_payment_id"]
    actions = ['confirmar_pagos'] # Habilita la acción en lote que vimos

    @admin.action(description="Marcar pagos seleccionados como PAGADOS")
    def confirmar_pagos(self, request, queryset):
        for pago in queryset:
            if pago.estado != 'pagado':
                pago.marcar_pagado(referencia="Confirmación Admin")
        self.message_user(request, "Los pagos seleccionados han sido confirmados y notificados.")

# 4. Registro de Notificación (Para monitoreo)
@admin.register(Notificacion)
class NotificacionAdmin(admin.ModelAdmin):
    list_display = ["id_usuario", "id_pedido", "leida", "fecha_creacion"]
    list_filter = ["leida", "fecha_creacion"]
    search_fields = ["id_usuario__username", "mensaje"]

# 5. Registro de Comentarios
@admin.register(ComentarioProducto)
class ComentarioProductoAdmin(admin.ModelAdmin):
    list_display = ["id_producto", "id_usuario", "calificacion", "aprobado"]
    list_editable = ["aprobado"]
    list_filter = ["aprobado", "calificacion"]
    search_fields = ["id_producto__nombre", "id_usuario__username"]

# Registro simple para los que no necesitan configuración especial
admin.site.register(ItemPedido)
admin.site.register(CarritoItem)
