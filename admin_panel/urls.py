from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'admin_panel'

urlpatterns = [
    # Login del panel
    path('login/', views.login_view, name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/panel/login/'), name='logout'),  
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    # Productos
    path('productos/', views.productos_lista, name='productos_lista'),
    path('productos/crear/', views.producto_crear, name='producto_crear'),
    path('productos/editar/<int:id_producto>/', views.producto_editar, name='producto_editar'),
    path('productos/eliminar/<int:id_producto>/', views.producto_eliminar, name='producto_eliminar'),
    # Categorías
    path('categorias/', views.categorias_lista, name='categorias_lista'),
    path('categorias/crear/', views.categoria_crear, name='categoria_crear'),
    path('categorias/editar/<int:id_categoria>/', views.categoria_editar, name='categoria_editar'),
    # CORRECTO: name es 'eliminar_categoria'
    path('categorias/eliminar/<int:id_categoria>/', views.categoria_eliminar, name='eliminar_categoria'), 
    # Inventario
    path('inventario/', views.inventario, name='inventario'),
    path('inventario/movimientos/', views.inventario_movimientos, name='inventario_movimientos'),   
    # Pedidos
    path('pedidos/', views.pedidos_lista, name='pedidos_lista'),
    path('pedidos/<int:id_pedido>/', views.pedido_detalle, name='pedido_detalle'),   
    # Clientes
    path('clientes/', views.clientes_lista, name='clientes_lista'),
    path('clientes/<int:id_usuario>/', views.cliente_detalle, name='cliente_detalle'),    
    # Proveedores
    path('proveedores/', views.proveedores_lista, name='proveedores_lista'),
    path('proveedores/crear/', views.proveedor_crear, name='proveedor_crear'),
    path('proveedores/editar/<int:id_proveedor>/', views.proveedor_editar, name='proveedor_editar'),
    path('proveedores/eliminar/<int:id_proveedor>/', views.proveedor_eliminar, name='proveedor_eliminar'),    
    # Compras
    path('compras/', views.compras_lista, name='compras_lista'),
    path('compras/crear/', views.compra_crear, name='compra_crear'),    
    # Pagos
    path('pagos/', views.pagos_lista, name='pagos_lista'),    
    # Envíos
    path('envios/', views.envios_lista, name='envios_lista'),
    path('envios/zonas/', views.direcciones_envio, name='direcciones_envio'),
    path('envios/zonas/crear/', views.zona_reparto_crear, name='zona_reparto_crear'),
    path('envios/zonas/editar/<int:id_zona>/', views.zona_reparto_editar, name='zona_reparto_editar'),
    path('envios/zonas/eliminar/<int:id_zona>/', views.zona_reparto_eliminar, name='zona_reparto_eliminar'),    
    # Direcciones de envío de usuarios (CRUD)
    path('envios/direcciones-usuarios/', views.direcciones_envio_lista, name='direcciones_envio_lista'),
    path('envios/direcciones-usuarios/crear/', views.direccion_envio_crear, name='direccion_envio_crear'),
    path('envios/direcciones-usuarios/editar/<int:id_direccion>/', views.direccion_envio_editar, name='direccion_envio_editar'),
    path('envios/direcciones-usuarios/eliminar/<int:id_direccion>/', views.direccion_envio_eliminar, name='direccion_envio_eliminar'),    
    # Comentarios / Calificaciones
    path('comentarios/', views.comentarios_lista, name='comentarios_lista'),
    path('comentarios/aprobar/<int:id_comentario>/', views.comentario_aprobar, name='comentario_aprobar'),
    path('comentarios/rechazar/<int:id_comentario>/', views.comentario_rechazar, name='comentario_rechazar'),
    # Notificaciones del sistema (CRUD completo)
    path('notificaciones/', views.notificaciones_lista, name='notificaciones_lista'),
    path('notificaciones/crear/', views.notificacion_crear, name='notificacion_crear'),
    path('notificaciones/<int:id_notificacion>/', views.notificacion_detalle, name='notificacion_detalle'),
    path('notificaciones/<int:id_notificacion>/eliminar/', views.notificacion_eliminar, name='notificacion_eliminar'),
    path('notificaciones/marcar-leidas/', views.marcar_notificaciones_leidas, name='marcar_notificaciones_leidas'), 
    # Roles de Panel (CRUD)
    path('roles/', views.roles_lista, name='roles_lista'),
    path('roles/crear/', views.rol_crear, name='rol_crear'),
    path('roles/editar/<int:id_rol>/', views.rol_editar, name='rol_editar'),
    path('roles/eliminar/<int:id_rol>/', views.rol_eliminar, name='rol_eliminar'),
    # Usuarios de Panel (CRUD)
    path('usuarios-panel/', views.usuarios_panel_lista, name='usuarios_panel_lista'),
    path('usuarios-panel/crear/', views.usuario_panel_crear, name='usuario_panel_crear'),
    path('usuarios-panel/editar/<int:id_usuario_panel>/', views.usuario_panel_editar, name='usuario_panel_editar'),
    path('usuarios-panel/eliminar/<int:id_usuario_panel>/', views.usuario_panel_eliminar, name='usuario_panel_eliminar'),
    # Tokens de recuperación
    path('tokens/recuperacion/', views.tokens_recuperacion_lista, name='tokens_recuperacion_lista'),
    path('tokens/recuperacion/<int:id_token>/eliminar/', views.token_recuperacion_eliminar, name='token_recuperacion_eliminar'),
    
    # Tokens de verificación
    path('tokens/verificacion/', views.tokens_verificacion_lista, name='tokens_verificacion_lista'),
    path('tokens/verificacion/<int:id_token>/eliminar/', views.token_verificacion_eliminar, name='token_verificacion_eliminar'),
    
    # Logística
    path('logistica/', views.logistica, name='logistica'),
    
    # Reportes
    path('reportes/', views.reportes, name='reportes'),
    path('reportes/ventas/', views.reporte_ventas, name='reporte_ventas'),
    path('reportes/productos/', views.reporte_productos, name='reporte_productos'),
    
    # Chatbot IA
    path('chatbot/', views.chatbot_ia, name='chatbot_ia'),
    
    # Configuración
    path('configuracion/', views.configuracion, name='configuracion'),
    
    # Perfil
    path('perfil/', views.perfil, name='perfil'),
    path('clientes/eliminar/<int:id_usuario>/', views.cliente_eliminar, name='cliente_eliminar'),
    path('compras/obtener-unidad/<int:id_producto>/', views.obtener_unidad_producto, name='obtener_unidad_producto'),
    path('pedidos/cambiar-estado/<int:id_pedido>/', views.pedido_cambiar_estado, name='pedido_cambiar_estado'),
]