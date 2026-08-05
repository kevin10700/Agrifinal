from django.contrib import admin
from .models import RolPanel, UsuarioPanel


@admin.register(RolPanel)
class RolPanelAdmin(admin.ModelAdmin):
    """Admin para gestionar roles del panel administrativo"""
    list_display = ['nombre', 'activo', 'puede_gestionar_productos', 'puede_gestionar_pedidos', 
                    'puede_gestionar_clientes', 'puede_gestionar_proveedores', 'fecha_creacion']
    list_filter = ['activo', 'fecha_creacion']
    search_fields = ['nombre', 'descripcion']
    list_editable = ['activo']
    readonly_fields = ['fecha_creacion', 'fecha_actualizacion']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('nombre', 'descripcion', 'activo')
        }),
        ('Permisos de Productos', {
            'fields': ('puede_gestionar_productos',)
        }),
        ('Permisos de Pedidos', {
            'fields': ('puede_gestionar_pedidos',)
        }),
        ('Permisos de Clientes', {
            'fields': ('puede_gestionar_clientes',)
        }),
        ('Permisos de Proveedores', {
            'fields': ('puede_gestionar_proveedores',)
        }),
        ('Permisos de Compras', {
            'fields': ('puede_gestionar_compras',)
        }),
        ('Permisos de Pagos', {
            'fields': ('puede_gestionar_pagos',)
        }),
        ('Permisos de Envíos', {
            'fields': ('puede_gestionar_envios', 'puede_gestionar_direcciones_envio')
        }),
        ('Permisos de Inventario', {
            'fields': ('puede_gestionar_inventario',)
        }),
        ('Permisos de Reportes', {
            'fields': ('puede_ver_reportes', 'puede_ver_dashboard')
        }),
        ('Permisos de Configuración', {
            'fields': ('puede_gestionar_configuracion',)
        }),
        ('Fechas', {
            'fields': ('fecha_creacion', 'fecha_actualizacion'),
            'classes': ('collapse',)
        }),
    )


@admin.register(UsuarioPanel)
class UsuarioPanelAdmin(admin.ModelAdmin):
    """Admin para gestionar usuarios del panel"""
    list_display = ['usuario', 'rol', 'fecha_asignacion']
    list_filter = ['rol', 'fecha_asignacion']
    search_fields = ['usuario__nombre_completo', 'usuario__email', 'rol__nombre']
    list_select_related = ['usuario', 'rol']
    readonly_fields = ['fecha_asignacion', 'fecha_actualizacion']
    
    fieldsets = (
        ('Usuario y Rol', {
            'fields': ('usuario', 'rol')
        }),
        ('Fechas', {
            'fields': ('fecha_asignacion', 'fecha_actualizacion'),
            'classes': ('collapse',)
        }),
    )