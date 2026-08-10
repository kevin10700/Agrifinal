from django.db import models
from django.conf import settings
from django.utils import timezone

from usuarios.models import Usuario, DireccionEnvio
from productos.models import Producto


# Pedido

class Pedido(models.Model):
    ESTADOS_PEDIDO = [
        ("pendiente", "Pendiente"),
        ("confirmado", "Confirmado"),
        ("preparando", "En preparación"),
        ("enviado", "Enviado"),
        ("entregado", "Entregado"),
        ("cancelado", "Cancelado"),
    ]

    ESTADOS_CANCELACION = [
        ("sin_solicitud", "Sin solicitud"),
        ("solicitado", "Cancelación solicitada"),
        ("aprobado", "Cancelación aprobada"),
        ("rechazado", "Cancelación rechazada"),
    ]

    ESTADOS_PAGO = [
        ("pendiente", "Pendiente de pago"),
        ("pagado", "Pagado"),
        ("rechazado", "Rechazado"),
        ("cancelado", "Cancelado"),
    ]

    id_pedido = models.AutoField(primary_key=True)

    id_usuario = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name="pedidos",
        db_column="id",
    )
    id_direccion_envio = models.ForeignKey(
        DireccionEnvio,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column="id_direccion_envio",
    )

    fecha_pedido = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(
        max_length=20, choices=ESTADOS_PEDIDO, default="pendiente"
    )
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    costo_envio = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    estado_pago = models.CharField(
        max_length=20, choices=ESTADOS_PAGO, default="pendiente"
    )

    # Datos de contacto al momento del pedido (desnormalización controlada)
    nombre_receptor = models.CharField(max_length=200, blank=True)
    telefono_contacto = models.CharField(max_length=15, blank=True)
    direccion_entrega = models.TextField(blank=True)

    # Seguimiento
    numero_rastreo = models.CharField(max_length=100, blank=True)
    notas = models.TextField(blank=True)
    mensaje_estado = models.TextField(
        blank=True,
        help_text="Mensaje adicional para el cliente sobre su pedido",
    )

    # Cancelación
    estado_cancelacion = models.CharField(
        max_length=20,
        choices=ESTADOS_CANCELACION,
        default="sin_solicitud",
    )
    motivo_cancelacion = models.TextField(blank=True)
    razon_rechazo = models.TextField(blank=True)
    fecha_solicitud_cancelacion = models.DateTimeField(null=True, blank=True)
    fecha_aprobacion_cancelacion = models.DateTimeField(null=True, blank=True)

    # Reembolso
    requiere_reembolso = models.BooleanField(default=False)
    fecha_reembolso = models.DateTimeField(null=True, blank=True)
    referencia_reembolso = models.CharField(max_length=100, blank=True)

    class Meta:
        db_table = "pedidos_pedido"
        verbose_name = "Pedido"
        verbose_name_plural = "Pedidos"
        ordering = ["-fecha_pedido"]

    def __str__(self):
        return f"Pedido #{self.id_pedido} – {self.id_usuario.username}"

    # Métodos de negocio
    def actualizar_estado(self, nuevo_estado, mensaje_extra=""):
        self.estado = nuevo_estado
        mensajes = {
            "pendiente": "Su pedido ha sido registrado. Pronto nos comunicaremos.",
            "confirmado": "Su pedido ha sido confirmado.",
            "preparando": "Estamos empacando sus productos frescos.",
            "enviado": "¡Su pedido está en camino!",
            "entregado": "Su pedido ha sido entregado. ¡Gracias por comprar en Agrivale!",
            "cancelado": "Su pedido ha sido cancelado. Contáctenos al 7297159725.",
        }
        mensaje = mensajes.get(
            nuevo_estado,
            f"El estado cambió a: {self.get_estado_display()}",
        )
        if mensaje_extra:
            mensaje += f"\n\n Nota: {mensaje_extra}"
        self.mensaje_estado = mensaje
        self.save()
        
        Notificacion.objects.create(
            id_usuario=self.id_usuario,
            id_pedido=self,
            mensaje=mensaje,
        )

        # --- CÓDIGO PARA ENVÍO DE CORREO ---
        if nuevo_estado == 'enviado':
            try:
                from django.core.mail import send_mail
                from django.conf import settings
                
                # Intentamos obtener los datos de la entrega si existen
                guia = self.entrega.numero_guia if hasattr(self, 'entrega') else "Pendiente"
                paqueteria = (
                    self.entrega.transportista or self.entrega.paqueteria
                    if hasattr(self, 'entrega')
                    else "nuestra paquetería"
                )
                
                send_mail(
                    '¡Tu pedido Agrivale está en camino!',
                    f'Hola {self.id_usuario.username}, tu pedido #{self.id_pedido} ya va en camino por {paqueteria}. Tu número de guía es: {guia}.',
                    settings.DEFAULT_FROM_EMAIL,
                    [self.id_usuario.email],
                    fail_silently=False,
                )
            except Exception as e:
                print(f"Error al enviar correo: {e}")

# Ítem de pedido

class ItemPedido(models.Model):
    id_item_pedido = models.AutoField(primary_key=True)

    id_pedido = models.ForeignKey(
        Pedido,
        on_delete=models.CASCADE,
        related_name="items",
        db_column="id_pedido",
    )
    id_producto = models.ForeignKey(
        Producto,
        on_delete=models.CASCADE,
        db_column="id_producto",
    )
    cantidad = models.IntegerField()
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = "pedidos_item_pedido"
        verbose_name = "Ítem de pedido"
        verbose_name_plural = "Ítems de pedido"

    def get_subtotal(self):
        return self.precio_unitario * self.cantidad

    def __str__(self):
        return f"{self.cantidad} × {self.id_producto.nombre}"

# Carrito de compras
class CarritoItem(models.Model):
    id_carrito_item = models.AutoField(primary_key=True)

    id_usuario = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name="carrito_items",
        db_column="id",
    )
    id_producto = models.ForeignKey(
        Producto,
        on_delete=models.CASCADE,
        db_column="id_producto",
    )
    cantidad = models.IntegerField(default=1)
    fecha_agregado = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "pedidos_carrito_item"
        verbose_name = "Ítem de carrito"
        verbose_name_plural = "Ítems de carrito"

    def get_subtotal(self):
        return self.id_producto.get_precio_actual() * self.cantidad

    def __str__(self):
        return f"{self.cantidad} × {self.id_producto.nombre} ({self.id_usuario.username})"

# Notificación

class Notificacion(models.Model):
    id_notificacion = models.AutoField(primary_key=True)

    id_usuario = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name="notificaciones",
        db_column="id",
    )
    id_pedido = models.ForeignKey(
        Pedido,
        on_delete=models.CASCADE,
        related_name="notificaciones",
        db_column="id_pedido",
    )
    mensaje = models.TextField()
    leida = models.BooleanField(default=False)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "pedidos_notificacion"
        verbose_name = "Notificación"
        verbose_name_plural = "Notificaciones"
        ordering = ["-fecha_creacion"]

    def __str__(self):
        return f"Notificación #{self.id_notificacion} – {self.id_usuario.username}"

# Entrega
class Entrega(models.Model):
    ESTADOS_ENTREGA = [
        ("pendiente", "Pendiente de asignación"),
        ("en_ruta", "En camino"),
        ("en_transito", "En tránsito"),
        ("entregado", "Entregado"),
        ("incidente", "Incidente reportado"),
    ]

    id_entrega = models.AutoField(primary_key=True)

    id_pedido = models.OneToOneField(
        Pedido,
        on_delete=models.CASCADE,
        related_name="entrega",
        db_column="id_pedido",
    )

    # Campo heredado para compatibilidad con el flujo actual. Los nuevos
    # transportistas se guardarán en ``transportista`` sin opciones fijas.
    paqueteria = models.CharField(
        max_length=50,
        default='',
        db_column='paqueteria'
    )

    transportista = models.CharField(max_length=100, blank=True)
    servicio = models.CharField(max_length=100, blank=True)
    
    # Campo obligatorio para rastrear los envíos de terceros
    numero_guia = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        db_column='numero_guia',
        help_text="Número de rastreo proporcionado por la paquetería externa"
    )
    tracking_number = models.CharField(max_length=100, blank=True)
    costo_envio = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    respuesta_json = models.JSONField(default=dict, blank=True)

    estado = models.CharField(
        max_length=20, choices=ESTADOS_ENTREGA, default="pendiente"
    )
    fecha_asignacion = models.DateTimeField(null=True, blank=True)
    fecha_envio = models.DateTimeField(null=True, blank=True)
    fecha_entrega = models.DateTimeField(null=True, blank=True)
    ubicacion_actual = models.CharField(max_length=255, blank=True)
    notas_entrega = models.TextField(blank=True)

    class Meta:
        db_table = "pedidos_entrega"
        verbose_name = "Entrega"
        verbose_name_plural = "Entregas"

    def __str__(self):
        return f"Entrega #{self.id_entrega} – {self.paqueteria} (Pedido #{self.id_pedido_id})"

    def actualizar_estado(self, nuevo_estado, notes=""):
        self.estado = nuevo_estado
        mapeo = {
            "pendiente": "pendiente",
            "en_ruta": "enviado",
            "en_transito": "enviado",
            "entregado": "entregado",
            "incidente": "pendiente",
        }
        pedido = self.id_pedido
        if nuevo_estado in mapeo:
            pedido.estado = mapeo[nuevo_estado]
            pedido.save()
        if notes:
            self.notas_entrega = notes
        self.save()
        
        mensajes = {
            "pendiente": "Su pedido está pendiente de procesamiento logístico.",
            "en_ruta": f"¡Su pedido ya va en camino por {self.transportista or self.paqueteria or 'la paquetería'}! Guía: {self.numero_guia if self.numero_guia else 'Pendiente'}",
            "en_transito": f"Su pedido está en tránsito por {self.transportista or self.paqueteria or 'la paquetería'}.",
            "entregado": "¡Su pedido fue entregado exitosamente por la paquetería! Gracias por comprar en Agrivale.",
            "incidente": "Hubo un incidente con la paquetería en su entrega. Nos comunicaremos con ellos.",
        }
        Notificacion.objects.create(
            id_usuario=pedido.id_usuario,
            id_pedido=pedido,
            mensaje=mensajes.get(nuevo_estado, "Estado de entrega actualizado."),
        )

# Comentario de producto
class ComentarioProducto(models.Model):
    CALIFICACIONES = [
        (1, "1 estrella – Muy malo"),
        (2, "2 estrellas – Malo"),
        (3, "3 estrellas – Regular"),
        (4, "4 estrellas – Bueno"),
        (5, "5 estrellas – Excelente"),
    ]

    id_comentario = models.AutoField(primary_key=True)

    id_producto = models.ForeignKey(
        Producto,
        on_delete=models.CASCADE,
        related_name="comentarios",
        db_column="id_producto",
    )
    id_usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="comentarios",
        db_column="id",
    )

    calificacion = models.IntegerField(choices=CALIFICACIONES)
    titulo = models.CharField(max_length=200, blank=True)
    comentario = models.TextField()

    imagen_1 = models.ImageField(upload_to="comentarios/", blank=True, null=True)
    imagen_2 = models.ImageField(upload_to="comentarios/", blank=True, null=True)
    imagen_3 = models.ImageField(upload_to="comentarios/", blank=True, null=True)

    compra_verificada = models.BooleanField(default=False)
    aprobado = models.BooleanField(default=False)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_aprobacion = models.DateTimeField(null=True, blank=True)

    respuesta_vendedor = models.TextField(blank=True)
    fecha_respuesta = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "pedidos_comentario_producto"
        verbose_name = "Comentario"
        verbose_name_plural = "Comentarios"
        ordering = ["-fecha_creacion"]

    def __str__(self):
        return f"{self.id_usuario.username} – {self.id_producto.nombre} ({self.calificacion}★)"

    def aprobar(self):
        self.aprobado = True
        self.fecha_aprobacion = timezone.now()
        self.save()

    def responder(self, respuesta):
        self.respuesta_vendedor = respuesta
        self.fecha_respuesta = timezone.now()
        self.save()
# Pago
class Pago(models.Model):
    METODOS_PAGO = [
        ("transferencia", "Transferencia Bancaria"),
        ("oxxo", "Pago en OXXO"),
        ("tarjeta", "Stripe"),
        ("mercadopago", "Mercado Pago"),
    ]

    ESTADOS_PAGO = [
        ("pendiente", "Pendiente de pago"),
        ("pagado", "Pagado"),
        ("fallido", "Fallido"),
        ("reembolsado", "Reembolsado"),
    ]

    id_pago = models.AutoField(primary_key=True)
    id_pedido = models.OneToOneField(
        Pedido,
        on_delete=models.CASCADE,
        related_name="pago",
        db_column="id_pedido",
    )
    proveedor_pago = models.CharField(max_length=50, default="manual")
    metodo = models.CharField(max_length=20, choices=METODOS_PAGO, default="transferencia")
    estado = models.CharField(max_length=20, choices=ESTADOS_PAGO, default="pendiente")
    
    # Campo para subir el ticket/foto del pago
    comprobante = models.ImageField(upload_to='comprobantes/', blank=True, null=True)

    # Datos de tarjeta
    ultimos_digitos = models.CharField(max_length=4, blank=True)
    nombre_titular = models.CharField(max_length=200, blank=True)
    fecha_expiracion = models.CharField(max_length=7, blank=True)
    
    referencia_oxxo = models.CharField(max_length=18, blank=True, null=True)
    fecha_vencimiento_oxxo = models.DateTimeField(null=True, blank=True)

    fecha_pago = models.DateTimeField(null=True, blank=True)
    referencia = models.CharField(max_length=100, blank=True)
    referencia_pago = models.CharField(max_length=100, blank=True)
    mercadopago_payment_id = models.CharField(max_length=100, blank=True)

    class Meta:
        db_table = "pedidos_pago"
        verbose_name = "Pago"
        verbose_name_plural = "Pagos"

    def __str__(self):
        return f"Pago #{self.id_pago} – Pedido #{self.id_pedido_id} – {self.estado}"

    def marcar_pagado(self, referencia=""):
        self.estado = "pagado"
        self.fecha_pago = timezone.now()
        if referencia:
            self.referencia = referencia
        self.save()
        
        pedido = self.id_pedido
        pedido.estado = "confirmado"
        pedido.estado_pago = "pagado"
        pedido.save()

        # Crear notificación
        Notificacion.objects.create(
            id_usuario=pedido.id_usuario,
            id_pedido=pedido,
            mensaje="¡Pago recibido! Hemos confirmado tu pedido y estamos preparando tus productos frescos."
        )

        # Enviar correo
        try:
            from django.core.mail import send_mail
            from django.conf import settings
            
            send_mail(
                '¡Pago recibido! Pedido confirmado - Agrivale',
                f'Hola {pedido.id_usuario.username}, hemos recibido tu pago correctamente para el pedido #{pedido.id_pedido}. ¡Estamos preparando tus productos!',
                settings.DEFAULT_FROM_EMAIL,
                [pedido.id_usuario.email],
                fail_silently=True,
            )
        except Exception as e:
            print(f"Error al enviar correo de pago: {e}")
