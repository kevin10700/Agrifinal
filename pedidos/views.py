from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.utils import timezone
from django.db import transaction
from django.http import JsonResponse, HttpResponse
from django.conf import settings
from .models import CarritoItem, Pedido, ItemPedido, Notificacion, Pago, Entrega
from .forms import CheckoutForm, ComprobanteForm
from productos.models import Producto
from usuarios.models import DireccionEnvio
import random
import stripe
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import pandas as pd
from io import BytesIO

# --- FUNCIONES AUXILIARES ---
def generar_referencia_transferencia(pedido_id):
    """Genera una referencia única para transferencia bancaria"""
    timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
    return f"AGRIVALE-{pedido_id}-{timestamp}"

def generar_referencia_oxxo(pedido_id):
    """Genera una referencia de 18 dígitos para OXXO"""
    base = f"{pedido_id:06d}{random.randint(100000000000, 999999999999)}"
    return base[:18]

# --- CARRITO ---
@login_required
def ver_carrito(request):
    items = CarritoItem.objects.filter(id_usuario=request.user)
    total = sum(item.get_subtotal() for item in items)
    return render(request, 'pedidos/carrito.html', {'items': items, 'total': total})

@login_required
def agregar_al_carrito(request, producto_id):
    producto = get_object_or_404(Producto, id_producto=producto_id)
    item, created = CarritoItem.objects.get_or_create(
        id_usuario=request.user, 
        id_producto=producto, 
        defaults={'cantidad': 1}
    )
    if not created:
        item.cantidad += 1
        item.save()
    return redirect('pedidos:ver_carrito')

@login_required
def eliminar_del_carrito(request, item_id):
    CarritoItem.objects.filter(id_carrito_item=item_id, id_usuario=request.user).delete()
    return redirect('pedidos:ver_carrito')

@login_required
def actualizar_cantidad(request, item_id):
    item = get_object_or_404(CarritoItem, id_carrito_item=item_id, id_usuario=request.user)
    if request.method == 'POST':
        cantidad = int(request.POST.get('cantidad', 1))
        if cantidad <= 0:
            item.delete()
        else:
            item.cantidad = cantidad
            item.save()
    return redirect('pedidos:ver_carrito')

# --- PEDIDOS Y PAGOS ---
def calcular_resumen_carrito(items):
    """Obtiene importes y un paquete consolidado desde el catálogo."""
    subtotal = sum((item.get_subtotal() for item in items), Decimal("0"))

    def peso_unitario(producto):
        # Los artículos vendidos por kg se capturan por kilogramo en el carrito.
        # Para costales, cajas y demás presentaciones se respeta peso_kg.
        if producto.peso_kg > 0:
            return producto.peso_kg
        if producto.unidad_medida == "kg":
            return Decimal("1")
        if producto.unidad_medida == "libra":
            return Decimal("0.453592")
        return Decimal("0")

    peso_total = sum(
        (peso_unitario(item.id_producto) * item.cantidad for item in items), Decimal("0")
    )
    # Muchos productos iniciales del catálogo todavía no tienen empaque
    # capturado. Envia no acepta dimensiones en cero, así que mientras se
    # completa esa información usamos la caja estándar de Agrivale. Los
    # valores del producto siguen teniendo prioridad cuando existen.
    lado_estandar = Decimal("20")
    alto = max(
        (item.id_producto.alto_cm or lado_estandar for item in items),
        default=lado_estandar,
    )
    ancho = max(
        (item.id_producto.ancho_cm or lado_estandar for item in items),
        default=lado_estandar,
    )
    largo = sum(
        (
            (item.id_producto.largo_cm or lado_estandar) * item.cantidad
            for item in items
        ),
        Decimal("0"),
    )
    return {
        "subtotal": subtotal,
        "paquete": {
            "peso": str(peso_total),
            "alto": str(alto),
            "ancho": str(ancho),
            "largo": str(largo),
            "valor_declarado": str(subtotal),
        },
    }


def _datos_iniciales_checkout(usuario):
    direccion = usuario.direcciones.filter(es_principal=True).first() or usuario.direcciones.first()
    initial = {
        "nombre_receptor": usuario.nombre_completo,
        "correo": usuario.email,
        "telefono_contacto": usuario.telefono,
        "pais": "MX",
    }
    if direccion:
        initial.update({
            "pais": direccion.pais,
            "estado": direccion.estado,
            "municipio": direccion.municipio,
            "codigo_postal": direccion.codigo_postal,
            "colonia": direccion.colonia,
            "calle": direccion.calle,
            "numero_exterior": direccion.numero_exterior,
            "numero_interior": direccion.numero_interior,
            "referencias": direccion.referencias,
        })
    return initial


def _guardar_direccion_checkout(usuario, data):
    direccion = usuario.direcciones.filter(es_principal=True).first()
    valores = {
        "nombre_referencia": "Entrega principal",
        "calle": data["calle"],
        "numero_exterior": data["numero_exterior"],
        "numero_interior": data["numero_interior"],
        "colonia": data["colonia"],
        "municipio": data["municipio"],
        "estado": data["estado"],
        "codigo_postal": data["codigo_postal"],
        "pais": data["pais"],
        "referencias": data["referencias"],
        "telefono_contacto": data["telefono_contacto"],
    }
    if direccion:
        for campo, valor in valores.items():
            setattr(direccion, campo, valor)
        direccion.save()
        return direccion
    return DireccionEnvio.objects.create(id_usuario=usuario, es_principal=True, **valores)


@login_required
def confirmar_pedido(request):
    items = CarritoItem.objects.filter(id_usuario=request.user).select_related("id_producto")
    if not items:
        messages.warning(request, 'Tu carrito está vacío.')
        return redirect('productos:lista')

    resumen = calcular_resumen_carrito(items)
    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            datos = form.cleaned_data
            cotizaciones = request.session.get("envia_cotizaciones", [])
            opcion = next(
                (
                    quote for quote in cotizaciones
                    if quote.get("transportista") == datos["transportista"]
                    and quote.get("servicio") == datos["servicio"]
                ),
                None,
            )
            if not opcion or opcion.get("precio") is None:
                form.add_error(None, "Selecciona una opción de envío válida después de cotizar.")
            else:
                costo_envio = Decimal(str(opcion["precio"]))
                total = resumen["subtotal"] + costo_envio

                # Stripe se conserva sin cambios; esta sesión mantiene su flujo actual.
                if datos["metodo_pago"] == 'tarjeta':
                    request.session['temp_envio'] = {
                        'nombre_receptor': datos["nombre_receptor"],
                        'telefono_contacto': datos["telefono_contacto"],
                        'direccion_entrega': ", ".join(filter(None, [datos["calle"], datos["numero_exterior"], datos["colonia"], datos["municipio"], datos["estado"], datos["codigo_postal"]])),
                        'metodo_pago': datos["metodo_pago"],
                        'total': float(total),
                    }
                    return redirect('pedidos:pagar_con_stripe_temp')

                try:
                    with transaction.atomic():
                        direccion = _guardar_direccion_checkout(request.user, datos)
                        if request.user.email != datos["correo"] or request.user.telefono != datos["telefono_contacto"]:
                            request.user.email = datos["correo"]
                            request.user.telefono = datos["telefono_contacto"]
                            request.user.save(update_fields=["email", "telefono"])

                        pedido = Pedido.objects.create(
                            id_usuario=request.user,
                            id_direccion_envio=direccion,
                            subtotal=resumen["subtotal"],
                            costo_envio=costo_envio,
                            total=total,
                            estado='pendiente',
                            estado_pago='pendiente',
                            nombre_receptor=datos["nombre_receptor"],
                            telefono_contacto=datos["telefono_contacto"],
                            direccion_entrega=direccion.direccion_completa,
                        )
                        for item in items:
                            if item.cantidad > item.id_producto.stock:
                                raise ValueError(f"No hay existencias suficientes de {item.id_producto.nombre}.")
                            ItemPedido.objects.create(
                                id_pedido=pedido,
                                id_producto=item.id_producto,
                                cantidad=item.cantidad,
                                precio_unitario=item.id_producto.get_precio_actual(),
                            )
                            item.id_producto.stock -= item.cantidad
                            item.id_producto.save(update_fields=["stock"])

                        pago = Pago.objects.create(
                            id_pedido=pedido,
                            metodo=datos["metodo_pago"],
                            proveedor_pago=("mercadopago" if datos["metodo_pago"] == "mercadopago" else "manual"),
                            estado='pendiente',
                        )
                        Entrega.objects.create(
                            id_pedido=pedido,
                            transportista=datos["transportista"],
                            servicio=datos["servicio"],
                            costo_envio=costo_envio,
                            respuesta_json=(
                                {
                                    "tipo": "local",
                                    "zona_reparto": opcion.get("zona_reparto", ""),
                                    "tiempo_entrega": opcion.get("dias_estimados", ""),
                                    "costo_envio": str(costo_envio),
                                }
                                if opcion.get("tipo") == "local"
                                else {}
                            ),
                            estado='pendiente',
                        )
                        items.delete()
                        request.session.pop("envia_cotizaciones", None)

                        if datos["metodo_pago"] == "mercadopago":
                            # Flujo independiente de Stripe: el pedido existe antes
                            # de redirigir y el webhook es quien confirma el pago.
                            from payments.services.mercadopago import crear_preferencia

                            preferencia = crear_preferencia(pedido, request)
                            pago.referencia = preferencia.get("id", "")
                            pago.referencia_pago = pago.referencia
                            pago.save(update_fields=["referencia", "referencia_pago"])
                            return redirect(preferencia["init_point"], code=303)

                        if datos["metodo_pago"] == 'transferencia':
                            pago.referencia = generar_referencia_transferencia(pedido.id_pedido)
                            pago.referencia_pago = pago.referencia
                            pago.save(update_fields=["referencia", "referencia_pago"])
                            return redirect('pedidos:instrucciones_pago', pedido_id=pedido.id_pedido)

                        pago.referencia_oxxo = generar_referencia_oxxo(pedido.id_pedido)
                        pago.fecha_vencimiento_oxxo = timezone.now() + timezone.timedelta(hours=48)
                        pago.save(update_fields=["referencia_oxxo", "fecha_vencimiento_oxxo"])
                        return redirect('pedidos:instrucciones_pago', pedido_id=pedido.id_pedido)
                except Exception as error:
                    messages.error(request, f"No fue posible crear el pedido: {error}")
        
    else:
        form = CheckoutForm(initial=_datos_iniciales_checkout(request.user))

    return render(request, 'pedidos/confirmar_pedido.html', {
        'items': items,
        'form': form,
        'subtotal': resumen["subtotal"],
        'paquete': resumen["paquete"],
    })

@login_required
def pagar_con_stripe_temp(request):
    """Crea la sesión de Stripe usando datos temporales de sesión sin crear pedido previo"""
    datos_envio = request.session.get('temp_envio')
    if not datos_envio:
        messages.error(request, 'No hay datos de envío temporales.')
        return redirect('pedidos:ver_carrito')
    
    items = CarritoItem.objects.filter(id_usuario=request.user)
    if not items:
        messages.error(request, 'Tu carrito está vacío.')
        return redirect('productos:lista')

    stripe.api_key = settings.STRIPE_SECRET_KEY

    try:
        line_items = []
        for item in items:
            line_items.append({
                'price_data': {
                    'currency': 'mxn',
                    'unit_amount': int(item.id_producto.get_precio_actual() * 100),
                    'product_data': {'name': item.id_producto.nombre},
                },
                'quantity': item.cantidad,
            })

        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=line_items,
            mode='payment',
            success_url="http://127.0.0.1:8000/pedidos/stripe/exito/?session_id={CHECKOUT_SESSION_ID}",
            cancel_url="http://127.0.0.1:8000/pedidos/carrito/",
        )
        return redirect(checkout_session.url, code=303)
    except Exception as e:
        messages.error(request, f"Error al procesar el pago con Stripe: {str(e)}")
        return redirect('pedidos:ver_carrito')

@login_required
def stripe_exito(request):
    """Crea el pedido formalmente, descuenta stock y limpia carrito SOLO si el pago fue exitoso"""
    datos_envio = request.session.get('temp_envio')
    if not datos_envio:
        messages.error(request, 'La sesión de pago expiró o ya fue procesada.')
        return redirect('pedidos:mis_pedidos')
    
    items = CarritoItem.objects.filter(id_usuario=request.user)
    if not items:
        messages.error(request, 'No se encontraron productos en el carrito.')
        return redirect('productos:lista')

    try:
        with transaction.atomic():
            # 1. Crear el pedido formal
            pedido = Pedido.objects.create(
                id_usuario=request.user,
                total=Decimal(str(datos_envio['total'])),
                estado='pendiente',
                nombre_receptor=datos_envio['nombre_receptor'],
                telefono_contacto=datos_envio['telefono_contacto'],
                direccion_entrega=datos_envio['direccion_entrega']
            )
            
            # 2. Descontar stock y registrar items
            for item in items:
                ItemPedido.objects.create(
                    id_pedido=pedido,
                    id_producto=item.id_producto,
                    cantidad=item.cantidad,
                    precio_unitario=item.id_producto.get_precio_actual()
                )
                item.id_producto.stock -= item.cantidad
                item.id_producto.save()
            
            # 3. Registrar el pago
            Pago.objects.create(
                id_pedido=pedido,
                metodo='tarjeta',
                estado='pagado',
                referencia=request.GET.get('session_id', 'STRIPE')
            )
            
            # 4. Crear entrega, limpiar carrito y borrar datos temporales
            Entrega.objects.create(id_pedido=pedido, paqueteria='99MINUTOS', estado='pendiente')
            items.delete()
            del request.session['temp_envio']
            
            messages.success(request, f'✅ ¡Pago exitoso! Pedido #{pedido.id_pedido} creado correctamente.')
            return redirect('pedidos:detalle_pedido', pedido_id=pedido.id_pedido)
            
    except Exception as e:
        messages.error(request, f'Error al registrar el pedido post-pago: {str(e)}')
        return redirect('pedidos:ver_carrito')

@login_required
def instrucciones_pago(request, pedido_id):
    """Muestra las instrucciones de pago según el método seleccionado"""
    pedido = get_object_or_404(Pedido, id_pedido=pedido_id, id_usuario=request.user)
    pago = get_object_or_404(Pago, id_pedido=pedido)
    
    context = {
        'pedido': pedido,
        'pago': pago,
    }
    
    if pago.metodo == 'transferencia':
        context.update({
            'banco': 'BBVA México',
            'cuenta': '0123456789',
            'clabe': '012345678901234567',
            'beneficiario': 'AGRIVALE S.A. de C.V.',
            'referencia': pago.referencia,
        })
    elif pago.metodo == 'oxxo':
        context.update({
            'referencia': pago.referencia_oxxo,
            'vencimiento': pago.fecha_vencimiento_oxxo,
        })
    
    return render(request, 'pedidos/instrucciones_pago.html', context)

@login_required
def subir_comprobante(request, id_pedido):
    """Vista para que el usuario suba su comprobante de pago"""
    pedido = get_object_or_404(Pedido, id_pedido=id_pedido, id_usuario=request.user)
    pago = get_object_or_404(Pago, id_pedido=pedido)
    
    if pago.estado == 'pagado':
        messages.warning(request, 'Este pedido ya fue pagado.')
        return redirect('pedidos:detalle_pedido', pedido_id=pedido.id_pedido)
    
    if pago.metodo == 'tarjeta':
        messages.warning(request, 'Los pagos con tarjeta se procesan mediante Stripe.')
        return redirect('pedidos:detalle_pedido', pedido_id=pedido.id_pedido)
    
    if request.method == 'POST':
        form = ComprobanteForm(request.POST, request.FILES, instance=pago)
        if form.is_valid():
            form.save()
            messages.success(
                request, 
                '✅ Comprobante subido correctamente. Estaremos validando tu pago en las próximas 24-48 horas.'
            )
            return redirect('pedidos:mis_pedidos')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{error}')
    else:
        form = ComprobanteForm(instance=pago)
    
    return render(request, 'pedidos/subir_comprobante.html', {
        'form': form,
        'pedido': pedido,
        'pago': pago
    })

# --- GESTIÓN DE USUARIO Y ADMIN ---
@login_required
def mis_pedidos(request):
    pedidos = Pedido.objects.filter(id_usuario=request.user).order_by('-fecha_pedido')
    return render(request, 'pedidos/mis_pedidos.html', {'pedidos': pedidos})

@login_required
def detalle_pedido(request, pedido_id):
    pedido = get_object_or_404(Pedido, id_pedido=pedido_id, id_usuario=request.user)
    return render(request, 'pedidos/detalle_pedido.html', {'pedido': pedido})

@staff_member_required
def admin_entregas(request):
    entregas = Entrega.objects.all().order_by('-fecha_asignacion')
    return render(request, 'pedidos/admin_entregas.html', {'entregas': entregas})

# --- RUTAS RESTANTES ---
@login_required
def notificaciones(request):
    notificaciones = Notificacion.objects.filter(id_usuario=request.user).order_by('-fecha_creacion')
    return render(request, 'pedidos/notificaciones.html', {'notificaciones': notificaciones})

@login_required
def solicitar_cancelacion(request, pedido_id):
    pedido = get_object_or_404(Pedido, id_pedido=pedido_id, id_usuario=request.user)
    if request.method == 'POST':
        motivo = request.POST.get('motivo')
        if motivo:
            pedido.estado_cancelacion = 'solicitado'
            pedido.motivo_cancelacion = motivo
            pedido.fecha_solicitud_cancelacion = timezone.now()
            pedido.save()
            messages.success(request, 'Solicitud de cancelación enviada.')
            return redirect('pedidos:mis_pedidos')
    return render(request, 'pedidos/solicitar_cancelacion.html', {'pedido': pedido})

@staff_member_required
def admin_gestionar_cancelaciones(request):
    pedidos = Pedido.objects.filter(estado_cancelacion='solicitado')
    return render(request, 'pedidos/admin_cancelaciones.html', {'pedidos': pedidos})

@staff_member_required
def admin_aprobar_cancelacion(request, pedido_id):
    pedido = get_object_or_404(Pedido, id_pedido=pedido_id)
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'aprobar':
            pedido.estado_cancelacion = 'aprobado'
            pedido.estado = 'cancelado'
            pedido.fecha_aprobacion_cancelacion = timezone.now()
            pedido.requiere_reembolso = True
            pedido.save()
            messages.success(request, f'Cancelación aprobada para pedido #{pedido_id}')
        elif action == 'rechazar':
            razon = request.POST.get('razon_rechazo', '')
            pedido.estado_cancelacion = 'rechazado'
            pedido.razon_rechazo = razon
            pedido.save()
            messages.warning(request, f'Cancelación rechazada para pedido #{pedido_id}')
    return redirect('pedidos:admin_cancelaciones')

@staff_member_required
def admin_crear_entrega(request, pedido_id):
    pedido = get_object_or_404(Pedido, id_pedido=pedido_id)
    if request.method == 'POST':
        paqueteria = request.POST.get('paqueteria')
        numero_guia = request.POST.get('numero_guia')
        if paqueteria and numero_guia:
            Entrega.objects.create(
                id_pedido=pedido,
                paqueteria=paqueteria,
                numero_guia=numero_guia,
                estado='pendiente',
                fecha_asignacion=timezone.now()
            )
            messages.success(request, f'Entrega creada para pedido #{pedido_id}')
            return redirect('pedidos:admin_entregas')
    return render(request, 'pedidos/admin_crear_entrega.html', {'pedido': pedido})

@staff_member_required
def admin_actualizar_entrega(request, entrega_id):
    entrega = get_object_or_404(Entrega, id_entrega=entrega_id)
    if request.method == 'POST':
        nuevo_estado = request.POST.get('estado')
        if nuevo_estado:
            entrega.actualizar_estado(nuevo_estado)
            messages.success(request, f'Entrega #{entrega_id} actualizada a {nuevo_estado}')
            return redirect('pedidos:admin_entregas')
    return render(request, 'pedidos/admin_actualizar_entrega.html', {'entrega': entrega})

@staff_member_required
def admin_detalle_entrega(request, entrega_id):
    entrega = get_object_or_404(Entrega, id_entrega=entrega_id)
    return render(request, 'pedidos/admin_detalle_entrega.html', {'entrega': entrega})

# --- REPORTES Y EXPORTACIONES ---

@staff_member_required
def exportar_ventas_pdf(request, periodo='mes'):
    """Exporta reporte de ventas en PDF"""
    # Calcular fechas según el periodo
    hoy = timezone.now().date()
    if periodo == 'dia':
        fecha_inicio = hoy
        fecha_fin = hoy + timedelta(days=1)
    elif periodo == 'semana':
        fecha_inicio = hoy - timedelta(days=7)
        fecha_fin = hoy + timedelta(days=1)
    elif periodo == 'mes':
        fecha_inicio = hoy.replace(day=1)
        fecha_fin = hoy + timedelta(days=1)
    elif periodo == 'anio':
        fecha_inicio = hoy.replace(month=1, day=1)
        fecha_fin = hoy + timedelta(days=1)
    else:
        fecha_inicio = hoy - timedelta(days=30)
        fecha_fin = hoy + timedelta(days=1)
    
    # Obtener pedidos del periodo
    pedidos = Pedido.objects.filter(
        fecha_pedido__gte=fecha_inicio,
        fecha_pedido__lt=fecha_fin,
        estado__in=['completado', 'en_proceso']
    ).order_by('-fecha_pedido')
    
    # Crear PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="ventas_{periodo}_{hoy}.pdf"'
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=18)
    
    elements = []
    styles = getSampleStyleSheet()
    
    # Título
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.darkgreen,
        alignment=1,
        spaceAfter=20
    )
    elements.append(Paragraph(f"Reporte de Ventas - {periodo.capitalize()}", title_style))
    elements.append(Paragraph(f"Periodo: {fecha_inicio} a {fecha_fin - timedelta(days=1)}", styles['Normal']))
    elements.append(Spacer(1, 20))
    
    # Resumen
    total_ventas = sum(p.total for p in pedidos)
    total_pedidos = pedidos.count()
    elements.append(Paragraph(f"<b>Total de pedidos:</b> {total_pedidos}", styles['Normal']))
    elements.append(Paragraph(f"<b>Total de ventas:</b> ${total_ventas:,.2f} MXN", styles['Normal']))
    elements.append(Spacer(1, 20))
    
    # Tabla de pedidos
    data = [['# Pedido', 'Cliente', 'Fecha', 'Total', 'Estado']]
    for pedido in pedidos:
        data.append([
            str(pedido.id_pedido),
            pedido.usuario.username,
            pedido.fecha_pedido.strftime('%d/%m/%Y %H:%M'),
            f"${pedido.total:,.2f}",
            pedido.get_estado_display()
        ])
    
    table = Table(data, colWidths=[1*inch, 2*inch, 1.5*inch, 1*inch, 1*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkgreen),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    elements.append(table)
    
    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()
    response.write(pdf)
    
    return response

@staff_member_required
def exportar_ventas_excel(request, periodo='mes'):
    """Exporta reporte de ventas en Excel"""
    # Calcular fechas según el periodo
    hoy = timezone.now().date()
    if periodo == 'dia':
        fecha_inicio = hoy
        fecha_fin = hoy + timedelta(days=1)
    elif periodo == 'semana':
        fecha_inicio = hoy - timedelta(days=7)
        fecha_fin = hoy + timedelta(days=1)
    elif periodo == 'mes':
        fecha_inicio = hoy.replace(day=1)
        fecha_fin = hoy + timedelta(days=1)
    elif periodo == 'anio':
        fecha_inicio = hoy.replace(month=1, day=1)
        fecha_fin = hoy + timedelta(days=1)
    else:
        fecha_inicio = hoy - timedelta(days=30)
        fecha_fin = hoy + timedelta(days=1)
    
    # Obtener pedidos del periodo
    pedidos = Pedido.objects.filter(
        fecha_pedido__gte=fecha_inicio,
        fecha_pedido__lt=fecha_fin,
        estado__in=['completado', 'en_proceso']
    ).order_by('-fecha_pedido')
    
    # Crear DataFrame
    data = []
    for pedido in pedidos:
        data.append({
            'Pedido': pedido.id_pedido,
            'Cliente': pedido.usuario.username,
            'Fecha': pedido.fecha_pedido.strftime('%d/%m/%Y %H:%M'),
            'Total': float(pedido.total),
            'Estado': pedido.get_estado_display(),
            'Método de pago': pedido.metodo_pago if hasattr(pedido, 'metodo_pago') else 'N/A'
        })
    
    df = pd.DataFrame(data)
    
    # Crear Excel con manejo seguro si falta openpyxl
    output = BytesIO()
    try:
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Ventas', index=False)

            # Hoja de resumen
            total_pedidos = pedidos.count() if hasattr(pedidos, 'count') else len(pedidos)
            total_ventas = float(sum(p.total for p in pedidos)) if pedidos else 0.0
            promedio = float(total_ventas / total_pedidos) if total_pedidos else 0.0
            resumen = pd.DataFrame({
                'Métrica': ['Total de pedidos', 'Total de ventas', 'Promedio por pedido'],
                'Valor': [
                    total_pedidos,
                    total_ventas,
                    promedio
                ]
            })
            resumen.to_excel(writer, sheet_name='Resumen', index=False)

        output.seek(0)
        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="ventas_{periodo}_{hoy}.xlsx"'
        return response
    except ModuleNotFoundError:
        # Fallback a CSV si openpyxl no está instalado
        csv_out = df.to_csv(index=False)
        response = HttpResponse(csv_out, content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="ventas_{periodo}_{hoy}.csv"'
        return response

@staff_member_required
def exportar_productos_mas_vendidos(request, periodo='mes'):
    """Exporta productos más vendidos en Excel"""
    # Calcular fechas según el periodo
    hoy = timezone.now().date()
    if periodo == 'dia':
        fecha_inicio = hoy
        fecha_fin = hoy + timedelta(days=1)
    elif periodo == 'semana':
        fecha_inicio = hoy - timedelta(days=7)
        fecha_fin = hoy + timedelta(days=1)
    elif periodo == 'mes':
        fecha_inicio = hoy.replace(day=1)
        fecha_fin = hoy + timedelta(days=1)
    elif periodo == 'anio':
        fecha_inicio = hoy.replace(month=1, day=1)
        fecha_fin = hoy + timedelta(days=1)
    else:
        fecha_inicio = hoy - timedelta(days=30)
        fecha_fin = hoy + timedelta(days=1)
    
    # Obtener items de pedido del periodo
    items = ItemPedido.objects.filter(
        id_pedido__fecha_pedido__gte=fecha_inicio,
        id_pedido__fecha_pedido__lt=fecha_fin,
        id_pedido__estado__in=['completado', 'en_proceso']
    )
    
    # Agrupar por producto
    productos_vendidos = {}
    for item in items:
        producto_id = item.id_producto.id_producto
        if producto_id not in productos_vendidos:
            productos_vendidos[producto_id] = {
                'nombre': item.id_producto.nombre,
                'categoria': item.id_producto.categoria.nombre if item.id_producto.categoria else 'N/A',
                'cantidad': 0,
                'total': 0
            }
        productos_vendidos[producto_id]['cantidad'] += item.cantidad
        productos_vendidos[producto_id]['total'] += item.subtotal
    
    # Convertir a lista y ordenar
    lista_productos = sorted(
        productos_vendidos.values(),
        key=lambda x: x['cantidad'],
        reverse=True
    )
    
    # Crear DataFrame a partir de la lista (los dicts usan keys internas)
    if lista_productos:
        df = pd.DataFrame(lista_productos)
        # Normalizar nombres de columna para el archivo exportado
        df = df.rename(columns={
            'nombre': 'Producto',
            'categoria': 'Categoría',
            'cantidad': 'Cantidad Vendida',
            'total': 'Total Ventas'
        })
    else:
        # DataFrame vacío con columnas esperadas (evita el ValueError al asignar columnas)
        df = pd.DataFrame(columns=['Producto', 'Categoría', 'Cantidad Vendida', 'Total Ventas'])

    # Crear Excel (si falta openpyxl se lanzará ModuleNotFoundError; dejar que el caller o el entorno lo gestione
    # o se puede capturar y ofrecer CSV si se prefiere). Aquí se realiza la exportación segura.
    output = BytesIO()
    try:
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Productos Más Vendidos', index=False)

            # Hoja de resumen — usar accesos seguros cuando no haya productos
            resumen = pd.DataFrame({
                'Métrica': ['Total de productos diferentes', 'Producto más vendido', 'Cantidad del más vendido'],
                'Valor': [
                    len(lista_productos),
                    lista_productos[0].get('nombre') if lista_productos else 'N/A',
                    lista_productos[0].get('cantidad') if lista_productos else 0
                ]
            })
            resumen.to_excel(writer, sheet_name='Resumen', index=False)

        output.seek(0)
        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="productos_mas_vendidos_{periodo}_{hoy}.xlsx"'
        return response
    except ModuleNotFoundError:
        # Fallback a CSV si openpyxl no está instalado
        csv_out = df.to_csv(index=False)
        response = HttpResponse(csv_out, content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="productos_mas_vendidos_{periodo}_{hoy}.csv"'
        return response


@staff_member_required
def exportar_productos_mas_vendidos_pdf(request, periodo='mes'):
    """Exporta productos más vendidos en PDF."""
    hoy = timezone.now().date()
    if periodo == 'dia':
        fecha_inicio = hoy
        fecha_fin = hoy + timedelta(days=1)
    elif periodo == 'semana':
        fecha_inicio = hoy - timedelta(days=7)
        fecha_fin = hoy + timedelta(days=1)
    elif periodo == 'mes':
        fecha_inicio = hoy.replace(day=1)
        fecha_fin = hoy + timedelta(days=1)
    elif periodo == 'anio':
        fecha_inicio = hoy.replace(month=1, day=1)
        fecha_fin = hoy + timedelta(days=1)
    else:
        fecha_inicio = hoy - timedelta(days=30)
        fecha_fin = hoy + timedelta(days=1)

    items = ItemPedido.objects.filter(
        id_pedido__fecha_pedido__gte=fecha_inicio,
        id_pedido__fecha_pedido__lt=fecha_fin,
        id_pedido__estado__in=['completado', 'en_proceso']
    )

    productos_vendidos = {}
    for item in items:
        producto_id = item.id_producto.id_producto
        if producto_id not in productos_vendidos:
            productos_vendidos[producto_id] = {
                'nombre': item.id_producto.nombre,
                'categoria': item.id_producto.categoria.nombre if item.id_producto.categoria else 'N/A',
                'cantidad': 0,
                'total': 0
            }
        productos_vendidos[producto_id]['cantidad'] += item.cantidad
        productos_vendidos[producto_id]['total'] += item.subtotal

    lista_productos = sorted(
        productos_vendidos.values(),
        key=lambda x: x['cantidad'],
        reverse=True
    )

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=18)
    elements = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.darkgreen,
        alignment=1,
        spaceAfter=16
    )
    elements.append(Paragraph(f"Reporte de Productos Más Vendidos - {periodo.capitalize()}", title_style))
    elements.append(Paragraph(f"Periodo: {fecha_inicio} a {fecha_fin - timedelta(days=1)}", styles['Normal']))
    elements.append(Spacer(1, 14))

    data = [['Producto', 'Categoría', 'Cantidad', 'Total Ventas']]
    for producto in lista_productos:
        data.append([
            producto['nombre'],
            producto['categoria'],
            str(producto['cantidad']),
            f"${producto['total']:,.2f}"
        ])

    if len(data) == 1:
        elements.append(Paragraph('No se encontraron ventas en este periodo.', styles['Normal']))
    else:
        table = Table(data, colWidths=[2.5*inch, 2*inch, 1*inch, 1.3*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkgreen),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        elements.append(table)

    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="productos_mas_vendidos_{periodo}_{hoy}.pdf"'
    response.write(pdf)
    return response


@staff_member_required
def reporte_admin_page(request):
    """Página integrada en el admin que muestra enlaces y controles responsivos para los reportes."""
    return render(request, 'pedidos/admin_reporte.html', {
        'hoy': timezone.now().date()
    })
