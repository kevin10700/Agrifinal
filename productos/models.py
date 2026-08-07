from django.db import models
from django.urls import reverse
from admin_panel.models import Proveedor
from cloudinary.models import CloudinaryField


class Categoria(models.Model):
    id_categoria = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, max_length=50)
    icono = models.CharField(max_length=50, blank=True)
    orden = models.IntegerField(default=0)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True) # Corregí el typo "actializacion"

    class Meta:
        db_table = "productos_categoria"
        verbose_name = "Categoría"
        verbose_name_plural = "Categorías"
        ordering = ["orden", "nombre"]

    def __str__(self):
        return self.nombre


class Producto(models.Model):
    UNIDADES_MEDIDA = [
        ("kg", "Kilogramo"),
        ("unidad", "Unidad"),
        ("libra", "Libra"),
        ("docena", "Docena"),
        ("caja", "Caja"),
    ]

    id_producto = models.AutoField(primary_key=True)

    # ===== INFORMACIÓN BÁSICA =====
    nombre = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, max_length=50)
    descripcion_corta = models.CharField(max_length=300)
    descripcion_larga = models.TextField()

    # ===== PRECIOS Y STOCK =====
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    precio_oferta = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    stock = models.IntegerField(default=0)
    costo_promedio = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        help_text="Costo promedio de adquisición (calculado automáticamente)"
    )
    unidad_medida = models.CharField(
        max_length=20, choices=UNIDADES_MEDIDA, default="kg"
    )

    # ===== DATOS LOGÍSTICOS =====
    peso_kg = models.DecimalField(max_digits=8, decimal_places=3, default=0)
    alto_cm = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    ancho_cm = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    largo_cm = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    # ===== CLASIFICACIÓN =====
    id_categoria = models.ForeignKey(
        Categoria,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="productos",
        db_column="id_categoria",
    )
    id_proveedor = models.ForeignKey(
        Proveedor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="productos",
        db_column="id_proveedor",
        verbose_name="Proveedor",
    )
    es_destacado = models.BooleanField(default=False)
    es_nuevo = models.BooleanField(default=False)
    es_organico = models.BooleanField(default=False)

    # ===== IMÁGENES =====
    imagen_principal = CloudinaryField('image', blank=True, null=True)

    # ===== ATRIBUTOS AGRÍCOLAS =====
    temporada = models.CharField(max_length=100, blank=True)
    origen = models.CharField(max_length=100, blank=True)
    certificaciones = models.CharField(max_length=200, blank=True)

    # ===== METADATA =====
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    vistas = models.IntegerField(default=0)

    # CAMBIO NUEVO: Campo para activar/desactivar el producto sin borrarlo
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = "productos_producto"
        verbose_name = "Producto"
        verbose_name_plural = "Productos"
        ordering = ["-fecha_creacion"]

    def __str__(self):
        return self.nombre

    def get_precio_actual(self):
        return self.precio_oferta if self.precio_oferta else self.precio

    def get_absolute_url(self):
        return reverse("productos:detalle", args=[self.slug])

    def get_calificacion_promedio(self):
        from pedidos.models import ComentarioProducto
        comentarios = ComentarioProducto.objects.filter(
            id_producto=self, aprobado=True
        )
        if comentarios.exists():
            total = sum(c.calificacion for c in comentarios)
            return round(total / comentarios.count(), 1)
        return 0

    def get_total_comentarios(self):
        from pedidos.models import ComentarioProducto
        return ComentarioProducto.objects.filter(
            id_producto=self, aprobado=True
        ).count()

    def get_distribucion_calificaciones(self):
        from pedidos.models import ComentarioProducto
        return {
            i: ComentarioProducto.objects.filter(
                id_producto=self, aprobado=True, calificacion=i
            ).count()
            for i in range(1, 6)
        }

    def get_porcentaje_calificacion(self, estrellas):
        total = self.get_total_comentarios()
        if total == 0:
            return 0
        from pedidos.models import ComentarioProducto
        count = ComentarioProducto.objects.filter(
            id_producto=self, aprobado=True, calificacion=estrellas
        ).count()
        return round((count / total) * 100)


class ProductoAgricola(models.Model):
    """Catálogo maestro independiente del inventario histórico de la tienda."""
    class CategoriaMaestra(models.TextChoices):
        FERTILIZANTES_QUIMICOS = 'FERTILIZANTES_QUIMICOS', 'Fertilizantes químicos'
        ABONOS_ORGANICOS = 'ABONOS_ORGANICOS', 'Abonos orgánicos'
        AGROQUIMICOS = 'AGROQUIMICOS', 'Agroquímicos'
        BOMBAS_RIEGO = 'BOMBAS_RIEGO', 'Bombas y riego'
        HERRAMIENTAS_PLASTICOS = 'HERRAMIENTAS_PLASTICOS', 'Herramientas y plásticos'

    id = models.IntegerField(primary_key=True)
    nombre = models.CharField(max_length=255, db_index=True)
    categoria = models.CharField(max_length=32, choices=CategoriaMaestra.choices, db_index=True)
    uso_principal = models.TextField()
    presentaciones = models.JSONField(default=list)
    precio_base = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    stock = models.IntegerField(default=0)
    imagen_url = models.URLField(blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'productos'
        ordering = ['id']


class Favorito(models.Model):
    """Modelo para guardar productos favoritos de los usuarios."""
    id_favorito = models.AutoField(primary_key=True)
    id_usuario = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.CASCADE,
        related_name='favoritos',
        db_column='id_usuario'
    )
    id_producto = models.ForeignKey(
        Producto,
        on_delete=models.CASCADE,
        related_name='favoritos',
        db_column='id_producto'
    )
    fecha_agregado = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'productos_favorito'
        verbose_name = 'Favorito'
        verbose_name_plural = 'Favoritos'
        unique_together = ['id_usuario', 'id_producto']
        ordering = ['-fecha_agregado']

    def __str__(self):
        return f"{self.id_usuario.username} - {self.id_producto.nombre}"