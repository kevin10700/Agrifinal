from django.urls import path
from . import views

app_name = 'pedidos'

urlpatterns = [
    # Carrito
    path('carrito/', views.ver_carrito, name='ver_carrito'),
    path('carrito/agregar/<int:producto_id>/', views.agregar_al_carrito, name='agregar'),
    path('carrito/eliminar/<int:item_id>/', views.eliminar_del_carrito, name='eliminar'),
    path('carrito/actualizar/<int:item_id>/', views.actualizar_cantidad, name='actualizar'),
    
    # Checkout y pagos
    path('confirmar/', views.confirmar_pedido, name='confirmar'),
    path('instrucciones-pago/<int:pedido_id>/', views.instrucciones_pago, name='instrucciones_pago'),
    path('subir-comprobante/<int:id_pedido>/', views.subir_comprobante, name='subir_comprobante'),
    
    # Pedidos del usuario
    path('mis-pedidos/', views.mis_pedidos, name='mis_pedidos'),
    path('pedido/<int:pedido_id>/', views.detalle_pedido, name='detalle_pedido'),
    path('notificaciones/', views.notificaciones, name='notificaciones'),
    path('cancelar/<int:pedido_id>/', views.solicitar_cancelacion, name='solicitar_cancelacion'),
    
    # Admin
    path('admin/cancelaciones/', views.admin_gestionar_cancelaciones, name='admin_cancelaciones'),
    path('admin/cancelacion/<int:pedido_id>/', views.admin_aprobar_cancelacion, name='admin_aprobar_cancelacion'),
    path('admin/entrega/crear/<int:pedido_id>/', views.admin_crear_entrega, name='admin_crear_entrega'),
    path('admin/entrega/actualizar/<int:entrega_id>/', views.admin_actualizar_entrega, name='admin_actualizar_entrega'),
    path('admin/entrega/detalle/<int:entrega_id>/', views.admin_detalle_entrega, name='admin_detalle_entrega'),
    path('admin/entregas/', views.admin_entregas, name='admin_entregas'),
    
    # Reportes y exportaciones
    path('admin/reporte/ventas/pdf/<str:periodo>/', views.exportar_ventas_pdf, name='exportar_ventas_pdf'),
    path('admin/reporte/ventas/excel/<str:periodo>/', views.exportar_ventas_excel, name='exportar_ventas_excel'),
    path('admin/reporte/productos/pdf/<str:periodo>/', views.exportar_productos_mas_vendidos_pdf, name='exportar_productos_mas_vendidos_pdf'),
    path('admin/reporte/productos/excel/<str:periodo>/', views.exportar_productos_mas_vendidos, name='exportar_productos_mas_vendidos'),
    path('admin/reporte/', views.reporte_admin_page, name='reporte_admin_page'),
    
    # Stripe (Flujo seguro temporal)
    path('stripe/pagar-temp/', views.pagar_con_stripe_temp, name='pagar_con_stripe_temp'),
    path('stripe/exito/', views.stripe_exito, name='stripe_exito'),
    
    # Webhook de Stripe (Agregado para corregir el 404)
    path('webhook/', views.stripe_webhook, name='stripe_webhook'),
]