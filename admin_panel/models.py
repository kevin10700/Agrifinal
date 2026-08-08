from django.db import models
from django.contrib.auth.models import User, Group, Permission
from django.conf import settings


class Proveedor(models.Model):
    """
    Proveedor de productos de AGRIVale.
    Mantiene datos fiscales y comerciales separados del modelo Usuario.
    """
    id_proveedor = models.AutoField(primary_key=True)
    empresa = models.CharField("Empresa", max_length=200)
    rfc = models.CharField("RFC", max_length=13)
    contacto = models.CharField("Persona de contacto", max_length=150)
    correo = models.EmailField("Correo electrónico")
    telefono = models.CharField(max_length=15, blank=True)
    whatsapp = models.CharField(max_length=15, blank=True)

    # Dirección
    calle = models.CharField(max_length=200, blank=True)
    numero_exterior = models.CharField(max_length=10, blank=True)
    colonia = models.CharField(max_length=100, blank=True)
    municipio = models.CharField(max_length=100, blank=True)
    estado = models.CharField(max_length=100, blank=True)
    codigo_postal = models.CharField(max_length=10, blank=True)

    # Información comercial
    pagina_web = models.URLField(blank=True)
    tiempo_entrega = models.PositiveIntegerField("Tiempo de entrega (días)", default=7)
    descuento = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    condiciones_pago = models.CharField(
        max_length=20,
        choices=[("contado", "Contado"), ("credito", "Crédito"), ("mixto", "Mixto")],
        default="contado",
    )
    observaciones = models.TextField(blank=True)

    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "admin_panel_proveedor"
        verbose_name = "Proveedor"
        verbose_name_plural = "Proveedores"
        ordering = ["-fecha_creacion"]

    def __str__(self):
        return f"{self.empresa} ({self.rfc})"


class RolPanel(models.Model):
    """
    Rol específico para el Panel Administrativo de AGRIVALE.
    Este modelo permite gestionar roles personalizados para el panel.
    """
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    # Permisos específicos del panel
    puede_gestionar_productos = models.BooleanField(default=True)
    puede_gestionar_pedidos = models.BooleanField(default=True)
    puede_gestionar_clientes = models.BooleanField(default=True)
    puede_gestionar_proveedores = models.BooleanField(default=True)
    puede_gestionar_compras = models.BooleanField(default=True)
    puede_gestionar_pagos = models.BooleanField(default=True)
    puede_gestionar_envios = models.BooleanField(default=True)
    puede_gestionar_inventario = models.BooleanField(default=True)
    puede_gestionar_direcciones_envio = models.BooleanField(default=False)
    puede_ver_reportes = models.BooleanField(default=True)
    puede_ver_dashboard = models.BooleanField(default=True)
    puede_gestionar_configuracion = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'admin_panel_rol'
        verbose_name = 'Rol de Panel'
        verbose_name_plural = 'Roles de Panel'
        ordering = ['nombre']
    
    def __str__(self):
        return self.nombre


class UsuarioPanel(models.Model):
    """
    Relación entre Usuarios y Roles del Panel Administrativo.
    Permite asignar roles específicos del panel a usuarios.
    """
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='rol_panel',
        db_column='id_usuario'
    )
    rol = models.ForeignKey(
        RolPanel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='usuarios'
    )
    fecha_asignacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'admin_panel_usuario'
        verbose_name = 'Usuario de Panel'
        verbose_name_plural = 'Usuarios de Panel'
        ordering = ['-fecha_asignacion']
    
    def __str__(self):
        return f"{self.usuario.nombre_completo} - {self.rol.nombre if self.rol else 'Sin rol'}"


class Compra(models.Model):
    """Modelo para registrar compras a proveedores"""
    ESTADOS = [
        ('pendiente', 'Pendiente'),
        ('recibida', 'Recibida'),
        ('cancelada', 'Cancelada'),
    ]
    
    id_compra = models.AutoField(primary_key=True)
    proveedor = models.ForeignKey(
        Proveedor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='compras',
        db_column='id_proveedor'
    )
    es_producto_propio = models.BooleanField(default=False)
    fecha_compra = models.DateField()
    numero_factura = models.CharField(max_length=50, blank=True)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='pendiente')
    observaciones = models.TextField(blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'admin_panel_compra'
        verbose_name = 'Compra'
        verbose_name_plural = 'Compras'
        ordering = ['-fecha_creacion']
    
    def __str__(self):
        proveedor_nombre = self.proveedor.empresa if self.proveedor else "Producto Propio"
        return f"Compra #{self.id_compra} - {proveedor_nombre} - {self.fecha_compra}"


class ItemCompra(models.Model):
    """Items individuales de una compra"""
    id_item = models.AutoField(primary_key=True)
    compra = models.ForeignKey(
        Compra,
        on_delete=models.CASCADE,
        related_name='items',
        db_column='id_compra'
    )
    producto = models.ForeignKey(
        'productos.Producto',
        on_delete=models.CASCADE,
        related_name='items_compra',
        db_column='id_producto'
    )
    cantidad = models.IntegerField()
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    
    class Meta:
        db_table = 'admin_panel_item_compra'
        verbose_name = 'Item de Compra'
        verbose_name_plural = 'Items de Compra'
    
    def __str__(self):
        return f"{self.producto.nombre} x {self.cantidad}"
    
    def save(self, *args, **kwargs):
        #calcular subtotal
        self.subtotal = self.cantidad * self.precio_unitario
        super().save(*args, **kwargs)


class MovimientoInventario(models.Model):
    """Kardex - Historial completo de movimientos de inventario"""
    TIPOS_MOVIMIENTO = [
        ('entrada_compra', 'Entrada por Compra'),
        ('entrada_devolucion', 'Entrada por Devolución'),
        ('salida_venta', 'Salida por Venta'),
        ('salida_merma', 'Salida por Merma/Pérdida'),
        ('salida_ajuste', 'Salida por Ajuste de Inventario'),
        ('entrada_ajuste', 'Entrada por Ajuste de Inventario'),
    ]
    
    id_movimiento = models.AutoField(primary_key=True)
    producto = models.ForeignKey(
        'productos.Producto',
        on_delete=models.CASCADE,
        related_name='movimientos_inventario',
        db_column='id_producto'
    )
    tipo = models.CharField(max_length=30, choices=TIPOS_MOVIMIENTO)
    cantidad = models.IntegerField()
    stock_anterior = models.IntegerField()
    stock_posterior = models.IntegerField()
    costo_unitario = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    compra = models.ForeignKey(
        Compra,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='movimientos_inventario',
        db_column='id_compra'
    )
    pedido = models.ForeignKey(
        'pedidos.Pedido',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='movimientos_inventario',
        db_column='id_pedido'
    )
    
    observaciones = models.TextField(blank=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='movimientos_inventario',
        db_column='id_usuario'
    )
    fecha_movimiento = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'admin_panel_movimiento_inventario'
        verbose_name = 'Movimiento de Inventario'
        verbose_name_plural = 'Movimientos de Inventario'
        ordering = ['-fecha_movimiento']
    
    def __str__(self):
        return f"{self.get_tipo_display()} - {self.producto.nombre} ({self.cantidad})"


class HistorialProducto(models.Model):
    """Historial completo de cambios y actualizaciones de productos"""
    TIPOS_CAMBIO = [
        ('creacion', 'Creación de Producto'),
        ('actualizacion', 'Actualización de Datos'),
        ('cambio_precio', 'Cambio de Precio'),
        ('cambio_stock', 'Cambio de Stock'),
        ('cambio_estado', 'Cambio de Estado (Activo/Inactivo)'),
        ('cambio_costo', 'Cambio de Costo Promedio'),
        ('actualizacion_imagen', 'Actualización de Imagen'),
    ]
    
    id_historial = models.AutoField(primary_key=True)
    producto = models.ForeignKey(
        'productos.Producto',
        on_delete=models.CASCADE,
        related_name='historial',
        db_column='id_producto'
    )
    tipo_cambio = models.CharField(max_length=30, choices=TIPOS_CAMBIO)
    
    # Campos que cambiaron (JSON para flexibilidad)
    campos_cambiados = models.JSONField(default=dict, blank=True)
    # Ejemplo: {"precio": {"anterior": 10.00, "nuevo": 12.50}, "stock": {"anterior": 100, "nuevo": 104}}
    
    # Valores específicos para cambios de precio
    precio_anterior = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    precio_nuevo = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    costo_anterior = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    costo_nuevo = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Referencia al movimiento de inventario relacionado (si aplica)
    movimiento_inventario = models.ForeignKey(
        MovimientoInventario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='historiales',
        db_column='id_movimiento'
    )
    
    # Referencia a la compra relacionada (si aplica)
    compra = models.ForeignKey(
        Compra,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='historiales',
        db_column='id_compra'
    )
    
    # Referencia al pedido relacionado (si aplica)
    pedido = models.ForeignKey(
        'pedidos.Pedido',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='historiales',
        db_column='id_pedido'
    )
    
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='historiales_productos',
        db_column='id_usuario'
    )
    observaciones = models.TextField(blank=True)
    fecha_cambio = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'admin_panel_historial_producto'
        verbose_name = 'Historial de Producto'
        verbose_name_plural = 'Historiales de Productos'
        ordering = ['-fecha_cambio']
        indexes = [
            models.Index(fields=['producto', '-fecha_cambio']),
            models.Index(fields=['tipo_cambio', '-fecha_cambio']),
        ]
    
    def __str__(self):
        return f"{self.get_tipo_cambio_display()} - {self.producto.nombre} - {self.fecha_cambio.strftime('%d/%m/%Y %H:%M')}"
