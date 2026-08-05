from django.core.exceptions import ValidationError
from django.db import models


class ZonaReparto(models.Model):
    """Zona atendida directamente por el reparto propio de Agrivale."""

    nombre = models.CharField(max_length=120, unique=True)
    municipio = models.CharField(max_length=100)
    estado = models.CharField(max_length=100)
    codigo_postal_inicio = models.CharField(max_length=5)
    codigo_postal_fin = models.CharField(max_length=5)
    costo_envio = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tiempo_entrega = models.CharField(max_length=100)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Zona de reparto"
        verbose_name_plural = "Zonas de reparto"
        ordering = ("estado", "municipio", "codigo_postal_inicio")

    def clean(self):
        for field in ("codigo_postal_inicio", "codigo_postal_fin"):
            value = str(getattr(self, field) or "")
            if not value.isdigit() or len(value) != 5:
                raise ValidationError({field: "Debe ser un código postal de 5 dígitos."})
        if int(self.codigo_postal_inicio) > int(self.codigo_postal_fin):
            raise ValidationError({"codigo_postal_fin": "Debe ser mayor o igual al código postal inicial."})

    def __str__(self):
        return f"{self.nombre} ({self.codigo_postal_inicio}-{self.codigo_postal_fin})"
