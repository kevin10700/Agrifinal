from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path("", include("productos.urls")),
    path('usuarios/', include('usuarios.urls')),
    path('api/', include('usuarios.api_urls')),
    path('pedidos/', include('pedidos.urls')),
    path('shipping/', include('shipping.urls')),
    path('payments/', include('payments.urls')),
    path('chatbot/', include('chatbot.urls')),
    path('panel/', include('admin_panel.urls')),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)