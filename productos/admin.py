from django.contrib import admin
from .models import Categoria, Producto


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ["id_categoria", "nombre", "slug", "orden"]
    prepopulated_fields = {"slug": ("nombre",)}
    ordering = ["orden"]


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = [
        "id_producto", "nombre", "precio", "precio_oferta",
        "stock", "peso_kg", "id_categoria", "es_destacado", "es_organico",
    ]
    list_display_links = ["id_producto", "nombre"]  # ← permite clic en ambas columnas
    list_filter = ["id_categoria", "es_organico", "es_destacado", "es_nuevo"]
    search_fields = ["nombre", "descripcion_corta"]
    prepopulated_fields = {"slug": ("nombre",)}
    readonly_fields = ["fecha_creacion", "fecha_actualizacion", "vistas"]

    fieldsets = (
        ("Información básica", {
            "fields": ("nombre", "slug", "id_categoria", "descripcion_corta", "descripcion_larga"),
        }),
        ("Precio y stock", {
            "fields": ("precio", "precio_oferta", "stock", "unidad_medida"),
        }),
        ("Logística para envíos", {
            "fields": ("peso_kg", "alto_cm", "ancho_cm", "largo_cm"),
            "description": "Captura peso en kilogramos y dimensiones del empaque en centímetros.",
        }),
        ("Clasificación", {
            "fields": ("es_destacado", "es_nuevo", "es_organico"),
        }),
        ("Atributos agrícolas", {
            "fields": ("temporada", "origen", "certificaciones"),
            "classes": ("collapse",),
        }),
        ("Imagen", {
            "fields": ("imagen_principal",),
        }),
        ("Metadata", {
            "fields": ("vistas", "fecha_creacion", "fecha_actualizacion"),
            "classes": ("collapse",),
        }),
    )
