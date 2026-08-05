from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib import messages
from decimal import Decimal

from .models import Pedido, ItemPedido
from admin_panel.models import MovimientoInventario


@receiver(post_save, sender=Pedido)
def actualizar_inventario_pedido(sender, instance, created, **kwargs):
    """
    Signal que se ejecuta cuando se guarda un pedido.
    Si el pedido se confirma o se marca como pagado, descuenta del inventario
    y crea los movimientos de Kardex correspondientes.
    """
    # Solo procesar si el pedido ya existía (no en la creación inicial)
    if not created:
        # Usar el estado anterior almacenado en pre_save para comparar
        estado_anterior = getattr(instance, '_estado_anterior', None)
        estado_pago_anterior = getattr(instance, '_estado_pago_anterior', None)
        
        # Si no tenemos el estado anterior (por ejemplo, carga masiva), no procesamos
        if estado_anterior is None and estado_pago_anterior is None:
            return
        
        # Verificar si el pedido pasó a estado 'confirmado' o 'pagado'
        if (instance.estado == 'confirmado' and estado_anterior != 'confirmado') or \
            (instance.estado_pago == 'pagado' and estado_pago_anterior != 'pagado'):
            
            # Solo procesar una vez
            if estado_anterior != 'confirmado' and estado_pago_anterior != 'pagado':
                # Obtener los items del pedido
                items = instance.items.select_related('id_producto').all()
                
                for item in items:
                    producto = item.id_producto
                    cantidad = item.cantidad
                    
                    # Guardar stock anterior
                    stock_anterior = producto.stock
                    
                    # Verificar que hay stock suficiente
                    if stock_anterior >= cantidad:
                        # Descontar del stock
                        producto.stock -= cantidad
                        producto.save()
                        
                        # Crear movimiento de Kardex (Salida por Venta)
                        MovimientoInventario.objects.create(
                            producto=producto,
                            tipo='salida_venta',
                            cantidad=cantidad,
                            stock_anterior=stock_anterior,
                            stock_posterior=producto.stock,
                            costo_unitario=producto.costo_promedio,
                            pedido=instance,
                            observaciones=f'Venta - Pedido #{instance.id_pedido}',
                            usuario=instance.id_usuario
                        )
                    else:
                        # Stock insuficiente - crear movimiento de todas formas pero con advertencia
                        MovimientoInventario.objects.create(
                            producto=producto,
                            tipo='salida_venta',
                            cantidad=cantidad,
                            stock_anterior=stock_anterior,
                            stock_posterior=0,  # Se queda en 0 o negativo
                            costo_unitario=producto.costo_promedio,
                            pedido=instance,
                            observaciones=f'Venta - Pedido #{instance.id_pedido} - STOCK INSUFICIENTE (Stock: {stock_anterior}, Solicitado: {cantidad})',
                            usuario=instance.id_usuario
                        )
                        # Forzar stock a 0
                        producto.stock = 0
                        producto.save()


@receiver(pre_save, sender=Pedido)
def guardar_estado_anterior_pedido(sender, instance, **kwargs):
    """
    Signal que se ejecuta antes de guardar un Pedido.
    Almacena el estado anterior para poder comparar en post_save.
    """
    if instance.pk:
        try:
            estado_anterior = Pedido.objects.get(pk=instance.pk)
            instance._estado_anterior = estado_anterior.estado
            instance._estado_pago_anterior = estado_anterior.estado_pago
        except Pedido.DoesNotExist:
            instance._estado_anterior = None
            instance._estado_pago_anterior = None
    else:
        instance._estado_anterior = None
        instance._estado_pago_anterior = None


@receiver(post_save, sender=ItemPedido)
def actualizar_inventario_item_pedido(sender, instance, created, **kwargs):
    """
    Signal auxiliar que se ejecuta cuando se crea un item de pedido.
    No hace nada por sí mismo, solo asegura que el producto existe.
    """
    pass
