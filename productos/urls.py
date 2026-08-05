from django.urls import path
from . import views


app_name = 'productos'

urlpatterns = [
    path('', views.ProductoListView.as_view(), name='lista'),
    path('ofertas/', views.OfertasListView.as_view(), name='ofertas'),
    path('producto/<slug:slug>/', views.detalle_producto, name='detalle'),
    path('comentario/agregar/<int:producto_id>/', views.agregar_comentario, name='agregar_comentario'),
    path('comprar-ahora/<int:producto_id>/', views.comprar_ahora, name='comprar_ahora'),
    path('api/productos/', views.api_productos, name='api_productos'),
    path('favoritos/', views.lista_favoritos, name='favoritos'),
    path('favoritos/toggle/<int:producto_id>/', views.toggle_favorito, name='toggle_favorito'),
    path('favoritos/verificar/<int:producto_id>/', views.verificar_favorito, name='verificar_favorito'),
]
