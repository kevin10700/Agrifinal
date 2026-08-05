"""
Configuración personalizada del panel de administración de Django
para mejorar la experiencia en dispositivos móviles.
"""
from django.contrib import admin
from django.contrib.admin.apps import AdminConfig


class AgrivaleAdminConfig(AdminConfig):
    """Configuración personalizada del admin de Agrivale"""
    default_site = 'appweb.admin.AgrivaleAdminSite'


class AgrivaleAdminSite(admin.AdminSite):
    """Sitio de administración personalizado para Agrivale"""
    
    site_header = "Panel de Administración - Agrivale"
    site_title = "Agrivale Admin"
    index_title = "Gestión del Sistema"
    
    # Configuración para mejorar la experiencia móvil
    enable_nav_sidebar = True
    
    def get_urls(self):
        """URLs personalizadas del admin"""
        from django.urls import path
        from django.contrib.admin.views.decorators import staff_member_required
        
        urls = super().get_urls()
        
        # Aquí se pueden agregar URLs personalizadas si es necesario
        custom_urls = [
            # Ejemplo: path('dashboard/', self.admin_view(self.dashboard_view), name='dashboard'),
        ]
        
        return custom_urls + urls


# Configuración del AdminSite por defecto
admin_site = AgrivaleAdminSite(name='agrivale_admin')

# Nota: Para usar esta configuración, actualizar appweb/__init__.py
# default_app_config = 'appweb.apps.AgriConfig'