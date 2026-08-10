from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class Usuario(AbstractUser):    
    first_name = None  
    last_name = None  
    nombre = models.CharField("Nombre(s)", max_length=100)
    apellido_paterno = models.CharField("Apellido paterno", max_length=100)
    apellido_materno = models.CharField(
        "Apellido materno", max_length=100, blank=True
    )

    # Datos personales
    fecha_nacimiento = models.DateField("Fecha de nacimiento", null=True, blank=True)
    telefono = models.CharField(max_length=15, blank=True)
    foto_perfil = models.ImageField(
        upload_to="perfiles/", blank=True, null=True
    )

    # Estado de cuenta
    correo_verificado = models.BooleanField(default=False)
    is_new_user = models.BooleanField(default=True)
    onboarding_completado = models.BooleanField(default=False)
    activo = models.BooleanField(default=True, verbose_name="Activo")

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email", "nombre", "apellido_paterno"]

    class Meta:
        db_table = "usuarios_usuario"
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"

    @property
    def nombre_completo(self):
        partes = [self.nombre, self.apellido_paterno]
        if self.apellido_materno:
            partes.append(self.apellido_materno)
        return " ".join(partes)

    @property
    def edad(self):
        """Calcula la edad a partir de fecha_nacimiento."""
        if not self.fecha_nacimiento:
            return None
        hoy = timezone.now().date()
        anios = hoy.year - self.fecha_nacimiento.year
        # Restar 1 si aún no ha pasado el cumpleaños este año
        if (hoy.month, hoy.day) < (
            self.fecha_nacimiento.month,
            self.fecha_nacimiento.day,
        ):
            anios -= 1
        return anios

    def __str__(self):
        return f"{self.nombre_completo} ({self.username})"


class RefreshToken(models.Model):
    """Registro revocable de tokens de renovación; nunca se guarda el JWT."""
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name="refresh_tokens")
    jti = models.CharField(max_length=64, unique=True, db_index=True)
    expira_en = models.DateTimeField()
    revocado_en = models.DateTimeField(null=True, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "usuarios_refresh_token"

    @property
    def vigente(self):
        return self.revocado_en is None and self.expira_en > timezone.now()


class DireccionEnvio(models.Model):
    # ✅ Cambiado: id_direccion → id (estándar)
    # Django manejará 'id' automáticamente
    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name="direcciones",
        db_column="usuario_id",  # Mantenemos el nombre de columna existente
    )

    nombre_referencia = models.CharField(
        "Nombre de referencia",
        max_length=100,
        help_text="Ej: Casa, Oficina",
    )
    calle = models.CharField(max_length=200)
    numero_exterior = models.CharField(max_length=10, blank=True)
    numero_interior = models.CharField(max_length=10, blank=True)
    colonia = models.CharField(max_length=100)
    municipio = models.CharField(max_length=100)
    estado = models.CharField(max_length=100)
    codigo_postal = models.CharField(max_length=10)
    pais = models.CharField(max_length=2, default="MX")
    referencias = models.TextField(blank=True)
    telefono_contacto = models.CharField(max_length=15, blank=True)
    es_principal = models.BooleanField(default=False)

    class Meta:
        db_table = "usuarios_direccion_envio"
        verbose_name = "Dirección de envío"
        verbose_name_plural = "Direcciones de envío"

    def __str__(self):
        return f"{self.nombre_referencia} – {self.calle} {self.numero_exterior}, {self.municipio}"

    @property
    def direccion_completa(self):
        partes = [self.calle, self.numero_exterior]
        if self.numero_interior:
            partes.append(f"Int. {self.numero_interior}")
        partes += [self.colonia, self.municipio, self.estado, self.codigo_postal, self.pais]
        return ", ".join(filter(None, partes))


class TokenVerificacion(models.Model):
    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name="tokens_verificacion",
        db_column="usuario_id",  # Mantenemos el nombre de columna existente
    )
    token = models.CharField(max_length=32, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "usuarios_token_verificacion"
        verbose_name = "Token de verificación"
        verbose_name_plural = "Tokens de verificación"

    def save(self, *args, **kwargs):
        import uuid
        if not self.token:
            self.token = uuid.uuid4().hex
        super().save(*args, **kwargs)

    @classmethod
    def generar_token(cls):
        """Genera un token único para verificación de correo"""
        import uuid
        return uuid.uuid4().hex

    def ha_expirado(self):
        from datetime import timedelta
        return timezone.now() > self.creado_en + timedelta(minutes=5)

    def __str__(self):
        return f"Token verificación – {self.usuario.username}"


class TokenRecuperacion(models.Model):
    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name="tokens_recuperacion",
        db_column="usuario_id",  # Mantenemos el nombre de columna existente
    )
    token = models.CharField(max_length=32, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    usado = models.BooleanField(default=False)

    class Meta:
        db_table = "usuarios_token_recuperacion"
        verbose_name = "Token de recuperación"
        verbose_name_plural = "Tokens de recuperación"

    def save(self, *args, **kwargs):
        import uuid
        if not self.token:
            self.token = uuid.uuid4().hex
        super().save(*args, **kwargs)

    def ha_expirado(self):
        from datetime import timedelta
        return timezone.now() > self.creado_en + timedelta(minutes=30)

    def __str__(self):
        return f"Token recuperación – {self.usuario.username}"