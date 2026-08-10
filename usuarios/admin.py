from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario, DireccionEnvio, TokenVerificacion, TokenRecuperacion


class DireccionInline(admin.TabularInline):
    model = DireccionEnvio
    fk_name = "usuario"
    extra = 0
    fields = [
        "nombre_referencia", "calle", "numero_exterior", "numero_interior",
        "colonia", "municipio", "estado", "codigo_postal",
        "telefono_contacto", "es_principal",
    ]


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    inlines = [DireccionInline]

    list_display = [
        "id", "username", "nombre", "apellido_paterno",
        "apellido_materno", "email", "edad_display",
        "correo_verificado", "is_active",
    ]
    list_filter = ["correo_verificado", "is_staff", "is_active"]
    search_fields = ["username", "email", "nombre", "apellido_paterno"]
    readonly_fields = ["edad_display", "date_joined", "last_login"]

    fieldsets = (
        ("Cuenta", {"fields": ("username", "password")}),
        ("Datos personales", {
            "fields": (
                "nombre", "apellido_paterno", "apellido_materno",
                "fecha_nacimiento", "edad_display",
                "email", "telefono", "foto_perfil",
            ),
        }),
        ("Roles y permisos", {
            "fields": (
                "correo_verificado",
                "is_active", "is_staff", "is_superuser",
                "groups", "user_permissions",
            ),
        }),
        ("Fechas", {
            "fields": ("date_joined", "last_login"),
            "classes": ("collapse",),
        }),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": (
                "username", "email",
                "nombre", "apellido_paterno", "apellido_materno",
                "fecha_nacimiento", "telefono",
                "password1", "password2",
            ),
        }),
    )

    def edad_display(self, obj):
        edad = obj.edad
        return f"{edad} años" if edad is not None else "—"
    edad_display.short_description = "Edad"


@admin.register(DireccionEnvio)
class DireccionEnvioAdmin(admin.ModelAdmin):
    list_display = [
        "id", "usuario", "nombre_referencia",
        "municipio", "estado", "es_principal",
    ]
    list_filter = ["estado", "es_principal"]
    search_fields = ["usuario__username", "municipio", "colonia"]


@admin.register(TokenVerificacion)
class TokenVerificacionAdmin(admin.ModelAdmin):
    list_display = ["id", "usuario", "creado_en"]
    readonly_fields = ["creado_en"]


@admin.register(TokenRecuperacion)
class TokenRecuperacionAdmin(admin.ModelAdmin):
    list_display = ["id", "usuario", "creado_en", "usado"]
    list_filter = ["usado"]
    readonly_fields = ["creado_en"]
