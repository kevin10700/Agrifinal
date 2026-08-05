from django.contrib import admin

from .models import ZonaReparto


@admin.register(ZonaReparto)
class ZonaRepartoAdmin(admin.ModelAdmin):
    list_display = (
        "nombre", "municipio", "estado", "codigo_postal_inicio",
        "codigo_postal_fin", "costo_envio", "tiempo_entrega", "activo",
    )
    list_filter = ("activo", "estado")
    search_fields = ("nombre", "municipio", "codigo_postal_inicio", "codigo_postal_fin")
    list_editable = ("activo",)
    ordering = ("estado", "municipio", "codigo_postal_inicio")
