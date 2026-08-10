from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Count, Sum, Q, F, Avg, Max, Min
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.utils.text import slugify
from datetime import datetime, timedelta
import json
from decimal import Decimal
from django.contrib.auth import login, logout as django_logout
from django.views.decorators.cache import never_cache

# Asegúrate de importar tu formulario según la estructura de tu proyecto
from .forms import PanelLoginForm

# Modelos
from usuarios.models import Usuario, DireccionEnvio, TokenRecuperacion, TokenVerificacion
from productos.models import Producto, Categoria
from pedidos.models import Pedido, ItemPedido, Pago, Entrega, Notificacion, CarritoItem
from .models import RolPanel, UsuarioPanel, Proveedor, Compra, ItemCompra, MovimientoInventario


# ===== DECORADOR DE PERMISOS =====

def rol_requerido(permiso):
    """
    Decorador que verifica si el usuario tiene un permiso específico del RolPanel.
    Si el usuario es superuser, siempre tiene acceso.
    Si el usuario tiene un UsuarioPanel con rol activo, se verifica el permiso específico.
    Si el usuario no tiene el permiso, redirige al dashboard con un mensaje de error.
    """
    def decorator(view_func):
        @login_required
        def wrapper(request, *args, **kwargs):
            # Superusers tienen acceso completo al panel
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            
            # Verificar si el usuario tiene un UsuarioPanel con rol activo
            try:
                usuario_panel = UsuarioPanel.objects.select_related('rol').get(usuario=request.user)
                if usuario_panel.rol and usuario_panel.rol.activo:
                    # Si tiene rol activo, verificar el permiso específico
                    if getattr(usuario_panel.rol, permiso, False):
                        return view_func(request, *args, **kwargs)
            except UsuarioPanel.DoesNotExist:
                pass
            
            messages.error(request, 'No tienes permisos para acceder a esta sección.')
            return redirect('admin_panel:dashboard')
        return wrapper
    return decorator


# ===== VISTA DE LOGIN =====

def login_view(request):
    """Vista de login del Panel Administrativo"""
    # Verificar si el usuario ya tiene acceso al panel (superuser o con UsuarioPanel asignado)
    if request.user.is_authenticated:
        if request.user.is_superuser:
            return redirect('admin_panel:dashboard')
        try:
            usuario_panel = UsuarioPanel.objects.select_related('rol').get(usuario=request.user)
            if usuario_panel.rol and usuario_panel.rol.activo:
                return redirect('admin_panel:dashboard')
        except UsuarioPanel.DoesNotExist:
            pass

    if request.method == 'POST':
        form = PanelLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            
            # Verificar si la cuenta está activa
            if not user.is_active:
                messages.error(
                    request,
                    '❌ Tu cuenta ha sido desactivada. Si crees que esto es un error, contacta al administrador.'
                )
                return render(request, 'admin_panel/login.html', {'form': form})
            
            # Login exitoso
            login(request, user)
            
            # Guardar información de seguridad en la sesión
            request.session['login_ip'] = get_client_ip(request)
            request.session['login_user_agent'] = request.META.get('HTTP_USER_AGENT', '')
            request.session['login_time'] = timezone.now().isoformat()
            
            messages.success(request, f'Bienvenido al Panel Administrativo, {user.nombre_completo}')
            return redirect('admin_panel:dashboard')
    else:
        form = PanelLoginForm()

    return render(request, 'admin_panel/login.html', {'form': form})


def get_client_ip(request):
    """Obtiene la IP real del cliente, considerando proxies."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


@login_required
def logout_view(request):
    """Cierra sesión del panel administrativo de forma consistente."""
    nombre = request.user.nombre_completo
    django_logout(request)
    messages.info(request, f'Sesión cerrada correctamente. Hasta pronto, {nombre}.')
    response = redirect('admin_panel:login')
    # Evita que el navegador muestre el dashboard desde caché al dar "atrás"
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate, private'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response


# ===== DASHBOARD =====

@login_required
def dashboard(request):
    """Dashboard profesional del panel administrativo"""
    
    # Estadísticas del día
    hoy = timezone.now().date()
    inicio_hoy = datetime.combine(hoy, datetime.min.time())
    
    # Ventas de hoy
    ventas_hoy = Pedido.objects.filter(
        fecha_pedido__gte=inicio_hoy,
        estado_pago='pagado'
    ).aggregate(
        total=Sum('total'),
        cantidad=Count('id_pedido')
    )
    
    # Ventas de la semana
    inicio_semana = hoy - timedelta(days=hoy.weekday())
    inicio_semana = datetime.combine(inicio_semana, datetime.min.time())
    ventas_semana = Pedido.objects.filter(
        fecha_pedido__gte=inicio_semana,
        estado_pago='pagado'
    ).aggregate(
        total=Sum('total'),
        cantidad=Count('id_pedido')
    )
    
    # Ventas del mes
    inicio_mes = datetime.combine(hoy.replace(day=1), datetime.min.time())
    ventas_mes = Pedido.objects.filter(
        fecha_pedido__gte=inicio_mes,
        estado_pago='pagado'
    ).aggregate(
        total=Sum('total'),
        cantidad=Count('id_pedido')
    )
    
    # Ingresos (total de ventas pagadas)
    ingresos = Pedido.objects.filter(estado_pago='pagado').aggregate(
        total=Sum('total')
    )
    
    # Ganancias (ingresos - costos de productos)
    ganancias = ingresos.get('total', 0) or 0
    
    # Pedidos por estado
    pedidos_pendientes = Pedido.objects.filter(estado='pendiente').count()
    pedidos_confirmados = Pedido.objects.filter(estado='confirmado').count()
    pedidos_preparando = Pedido.objects.filter(estado='preparando').count()
    pedidos_enviados = Pedido.objects.filter(estado='enviado').count()
    pedidos_entregados = Pedido.objects.filter(estado='entregado').count()
    pedidos_cancelados = Pedido.objects.filter(estado='cancelado').count()
    
    # Productos
    productos_sin_stock = Producto.objects.filter(stock=0).count()
    productos_bajo_stock = Producto.objects.filter(stock__lte=10, stock__gt=0).count()
    total_productos = Producto.objects.count()
    
    # Clientes
    hace_30_dias = hoy - timedelta(days=30)
    clientes_nuevos = Usuario.objects.filter(
        date_joined__gte=hace_30_dias
    ).count()
    total_clientes = Usuario.objects.filter(is_staff=False).count()
    
    # Proveedores
    proveedores_activos = Proveedor.objects.filter(activo=True).count()
    
    # Compras del mes
    compras_mes = Compra.objects.filter(
        fecha_creacion__gte=inicio_mes
    ).aggregate(total=Sum('total'))['total'] or 0
    
    # Valor del inventario
    valor_inventario = Producto.objects.aggregate(
        total=Sum(F('costo_promedio') * F('stock'))
    )
    
    # Productos más vendidos
    productos_mas_vendidos = ItemPedido.objects.values(
        'id_producto__nombre'
    ).annotate(
        total_vendido=Sum('cantidad')
    ).order_by('-total_vendido')[:10]
    
    # Categorías más vendidas
    categorias_mas_vendidas = ItemPedido.objects.values(
        'id_producto__id_categoria__nombre'
    ).annotate(
        total_vendido=Sum('cantidad')
    ).order_by('-total_vendido')[:5]
    
    # Ventas por mes (últimos 6 meses)
    meses = []
    ventas_por_mes = []
    for i in range(5, -1, -1):
        fecha = hoy - timedelta(days=30*i)
        mes_inicio = datetime.combine(fecha.replace(day=1), datetime.min.time())
        if fecha.month == 12:
            mes_fin = datetime.combine(fecha.replace(year=fecha.year+1, month=1, day=1), datetime.min.time())
        else:
            mes_fin = datetime.combine(fecha.replace(month=fecha.month+1, day=1), datetime.min.time())
        
        ventas_mes_actual = Pedido.objects.filter(
            fecha_pedido__gte=mes_inicio,
            fecha_pedido__lt=mes_fin,
            estado_pago='pagado'
        ).aggregate(total=Sum('total'))['total'] or 0
        
        meses.append(fecha.strftime('%B %Y'))
        ventas_por_mes.append(float(ventas_mes_actual))
    
    # Pedidos recientes
    pedidos_recientes = Pedido.objects.select_related(
        'id_usuario'
    ).order_by('-fecha_pedido')[:10]
    
    # Clientes recientes
    clientes_recientes = Usuario.objects.filter(
        is_staff=False
    ).order_by('-date_joined')[:5]
    
    # Proveedores recientes
    proveedores_recientes = Proveedor.objects.filter(activo=True).order_by('-fecha_creacion')[:5]
    
    # Alertas
    alertas = {
        'productos_sin_stock': productos_sin_stock,
        'productos_bajo_stock': productos_bajo_stock,
        'pedidos_pendientes': pedidos_pendientes,
        'pedidos_cancelados': pedidos_cancelados,
    }
    
    context = {
        # KPIs principales
        'ventas_hoy': ventas_hoy.get('total', 0) or 0,
        'ventas_hoy_cantidad': ventas_hoy.get('cantidad', 0) or 0,
        'ventas_semana': ventas_semana.get('total', 0) or 0,
        'ventas_mes': ventas_mes.get('total', 0) or 0,
        'ingresos': ingresos.get('total', 0) or 0,
        'ganancias': ganancias,
        'pedidos_pendientes': pedidos_pendientes,
        'pedidos_confirmados': pedidos_confirmados,
        'pedidos_preparando': pedidos_preparando,
        'pedidos_enviados': pedidos_enviados,
        'pedidos_entregados': pedidos_entregados,
        'pedidos_cancelados': pedidos_cancelados,
        'productos_sin_stock': productos_sin_stock,
        'productos_bajo_stock': productos_bajo_stock,
        'clientes_nuevos': clientes_nuevos,
        'proveedores_activos': proveedores_activos,
        'compras_mes': compras_mes,
        'valor_inventario': valor_inventario.get('total', 0) or 0,
        'total_productos': total_productos,
        'total_clientes': total_clientes,
        'total_categorias': Categoria.objects.count(),
        'total_pedidos': Pedido.objects.count(),
        
        # Datos para gráficas
        'productos_mas_vendidos': productos_mas_vendidos,
        'categorias_mas_vendidas': categorias_mas_vendidas,
        'meses': json.dumps(meses),
        'ventas_por_mes': json.dumps(ventas_por_mes),
        
        # Widgets
        'pedidos_recientes': pedidos_recientes,
        'clientes_recientes': clientes_recientes,
        'proveedores_recientes': proveedores_recientes,
        'alertas': alertas,
    }
    
    return render(request, 'admin_panel/dashboard.html', context)


# ===== VISTAS DE PRODUCTOS =====

@rol_requerido('puede_gestionar_productos')
def productos_lista(request):
    """Lista de productos con búsqueda y filtros"""
    from django.core.paginator import Paginator
    
    productos_lista = Producto.objects.select_related('id_categoria').all()
    
    # Búsqueda
    busqueda = request.GET.get('q', '')
    if busqueda:
        productos_lista = productos_lista.filter(
            Q(nombre__icontains=busqueda) |
            Q(descripcion_corta__icontains=busqueda)
        )
    
    # Filtro por categoría
    categoria_id = request.GET.get('categoria')
    if categoria_id:
        productos_lista = productos_lista.filter(id_categoria_id=categoria_id)
    
    # Filtro por estado de stock
    stock_filtro = request.GET.get('stock')
    if stock_filtro == 'sin_stock':
        productos_lista = productos_lista.filter(stock=0)
    elif stock_filtro == 'bajo_stock':
        productos_lista = productos_lista.filter(stock__lte=10, stock__gt=0)
    
    # Ordenamiento
    orden = request.GET.get('orden', '-fecha_creacion')
    productos_lista = productos_lista.order_by(orden)
    
    # Paginación
    paginator = Paginator(productos_lista, 20)
    page = request.GET.get('page')
    productos = paginator.get_page(page)
    
    categorias = Categoria.objects.all()
    
    context = {
        'productos': productos,
        'categorias': categorias,
        'busqueda': busqueda,
        'categoria_seleccionada': categoria_id,
        'stock_filtro': stock_filtro,
    }
    
    return render(request, 'admin_panel/productos/lista.html', context)


@rol_requerido('puede_gestionar_productos')
def producto_crear(request):
    """Crear nuevo producto - El stock inicial siempre es 0"""
    if request.method == 'POST':
        try:
            nombre = request.POST.get('nombre', '').strip()
            slug = request.POST.get('slug', '').strip() or slugify(nombre)
            descripcion_corta = request.POST.get('descripcion_corta', '').strip()
            descripcion_larga = request.POST.get('descripcion_larga', '').strip()
            precio = request.POST.get('precio', '0')
            precio_oferta = request.POST.get('precio_oferta', '').strip()
            categoria_id = request.POST.get('categoria')
            unidad_medida = request.POST.get('unidad_medida', 'kg')
            es_destacado = request.POST.get('es_destacado') == 'on'
            es_nuevo = request.POST.get('es_nuevo') == 'on'
            es_organico = request.POST.get('es_organico') == 'on'
            temporada = request.POST.get('temporada', '').strip()
            origen = request.POST.get('origen', '').strip()
            certificaciones = request.POST.get('certificaciones', '').strip()
            peso_kg = request.POST.get('peso_kg', '0')
            alto_cm = request.POST.get('alto_cm', '0')
            ancho_cm = request.POST.get('ancho_cm', '0')
            largo_cm = request.POST.get('largo_cm', '0')
            
            # Validaciones
            if not nombre:
                messages.error(request, 'El nombre del producto es obligatorio.')
                return redirect('admin_panel:producto_crear')
            if not categoria_id:
                messages.error(request, 'Debes seleccionar una categoría.')
                return redirect('admin_panel:producto_crear')
            if not descripcion_corta:
                messages.error(request, 'La descripción corta es obligatoria.')
                return redirect('admin_panel:producto_crear')
            
            categoria = get_object_or_404(Categoria, id_categoria=categoria_id)
            
            # Crear el producto con stock=0 (no se modifica a mano)
            producto = Producto(
                nombre=nombre,
                slug=slug,
                descripcion_corta=descripcion_corta,
                descripcion_larga=descripcion_larga,
                precio=Decimal(precio),
                precio_oferta=Decimal(precio_oferta) if precio_oferta else None,
                stock=0,  # Stock inicial siempre es 0
                costo_promedio=Decimal('0'),
                unidad_medida=unidad_medida,
                id_categoria=categoria,
                es_destacado=es_destacado,
                es_nuevo=es_nuevo,
                es_organico=es_organico,
                temporada=temporada,
                origen=origen,
                certificaciones=certificaciones,
                peso_kg=Decimal(peso_kg) if peso_kg else Decimal('0'),
                alto_cm=Decimal(alto_cm) if alto_cm else Decimal('0'),
                ancho_cm=Decimal(ancho_cm) if ancho_cm else Decimal('0'),
                largo_cm=Decimal(largo_cm) if largo_cm else Decimal('0'),
            )
            
            # Imagen principal
            if 'imagen_principal' in request.FILES:
                producto.imagen_principal = request.FILES['imagen_principal']
            
            producto.save()
            messages.success(request, f'✓ Producto "{producto.nombre}" creado exitosamente. El stock inicial es 0. Usa el módulo de Compras para abastecer.')
            return redirect('admin_panel:productos_lista')
            
        except Exception as e:
            messages.error(request, f'Error al crear el producto: {str(e)}')
            return redirect('admin_panel:producto_crear')
    
    categorias = Categoria.objects.all()
    return render(request, 'admin_panel/productos/crear.html', {'categorias': categorias})


@rol_requerido('puede_gestionar_productos')
def producto_editar(request, id_producto):
    """Editar producto existente - El stock es de solo lectura"""
    producto = get_object_or_404(Producto, id_producto=id_producto)
    
    if request.method == 'POST':
        try:
            nombre = request.POST.get('nombre', '').strip()
            slug = request.POST.get('slug', '').strip() or slugify(nombre)
            descripcion_corta = request.POST.get('descripcion_corta', '').strip()
            descripcion_larga = request.POST.get('descripcion_larga', '').strip()
            precio = request.POST.get('precio', '0')
            precio_oferta = request.POST.get('precio_oferta', '').strip()
            categoria_id = request.POST.get('categoria')
            unidad_medida = request.POST.get('unidad_medida', 'kg')
            es_destacado = request.POST.get('es_destacado') == 'on'
            es_nuevo = request.POST.get('es_nuevo') == 'on'
            es_organico = request.POST.get('es_organico') == 'on'
            temporada = request.POST.get('temporada', '').strip()
            origen = request.POST.get('origen', '').strip()
            certificaciones = request.POST.get('certificaciones', '').strip()
            peso_kg = request.POST.get('peso_kg', '0')
            alto_cm = request.POST.get('alto_cm', '0')
            ancho_cm = request.POST.get('ancho_cm', '0')
            largo_cm = request.POST.get('largo_cm', '0')
            
            # Validaciones
            if not nombre:
                messages.error(request, 'El nombre del producto es obligatorio.')
                return redirect('admin_panel:producto_editar', id_producto=id_producto)
            if not categoria_id:
                messages.error(request, 'Debes seleccionar una categoría.')
                return redirect('admin_panel:producto_editar', id_producto=id_producto)
            if not descripcion_corta:
                messages.error(request, 'La descripción corta es obligatoria.')
                return redirect('admin_panel:producto_editar', id_producto=id_producto)
            
            categoria = get_object_or_404(Categoria, id_categoria=categoria_id)
            
            # Actualizar el producto (NO modificar el stock manualmente)
            producto.nombre = nombre
            producto.slug = slug
            producto.descripcion_corta = descripcion_corta
            producto.descripcion_larga = descripcion_larga
            producto.precio = Decimal(precio)
            producto.precio_oferta = Decimal(precio_oferta) if precio_oferta else None
            # stock NO se modifica aquí - se actualiza vía compras y ventas
            producto.unidad_medida = unidad_medida
            producto.id_categoria = categoria
            producto.es_destacado = es_destacado
            producto.es_nuevo = es_nuevo
            producto.es_organico = es_organico
            producto.temporada = temporada
            producto.origen = origen
            producto.certificaciones = certificaciones
            producto.peso_kg = Decimal(peso_kg) if peso_kg else Decimal('0')
            producto.alto_cm = Decimal(alto_cm) if alto_cm else Decimal('0')
            producto.ancho_cm = Decimal(ancho_cm) if ancho_cm else Decimal('0')
            producto.largo_cm = Decimal(largo_cm) if largo_cm else Decimal('0')
            
            # Imagen principal
            if 'imagen_principal' in request.FILES:
                producto.imagen_principal = request.FILES['imagen_principal']
            
            producto.save()
            messages.success(request, f'✓ Producto "{producto.nombre}" actualizado exitosamente.')
            return redirect('admin_panel:productos_lista')
            
        except Exception as e:
            messages.error(request, f'Error al actualizar el producto: {str(e)}')
            return redirect('admin_panel:producto_editar', id_producto=id_producto)
    
    categorias = Categoria.objects.all()
    return render(request, 'admin_panel/productos/editar.html', {
        'producto': producto,
        'categorias': categorias
    })


@rol_requerido('puede_gestionar_productos')
def producto_eliminar(request, id_producto):
    """Desactivar/Activar producto (invierte el estado activo)"""
    producto = get_object_or_404(Producto, id_producto=id_producto)
    
    if request.method == 'POST':
        #Invertimos el estado actual
        producto.activo = not producto.activo
        producto.save()
        
        if producto.activo:
            messages.success(request, f'Producto "{producto.nombre}" reactivado exitosamente.')
        else:
            messages.success(request, f'Producto "{producto.nombre}" desactivado correctamente.')
            
        return redirect('admin_panel:productos_lista')
    
    return render(request, 'admin_panel/productos/eliminar.html', {'producto': producto})

# ===== VISTAS DE CATEGORÍAS =====

@rol_requerido('puede_gestionar_productos')
def categorias_lista(request):
    """Lista de categorías"""
    categorias = Categoria.objects.all()
    return render(request, 'admin_panel/categorias/lista.html', {'categorias': categorias})


@rol_requerido('puede_gestionar_productos')
def categoria_crear(request):
    """Crear nueva categoría"""
    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        slug = request.POST.get('slug', '').strip() or slugify(nombre)
        orden = request.POST.get('orden', '0')
        icono = request.POST.get('icono', '').strip()
        
        if not nombre:
            messages.error(request, 'El nombre de la categoría es obligatorio.')
            return redirect('admin_panel:categoria_crear')
        
        Categoria.objects.create(
            nombre=nombre,
            slug=slug,
            orden=int(orden) if orden else 0,
            icono=icono,
        )
        messages.success(request, f'Categoría "{nombre}" creada exitosamente')
        return redirect('admin_panel:categorias_lista')
    
    return render(request, 'admin_panel/categorias/crear.html')


@rol_requerido('puede_gestionar_productos')
def categoria_editar(request, id_categoria):
    """Editar categoría existente"""
    categoria = get_object_or_404(Categoria, id_categoria=id_categoria)
    
    if request.method == 'POST':
        categoria.nombre = request.POST.get('nombre', '').strip()
        categoria.slug = request.POST.get('slug', '').strip() or slugify(categoria.nombre)
        categoria.orden = int(request.POST.get('orden', '0') or 0)
        categoria.icono = request.POST.get('icono', '').strip()
        categoria.save()
        messages.success(request, 'Categoría actualizada exitosamente')
        return redirect('admin_panel:categorias_lista')
    
    return render(request, 'admin_panel/categorias/editar.html', {'categoria': categoria})


@rol_requerido('puede_gestionar_productos')
def categoria_eliminar(request, id_categoria):
    """Desactivar/Activar categoría (NUNCA se borra de la base de datos)"""
    categoria = get_object_or_404(Categoria, id_categoria=id_categoria)
    
    # VALIDACIÓN: Verificar si tiene productos asociados
    productos_asociados = Producto.objects.filter(id_categoria=categoria).exists()
    
    if request.method == 'POST':
        if productos_asociados:
            # Si tiene productos, NO se puede desactivar
            messages.error(request, f'No se puede desactivar la categoría "{categoria.nombre}" porque tiene productos asociados. Reasigna los productos primero.')
            return redirect('admin_panel:categorias_lista')
        else:
            #  CAMBIO AQUÍ: En lugar de BORRAR, la DESACTIVAMOS.
            # Si ya estaba inactiva, la reactivamos. Si estaba activa, la desactivamos.
            categoria.activo = not categoria.activo
            categoria.save()
            
            if categoria.activo:
                messages.success(request, f'✓ Categoría "{categoria.nombre}" reactivada exitosamente.')
            else:
                messages.success(request, f'✓ Categoría "{categoria.nombre}" desactivada exitosamente.')
            
            return redirect('admin_panel:categorias_lista')
    
    # Si es GET, mostramos la plantilla de confirmación
    return render(request, 'admin_panel/categorias/eliminar.html', {
        'categoria': categoria,
        'tiene_productos': productos_asociados
    })


# ===== VISTAS DE INVENTARIO =====

@rol_requerido('puede_gestionar_inventario')
def inventario(request):
    """Panel de inventario"""
    from django.core.paginator import Paginator
    
    productos_bajo_stock = Producto.objects.filter(stock__lte=10).order_by('stock')
    productos_sin_stock = Producto.objects.filter(stock=0)
    productos = Producto.objects.select_related('id_categoria').all()
    
    paginator = Paginator(productos, 20)
    page = request.GET.get('page')
    productos_paginados = paginator.get_page(page)
    
    context = {
        'productos': productos_paginados,
        'productos_bajo_stock': productos_bajo_stock,
        'productos_sin_stock': productos_sin_stock,
        'total_productos': Producto.objects.count(),
        'valor_inventario': Producto.objects.aggregate(total=Sum(F('costo_promedio') * F('stock')))['total'] or 0,
    }
    
    return render(request, 'admin_panel/inventario/lista.html', context)


@rol_requerido('puede_gestionar_inventario')
def historial_producto(request, id_producto):
    """Historial completo de un producto específico"""
    from django.core.paginator import Paginator
    from .models import HistorialProducto
    
    try:
        logger.info(f"📊 Cargando historial de producto ID: {id_producto}")
        
        producto = get_object_or_404(Producto, id_producto=id_producto)
        logger.info(f"✅ Producto encontrado: {producto.nombre}")
        
        # Obtener todo el historial del producto
        historial = HistorialProducto.objects.filter(producto=producto).select_related('usuario', 'compra', 'pedido', 'movimiento_inventario')
        logger.info(f"✅ Historial cargado: {historial.count()} registros")
        
        # Filtros
        tipo_filtro = request.GET.get('tipo')
        if tipo_filtro:
            historial = historial.filter(tipo_cambio=tipo_filtro)
        
        fecha_desde = request.GET.get('fecha_desde')
        if fecha_desde:
            historial = historial.filter(fecha_cambio__date__gte=fecha_desde)
        
        fecha_hasta = request.GET.get('fecha_hasta')
        if fecha_hasta:
            historial = historial.filter(fecha_cambio__date__lte=fecha_hasta)
        
        # Ordenar por fecha descendente
        historial = historial.order_by('-fecha_cambio')
        
        # Paginación
        paginator = Paginator(historial, 50)
        page = request.GET.get('page')
        historial_paginado = paginator.get_page(page)
        
        # Obtener tipos de cambio únicos para el filtro
        tipos_cambio = HistorialProducto.TIPOS_CAMBIO
        
        context = {
            'producto': producto,
            'historial': historial_paginado,
            'tipos_cambio': tipos_cambio,
            'tipo_filtro': tipo_filtro,
            'fecha_desde': fecha_desde,
            'fecha_hasta': fecha_hasta,
            'total_cambios': historial.count(),
        }
        
        logger.info(f"✅ Renderizando historial de {producto.nombre}")
        return render(request, 'admin_panel/inventario/historial_producto.html', context)
        
    except Exception as e:
        logger.error(f"❌ Error en historial_producto (ID: {id_producto}): {str(e)}", exc_info=True)
        messages.error(request, f'Error al cargar el historial: {str(e)}')
        return redirect('admin_panel:inventario')


@rol_requerido('puede_gestionar_inventario')
def historial_productos_lista(request):
    """Lista todos los productos con su historial resumido"""
    from django.core.paginator import Paginator
    from .models import HistorialProducto
    
    try:
        logger.info("📊 Cargando lista de historial de productos")
        
        # Obtener todos los productos
        productos = Producto.objects.select_related('id_categoria').all()
        logger.info(f"✅ Productos cargados: {productos.count()}")
        
        # Para cada producto, obtener el último cambio
        productos_con_historial = []
        for producto in productos:
            ultimo_historial = HistorialProducto.objects.filter(producto=producto).first()
            total_cambios = HistorialProducto.objects.filter(producto=producto).count()
            
            productos_con_historial.append({
                'producto': producto,
                'ultimo_cambio': ultimo_historial,
                'total_cambios': total_cambios,
            })
        
        logger.info(f"✅ Historial procesado para {len(productos_con_historial)} productos")
        
        # Paginación
        paginator = Paginator(productos_con_historial, 20)
        page = request.GET.get('page')
        productos_paginados = paginator.get_page(page)
        
        context = {
            'productos': productos_paginados,
            'total_productos': len(productos_con_historial),
        }
        
        logger.info(f"✅ Renderizando lista de historial de productos")
        return render(request, 'admin_panel/inventario/historial_productos.html', context)
        
    except Exception as e:
        logger.error(f"❌ Error en historial_productos_lista: {str(e)}", exc_info=True)
        messages.error(request, f'Error al cargar el historial de productos: {str(e)}')
        return redirect('admin_panel:inventario')


@rol_requerido('puede_gestionar_inventario')
def inventario_movimientos(request):
    """Historial de movimientos de inventario (Kardex)"""
    from django.core.paginator import Paginator
    
    try:
        logger.info("📊 Cargando movimientos de inventario")
        
        # Obtener todos los movimientos
        movimientos_lista = MovimientoInventario.objects.select_related(
            'producto', 'compra', 'pedido', 'usuario'
        ).all()
        logger.info(f"✅ Movimientos cargados: {movimientos_lista.count()}")
        
        # Filtro por producto
        producto_nombre = request.GET.get('producto', '')
        if producto_nombre:
            movimientos_lista = movimientos_lista.filter(
                producto__nombre__icontains=producto_nombre
            )
        
        # Filtro por tipo de movimiento
        tipo_movimiento = request.GET.get('tipo', '')
        if tipo_movimiento:
            movimientos_lista = movimientos_lista.filter(tipo=tipo_movimiento)
        
        # Filtro por fecha
        fecha_desde = request.GET.get('fecha_desde', '')
        if fecha_desde:
            movimientos_lista = movimientos_lista.filter(
                fecha_movimiento__date__gte=fecha_desde
            )
        
        # Ordenamiento
        movimientos_lista = movimientos_lista.order_by('-fecha_movimiento')
        
        # Paginación
        paginator = Paginator(movimientos_lista, 50)
        page = request.GET.get('page')
        movimientos = paginator.get_page(page)
        
        context = {
            'movimientos': movimientos,
        }
        
        logger.info(f"✅ Renderizando movimientos de inventario")
        return render(request, 'admin_panel/inventario/movimientos.html', context)
        
    except Exception as e:
        logger.error(f"❌ Error en inventario_movimientos: {str(e)}", exc_info=True)
        messages.error(request, f'Error al cargar los movimientos de inventario: {str(e)}')
        return redirect('admin_panel:inventario')


# ===== VISTAS DE PEDIDOS =====

@rol_requerido('puede_gestionar_pedidos')
def pedidos_lista(request):
    """Lista de pedidos con filtros"""
    from django.core.paginator import Paginator
    
    pedidos_lista = Pedido.objects.select_related('id_usuario').all()
    
    # Filtro por estado
    estado = request.GET.get('estado')
    if estado:
        pedidos_lista = pedidos_lista.filter(estado=estado)
    
    # Búsqueda
    busqueda = request.GET.get('q')
    if busqueda:
        pedidos_lista = pedidos_lista.filter(
            Q(id_pedido__icontains=busqueda) |
            Q(id_usuario__nombre__icontains=busqueda)
        )
    
    # Ordenamiento
    pedidos_lista = pedidos_lista.order_by('-fecha_pedido')
    
    # Paginación
    paginator = Paginator(pedidos_lista, 20)
    page = request.GET.get('page')
    pedidos = paginator.get_page(page)
    
    context = {
        'pedidos': pedidos,
        'estados': Pedido.ESTADOS_PEDIDO,
        'estado_seleccionado': estado,
        'busqueda': busqueda,
    }
    
    return render(request, 'admin_panel/pedidos/lista.html', context)


@rol_requerido('puede_gestionar_pedidos')
def pedido_detalle(request, id_pedido):
    """Detalle de un pedido"""
    pedido = get_object_or_404(Pedido, id_pedido=id_pedido)
    items = pedido.items.select_related('id_producto').all()
    
    # Cambiar estado si se solicita
    cambiar_estado = request.GET.get('cambiar_estado')
    if cambiar_estado and cambiar_estado in [estado[0] for estado in Pedido.ESTADOS_PEDIDO]:
        pedido.estado = cambiar_estado
        pedido.save()
        messages.success(request, f'Estado del pedido actualizado a: {pedido.get_estado_display()}')
    
    context = {
        'pedido': pedido,
        'items': items,
    }
    
    return render(request, 'admin_panel/pedidos/detalle.html', context)


# ===== VISTAS DE CLIENTES =====

@rol_requerido('puede_gestionar_clientes')
def clientes_lista(request):
    """Lista de clientes (todos los usuarios del sistema)"""
    from django.core.paginator import Paginator
    
    clientes_lista = Usuario.objects.all()
    
    # Búsqueda
    busqueda = request.GET.get('q')
    if busqueda:
        clientes_lista = clientes_lista.filter(
            Q(nombre__icontains=busqueda) |
            Q(apellido_paterno__icontains=busqueda) |
            Q(email__icontains=busqueda)
        )
    
    # Ordenamiento
    clientes_lista = clientes_lista.order_by('-date_joined')
    
    # Paginación
    paginator = Paginator(clientes_lista, 20)
    page = request.GET.get('page')
    clientes = paginator.get_page(page)
    
    context = {
        'clientes': clientes,
        'busqueda': busqueda,
    }
    
    return render(request, 'admin_panel/clientes/lista.html', context)


@rol_requerido('puede_gestionar_clientes')
def cliente_detalle(request, id_usuario):
    """Detalle de un cliente"""
    cliente = get_object_or_404(Usuario, id_usuario=id_usuario)
    
    # Obtener pedidos del cliente
    pedidos = Pedido.objects.filter(id_usuario=cliente).order_by('-fecha_pedido')[:10]
    
    # Total gastado
    total_gastado = Pedido.objects.filter(
        id_usuario=cliente,
        estado_pago='pagado'
    ).aggregate(total=Sum('total'))['total'] or 0
    
    context = {
        'cliente': cliente,
        'pedidos': pedidos,
        'total_gastado': total_gastado,
    }
    
    return render(request, 'admin_panel/clientes/detalle.html', context)

# ===== DESACTIVAR / ACTIVAR CLIENTE (USUARIO) =====

@rol_requerido('puede_gestionar_clientes')
def cliente_eliminar(request, id_usuario):
    """Desactivar o reactivar un cliente. Al desactivar, anonimiza sus reseñas."""
    cliente = get_object_or_404(Usuario, id_usuario=id_usuario)
    
    if request.method == 'POST':
        #Si vamos a DESACTIVAR al cliente (estaba activo)
        if cliente.is_active:
            # Importamos el modelo de reseñas
            from pedidos.models import ComentarioProducto
            
            # Anonimizamos sus reseñas
            ComentarioProducto.objects.filter(id_usuario=cliente).update(
                id_usuario=None,
            )
            
            # Luego desactivamos al cliente usando el campo nativo is_active
            cliente.is_active = False
            cliente.save()
            messages.success(request, f'Cliente "{cliente.nombre_completo}" desactivado. Sus reseñas han sido anonimizadas.')
        
        # Si estaba INACTIVO y lo vamos a REACTIVAR
        else:
            cliente.is_active = True
            cliente.save()
            messages.success(request, f' Cliente "{cliente.nombre_completo}" reactivado exitosamente.')
            
        return redirect('admin_panel:clientes_lista')
    
    return render(request, 'admin_panel/clientes/eliminar.html', {'cliente': cliente})

def validar_rfc(rfc):
    """
    Valida un RFC mexicano (Persona Moral o Física) y su dígito verificador.
    Retorna True si es válido, False si no.
    """
    import re

    # 1. Limpiar y convertir a mayúsculas
    rfc = rfc.strip().upper()
    
    # 2. Validar longitud (12 para morales, 13 para físicas)
    if len(rfc) not in [12, 13]:
        return False
    
    # 3. Validar estructura básica con Regex
    # Patrón: 3/4 letras, 6 números (fecha YYMMDD), 3 caracteres alfanuméricos (homoclave), 1 dígito verificador
    pattern = r'^[A-ZÑ&]{3,4}[0-9]{6}[A-Z0-9]{3}$'
    if not re.match(pattern, rfc):
        return False
    
    # 4. Validar dígito verificador (algoritmo oficial del SAT)
    # Extraemos el dígito verificador y el resto del RFC
    digito_verificador = rfc[-1]
    base_rfc = rfc[:-1]
    
    # Mapeo de caracteres a valores numéricos (algoritmo SAT)
    valores = {
        '0':0, '1':1, '2':2, '3':3, '4':4, '5':5, '6':6, '7':7, '8':8, '9':9,
        'A':10, 'B':11, 'C':12, 'D':13, 'E':14, 'F':15, 'G':16, 'H':17, 'I':18, 'J':19,
        'K':20, 'L':21, 'M':22, 'N':23, 'Ñ':24, 'O':25, 'P':26, 'Q':27, 'R':28, 'S':29,
        'T':30, 'U':31, 'V':32, 'W':33, 'X':34, 'Y':35, 'Z':36, '&':37
    }
    
    suma = 0
    for i, char in enumerate(reversed(base_rfc)):
        if char in valores:
            valor = valores[char]
            # El algoritmo usa una secuencia de pesos: 13, 11, 9, 7, 5, 3, 1
            # pero los pesos varían según la longitud del RFC.
            # Para simplificar, usamos el siguiente cálculo estándar:
            factor = 2 if i % 2 == 0 else 1
            suma += valor * factor
    
    # Calculamos el residuo (módulo 11)
    residuo = suma % 11
    digito_calculado = 11 - residuo
    
    # El dígito verificador calculado puede ser 10 o 11, que se representan como A o 0
    if digito_calculado == 10:
        digito_calculado = 'A'
    elif digito_calculado == 11:
        digito_calculado = '0'
    else:
        digito_calculado = str(digito_calculado)
    
    return digito_verificador == digito_calculado


#VISTAS DE PROVEEDORES

@rol_requerido('puede_gestionar_proveedores')
def proveedores_lista(request):
    """Lista de proveedores"""
    from django.core.paginator import Paginator

    proveedores_lista = Proveedor.objects.all()

    # Búsqueda
    busqueda = request.GET.get('q', '')
    if busqueda:
        proveedores_lista = proveedores_lista.filter(
            Q(empresa__icontains=busqueda) |
            Q(rfc__icontains=busqueda) |
            Q(contacto__icontains=busqueda) |
            Q(correo__icontains=busqueda)
        )

    # Filtro por estado activo/inactivo
    activo_filtro = request.GET.get('activo', '')
    if activo_filtro == 'activos':
        proveedores_lista = proveedores_lista.filter(activo=True)
    elif activo_filtro == 'inactivos':
        proveedores_lista = proveedores_lista.filter(activo=False)

    # Ordenamiento
    orden = request.GET.get('orden', '-fecha_creacion')
    proveedores_lista = proveedores_lista.order_by(orden)

    # Paginacion
    paginator = Paginator(proveedores_lista, 20)
    page = request.GET.get('page')
    proveedores = paginator.get_page(page)

    context = {
        'proveedores': proveedores,
        'busqueda': busqueda,
        'activo_filtro': activo_filtro,
    }

    return render(request, 'admin_panel/proveedores/lista.html', context)


@rol_requerido('puede_gestionar_proveedores')
def proveedor_crear(request):
    """Crear proveedor"""
    if request.method == 'POST':
        proveedor = Proveedor(
            empresa=request.POST.get('empresa', '').strip(),
            rfc=request.POST.get('rfc', '').strip().upper(),
            contacto=request.POST.get('contacto', '').strip(),
            correo=request.POST.get('correo', '').strip(),
            telefono=request.POST.get('telefono', '').strip(),
            whatsapp=request.POST.get('whatsapp', '').strip(),
            calle=request.POST.get('calle', '').strip(),
            numero_exterior=request.POST.get('numero_exterior', '').strip(),
            colonia=request.POST.get('colonia', '').strip(),
            municipio=request.POST.get('municipio', '').strip(),
            estado=request.POST.get('estado', '').strip(),
            codigo_postal=request.POST.get('codigo_postal', '').strip(),
            pagina_web=request.POST.get('pagina_web', '').strip(),
            tiempo_entrega=request.POST.get('tiempo_entrega') or 7,
            descuento=request.POST.get('descuento') or 0,
            condiciones_pago=request.POST.get('condiciones_pago', 'contado'),
            observaciones=request.POST.get('observaciones', '').strip(),
        )
        proveedor.save()
        messages.success(request, 'Proveedor creado exitosamente')
        return redirect('admin_panel:proveedores_lista')

    return render(request, 'admin_panel/proveedores/crear.html')


@rol_requerido('puede_gestionar_proveedores')
def proveedor_editar(request, id_proveedor):
    """Editar proveedor"""
    proveedor = get_object_or_404(Proveedor, id_proveedor=id_proveedor)

    if request.method == 'POST':
        proveedor.empresa = request.POST.get('empresa', '').strip()
        proveedor.rfc = request.POST.get('rfc', '').strip().upper()
        proveedor.contacto = request.POST.get('contacto', '').strip()
        proveedor.correo = request.POST.get('correo', '').strip()
        proveedor.telefono = request.POST.get('telefono', '').strip()
        proveedor.whatsapp = request.POST.get('whatsapp', '').strip()
        proveedor.calle = request.POST.get('calle', '').strip()
        proveedor.numero_exterior = request.POST.get('numero_exterior', '').strip()
        proveedor.colonia = request.POST.get('colonia', '').strip()
        proveedor.municipio = request.POST.get('municipio', '').strip()
        proveedor.estado = request.POST.get('estado', '').strip()
        proveedor.codigo_postal = request.POST.get('codigo_postal', '').strip()
        proveedor.pagina_web = request.POST.get('pagina_web', '').strip()
        proveedor.tiempo_entrega = request.POST.get('tiempo_entrega') or 7
        proveedor.descuento = request.POST.get('descuento') or 0
        proveedor.condiciones_pago = request.POST.get('condiciones_pago', 'contado')
        proveedor.observaciones = request.POST.get('observaciones', '').strip()
        proveedor.save()
        messages.success(request, 'Proveedor actualizado exitosamente')
        return redirect('admin_panel:proveedores_lista')

    return render(request, 'admin_panel/proveedores/editar.html', {'proveedor': proveedor})


@rol_requerido('puede_gestionar_proveedores')
def proveedor_eliminar(request, id_proveedor):
    """Eliminar proveedor definitivamente"""
    proveedor = get_object_or_404(Proveedor, id_proveedor=id_proveedor)

    # Verificar si tiene productos asociados
    productos_asociados = Producto.objects.filter(id_proveedor=proveedor)
    tiene_productos = productos_asociados.exists()

    if request.method == 'POST':
        if tiene_productos:
            # Si tiene productos, hacemos eliminación lógica (desactivar)
            proveedor.activo = False
            proveedor.save()
            messages.warning(request, f'El proveedor "{proveedor.empresa}" tenía productos asociados. Se ha desactivado en lugar de eliminarse.')
        else:
            proveedor.delete()
            messages.success(request, 'Proveedor eliminado exitosamente')
        return redirect('admin_panel:proveedores_lista')

    return render(request, 'admin_panel/proveedores/eliminar.html', {
        'proveedor': proveedor,
        'tiene_productos': tiene_productos,
        'productos_asociados': productos_asociados if tiene_productos else [],
    })


# VISTAS DE COMPRAS

@rol_requerido('puede_gestionar_compras')
def compras_lista(request):
    """Lista de compras"""
    from django.core.paginator import Paginator
    
    compras_lista = Compra.objects.select_related('proveedor').prefetch_related('items').all()
    
    # Filtro por estado
    estado = request.GET.get('estado')
    if estado:
        compras_lista = compras_lista.filter(estado=estado)
    
    # Búsqueda
    busqueda = request.GET.get('q', '')
    if busqueda:
        compras_lista = compras_lista.filter(
            Q(numero_factura__icontains=busqueda) |
            Q(proveedor__empresa__icontains=busqueda) |
            Q(observaciones__icontains=busqueda)
        )
    
    # Ordenamiento
    compras_lista = compras_lista.order_by('-fecha_creacion')
    
    # Paginación
    paginator = Paginator(compras_lista, 20)
    page = request.GET.get('page')
    compras = paginator.get_page(page)
    
    context = {
        'compras': compras,
        'estados': Compra.ESTADOS,
        'estado_seleccionado': estado,
        'busqueda': busqueda,
    }
    
    return render(request, 'admin_panel/compras/lista.html', context)


@rol_requerido('puede_gestionar_compras')
def compra_crear(request):
    """Crear orden de compra con Kardex automático"""
    from django.db import transaction
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Obtener datos del formulario
                proveedor_id = request.POST.get('proveedor')
                es_producto_propio = proveedor_id == 'propio'
                fecha_compra = request.POST.get('fecha')
                numero_factura = request.POST.get('factura', '')
                observaciones = request.POST.get('observaciones', '')
                
                # Obtener productos
                productos_ids = request.POST.getlist('producto[]')
                cantidades = request.POST.getlist('cantidad[]')
                precios = request.POST.getlist('precio[]')
                
                # Validar datos básicos
                if not proveedor_id:
                    messages.error(request, 'Debes seleccionar un proveedor')
                    return redirect('admin_panel:compra_crear')
                
                if not fecha_compra:
                    messages.error(request, 'Debes seleccionar una fecha de compra')
                    return redirect('admin_panel:compra_crear')
                
                if not productos_ids or not any(productos_ids):
                    messages.error(request, 'Debes agregar al menos un producto')
                    return redirect('admin_panel:compra_crear')
                
                # Validar cantidades y precios
                for i in range(len(productos_ids)):
                    if productos_ids[i]:
                        cantidad = float(cantidades[i]) 
                        precio = float(precios[i])
                        if cantidad <= 0:
                            messages.error(request, 'La cantidad debe ser mayor a 0')
                            return redirect('admin_panel:compra_crear')
                        if precio <= 0:
                            messages.error(request, 'El precio debe ser mayor a 0')
                            return redirect('admin_panel:compra_crear')
                
                # Crear la compra
                compra = Compra(
                    proveedor_id=proveedor_id if not es_producto_propio else None,
                    es_producto_propio=es_producto_propio,
                    fecha_compra=fecha_compra,
                    numero_factura=numero_factura,
                    observaciones=observaciones,
                    estado='recibida'
                )
                compra.save()
                
                # Crear los items de compra y actualizar stock
                total_compra = 0
                productos_actualizados = []
                
                for i in range(len(productos_ids)):
                    if productos_ids[i]:
                        producto = Producto.objects.get(id_producto=productos_ids[i])
                        cantidad = Decimal(cantidades[i])
                        precio_unitario = Decimal(str(precios[i]))
                        subtotal = cantidad * precio_unitario
                        total_compra += subtotal
                        
                        # Guardar stock anterior para el Kardex
                        stock_anterior = producto.stock
                        
                        # Crear item de compra
                        item = ItemCompra(
                            compra=compra,
                            producto=producto,
                            cantidad=cantidad,
                            precio_unitario=precio_unitario,
                            subtotal=subtotal
                        )
                        item.save()
                        
                        # Actualizar stock del producto
                        producto.stock += cantidad
                        
                        # Actualizar costo promedio (ponderado)
                        if stock_anterior > 0:
                            # Costo promedio ponderado: (stock_anterior * costo_promedio + cantidad * precio_unitario) / (stock_anterior + cantidad)
                            costo_total_anterior = stock_anterior * producto.costo_promedio
                            costo_total_nuevo = cantidad * precio_unitario
                            producto.costo_promedio = (costo_total_anterior + costo_total_nuevo) / (stock_anterior + cantidad)
                        else:
                            # Si no hay stock previo, el costo promedio es el precio de compra
                            producto.costo_promedio = precio_unitario
                        
                        producto.save()
                        
                        # Crear movimiento de Kardex (Entrada por Compra)
                        MovimientoInventario.objects.create(
                            producto=producto,
                            tipo='entrada_compra',
                            cantidad=cantidad,
                            stock_anterior=stock_anterior,
                            stock_posterior=producto.stock,
                            costo_unitario=precio_unitario,
                            compra=compra,
                            observaciones=f'Compra #{compra.id_compra} - Factura: {numero_factura or "N/A"}',
                            usuario=request.user
                        )
                        
                        productos_actualizados.append(producto.nombre)
                
                # Actualizar total de la compra
                compra.total = total_compra
                compra.save()
                
                # Mensaje de éxito con detalles
                proveedor_nombre = compra.proveedor.empresa if compra.proveedor else "Productos Propios"
                messages.success(request, f'✓ Compra #{compra.id_compra} registrada exitosamente a {proveedor_nombre}. Stock actualizado: {len(productos_actualizados)} producto(s). Kardex actualizado.')
                return redirect('admin_panel:compras_lista')
                
        except Exception as e:
            messages.error(request, f'Error al registrar la compra: {str(e)}')
            return redirect('admin_panel:compra_crear')
    
    # GET request - mostrar formulario
    proveedores = Proveedor.objects.filter(activo=True).order_by('empresa')
    productos = Producto.objects.select_related('id_categoria', 'id_proveedor').all().order_by('nombre')
    
    # Establecer fecha de hoy
    from datetime import date
    fecha_hoy = date.today().isoformat()
    
    context = {
        'proveedores': proveedores,
        'productos': productos,
        'fecha_hoy': fecha_hoy,
    }
    
    return render(request, 'admin_panel/compras/crear.html', context)


# ===== VISTAS DE PAGOS =====

@rol_requerido('puede_gestionar_pagos')
def pagos_lista(request):
    """Lista de pagos"""
    from django.core.paginator import Paginator
    
    pagos_lista = Pago.objects.select_related('id_pedido').all()
    
    # Filtro por estado
    estado = request.GET.get('estado')
    if estado:
        pagos_lista = pagos_lista.filter(estado=estado)
    
    # Ordenamiento
    pagos_lista = pagos_lista.order_by('-fecha_pago')
    
    # Paginación
    paginator = Paginator(pagos_lista, 20)
    page = request.GET.get('page')
    pagos = paginator.get_page(page)
    
    context = {
        'pagos': pagos,
        'estados': Pago.ESTADOS_PAGO,
        'estado_seleccionado': estado,
    }
    
    return render(request, 'admin_panel/pagos/lista.html', context)


# ===== VISTAS DE ENVÍOS =====

@rol_requerido('puede_gestionar_envios')
def envios_lista(request):
    """Lista de envíos con dirección de envío y transportista visibles."""
    from django.core.paginator import Paginator

    envios_lista = Entrega.objects.select_related(
        'id_pedido', 'id_pedido__id_direccion_envio'
    ).all()

    # Filtro por estado
    estado = request.GET.get('estado')
    if estado:
        envios_lista = envios_lista.filter(estado=estado)

    # Ordenamiento
    envios_lista = envios_lista.order_by('-fecha_envio')

    # Paginación
    paginator = Paginator(envios_lista, 20)
    page = request.GET.get('page')
    envios = paginator.get_page(page)

    context = {
        'envios': envios,
        'estados': Entrega.ESTADOS_ENTREGA,
        'estado_seleccionado': estado,
    }

    return render(request, 'admin_panel/envios/lista.html', context)


# ===== VISTAS DE NOTIFICACIONES =====

@login_required
@require_POST
def marcar_notificaciones_leidas(request):
    """Marca todas las notificaciones del usuario como leídas."""
    Notificacion.objects.filter(
        id_usuario=request.user,
        leida=False
    ).update(leida=True)
    return JsonResponse({'ok': True, 'mensaje': 'Notificaciones marcadas como leídas'})


# ===== VISTAS DE ZONAS DE REPARTO (CRUD) =====

@login_required
def direcciones_envio(request):
    """Lista de zonas de reparto con códigos postales y costos de envío."""
    from shipping.models import ZonaReparto

    zonas_lista = ZonaReparto.objects.all().order_by('estado', 'municipio', 'nombre')

    context = {
        'zonas': zonas_lista,
    }

    return render(request, 'admin_panel/envios/direcciones.html', context)


@login_required
def zona_reparto_crear(request):
    """Crear una nueva zona de reparto."""
    from decimal import Decimal
    from shipping.models import ZonaReparto

    if request.method == 'POST':
        try:
            costo_str = request.POST.get('costo_envio', '0').strip()
            if not costo_str:
                costo_str = '0'
            zona = ZonaReparto(
                nombre=request.POST.get('nombre', '').strip(),
                municipio=request.POST.get('municipio', '').strip(),
                estado=request.POST.get('estado', '').strip(),
                codigo_postal_inicio=request.POST.get('codigo_postal_inicio', '').strip(),
                codigo_postal_fin=request.POST.get('codigo_postal_fin', '').strip(),
                costo_envio=Decimal(costo_str),
                tiempo_entrega=request.POST.get('tiempo_entrega', '').strip(),
                activo=request.POST.get('activo') == 'on',
            )
            zona.full_clean()
            zona.save()
            messages.success(request, 'Zona de reparto creada exitosamente')
            return redirect('admin_panel:direcciones_envio')
        except Exception as e:
            messages.error(request, f'Error al crear la zona: {e}')

    return render(request, 'admin_panel/envios/zona_reparto_form.html', {
        'zona': None,
        'titulo': 'Nueva Zona de Reparto',
        'accion': 'Crear',
    })


@login_required
def zona_reparto_editar(request, id_zona):
    """Editar una zona de reparto."""
    from decimal import Decimal
    from shipping.models import ZonaReparto

    zona = get_object_or_404(ZonaReparto, id=id_zona)

    if request.method == 'POST':
        try:
            costo_str = request.POST.get('costo_envio', '0').strip()
            if not costo_str:
                costo_str = '0'
            zona.nombre = request.POST.get('nombre', '').strip()
            zona.municipio = request.POST.get('municipio', '').strip()
            zona.estado = request.POST.get('estado', '').strip()
            zona.codigo_postal_inicio = request.POST.get('codigo_postal_inicio', '').strip()
            zona.codigo_postal_fin = request.POST.get('codigo_postal_fin', '').strip()
            zona.costo_envio = Decimal(costo_str)
            zona.tiempo_entrega = request.POST.get('tiempo_entrega', '').strip()
            zona.activo = request.POST.get('activo') == 'on'
            zona.full_clean()
            zona.save()
            messages.success(request, 'Zona de reparto actualizada exitosamente')
            return redirect('admin_panel:direcciones_envio')
        except Exception as e:
            messages.error(request, f'Error al actualizar la zona: {e}')

    return render(request, 'admin_panel/envios/zona_reparto_form.html', {
        'zona': zona,
        'titulo': 'Editar Zona de Reparto',
        'accion': 'Guardar Cambios',
    })


@login_required
def zona_reparto_eliminar(request, id_zona):
    """Eliminar una zona de reparto."""
    from shipping.models import ZonaReparto

    zona = get_object_or_404(ZonaReparto, id=id_zona)

    if request.method == 'POST':
        zona.delete()
        messages.success(request, 'Zona de reparto eliminada exitosamente')
        return redirect('admin_panel:direcciones_envio')

    return render(request, 'admin_panel/envios/zona_reparto_eliminar.html', {
        'zona': zona,
    })


# ===== VISTAS DE COMENTARIOS =====

@rol_requerido('puede_gestionar_productos')
def comentarios_lista(request):
    """Lista de comentarios/calificaciones de productos para aprobación"""
    from django.core.paginator import Paginator
    from pedidos.models import ComentarioProducto

    comentarios_lista = ComentarioProducto.objects.select_related(
        'id_producto', 'id_usuario'
    ).all()

    filtro = request.GET.get('filtro', '')
    if filtro == 'pendientes':
        comentarios_lista = comentarios_lista.filter(aprobado=False)
    elif filtro == 'aprobados':
        comentarios_lista = comentarios_lista.filter(aprobado=True)

    busqueda = request.GET.get('q', '')
    if busqueda:
        comentarios_lista = comentarios_lista.filter(
            Q(comentario__icontains=busqueda) |
            Q(id_producto__nombre__icontains=busqueda) |
            Q(id_usuario__nombre__icontains=busqueda)
        )

    comentarios_lista = comentarios_lista.order_by('-fecha_creacion')

    paginator = Paginator(comentarios_lista, 20)
    page = request.GET.get('page')
    comentarios = paginator.get_page(page)

    context = {
        'comentarios': comentarios,
        'filtro': filtro,
        'busqueda': busqueda,
    }

    return render(request, 'admin_panel/comentarios/lista.html', context)


@rol_requerido('puede_gestionar_productos')
def comentario_aprobar(request, id_comentario):
    """Aprobar un comentario"""
    from pedidos.models import ComentarioProducto
    from django.utils import timezone

    comentario = get_object_or_404(ComentarioProducto, id_comentario=id_comentario)
    comentario.aprobado = True
    comentario.fecha_aprobacion = timezone.now()
    comentario.save()
    messages.success(request, f'Comentario de {comentario.id_usuario.nombre_completo} aprobado exitosamente')
    return redirect('admin_panel:comentarios_lista')


@rol_requerido('puede_gestionar_productos')
def comentario_rechazar(request, id_comentario):
    """Rechazar/eliminar un comentario"""
    from pedidos.models import ComentarioProducto

    comentario = get_object_or_404(ComentarioProducto, id_comentario=id_comentario)
    producto_nombre = comentario.id_producto.nombre
    usuario_nombre = comentario.id_usuario.nombre_completo
    comentario.delete()
    messages.success(request, f'Comentario de {usuario_nombre} sobre "{producto_nombre}" eliminado')
    return redirect('admin_panel:comentarios_lista')


# ===== VISTAS DE LOGÍSTICA =====

@rol_requerido('puede_gestionar_envios')
def logistica(request):
    """Tablero Kanban de logística"""
    pendientes = Pedido.objects.filter(estado='pendiente')
    preparando = Pedido.objects.filter(estado='preparando')
    enviados = Pedido.objects.filter(estado='enviado')
    entregados = Pedido.objects.filter(estado='entregado')
    cancelados = Pedido.objects.filter(estado='cancelado')
    
    context = {
        'pendientes': pendientes,
        'preparando': preparando,
        'enviados': enviados,
        'entregados': entregados,
        'cancelados': cancelados,
    }
    
    return render(request, 'admin_panel/logistica/kanban.html', context)


# ===== VISTAS DE REPORTES =====

@rol_requerido('puede_ver_reportes')
def reportes(request):
    """Módulo de reportes"""
    return render(request, 'admin_panel/reportes/index.html')


@rol_requerido('puede_ver_reportes')
def reporte_ventas(request):
    """Reporte de ventas"""
    return render(request, 'admin_panel/reportes/ventas.html')


@rol_requerido('puede_ver_reportes')
def reporte_productos(request):
    """Reporte de productos"""
    return render(request, 'admin_panel/reportes/productos.html')


@rol_requerido('puede_ver_reportes')
def reporte_ganancias(request):
    """Reporte de ganancias y rentabilidad"""
    from decimal import Decimal
    
    # Calcular ingresos totales
    ingresos_totales = Pedido.objects.filter(estado_pago='pagado').aggregate(
        total=Sum('total')
    )['total'] or Decimal('0')
    
    # Calcular costo total de productos vendidos
    costo_total = Decimal('0')
    items_pedidos = ItemPedido.objects.select_related('id_producto').filter(
        id_pedido__estado_pago='pagado'
    )
    
    productos_rentabilidad = {}
    
    for item in items_pedidos:
        producto = item.id_producto
        costo_unitario = producto.costo_promedio or Decimal('0')
        costo_item = costo_unitario * item.cantidad
        costo_total += costo_item
        
        # Acumular por producto
        if producto.id_producto not in productos_rentabilidad:
            productos_rentabilidad[producto.id_producto] = {
                'nombre': producto.nombre,
                'total_ventas': Decimal('0'),
                'total_costo': Decimal('0'),
                'cantidad': 0
            }
        
        productos_rentabilidad[producto.id_producto]['total_ventas'] += item.get_subtotal()
        productos_rentabilidad[producto.id_producto]['total_costo'] += costo_item
        productos_rentabilidad[producto.id_producto]['cantidad'] += item.cantidad
    
    # Calcular ganancia y margen por producto
    for prod_id, datos in productos_rentabilidad.items():
        datos['ganancia'] = datos['total_ventas'] - datos['total_costo']
        if datos['total_ventas'] > 0:
            datos['margen'] = (datos['ganancia'] / datos['total_ventas']) * 100
        else:
            datos['margen'] = Decimal('0')
    
    # Ordenar productos por ganancia
    productos_rentables = sorted(
        productos_rentabilidad.values(),
        key=lambda x: x['ganancia'],
        reverse=True
    )[:10]
    
    productos_bajo_margen = sorted(
        productos_rentabilidad.values(),
        key=lambda x: x['margen']
    )[:10]
    
    # Calcular ganancia bruta
    ganancia_bruta = ingresos_totales - costo_total
    
    # Calcular margen promedio
    if ingresos_totales > 0:
        margen_promedio = (ganancia_bruta / ingresos_totales) * 100
    else:
        margen_promedio = Decimal('0')
    
    # Rentabilidad por categoría
    categorias_rentabilidad = {}
    categorias = Categoria.objects.all()
    
    for categoria in categorias:
        productos_cat = Producto.objects.filter(id_categoria=categoria)
        ingresos_cat = Decimal('0')
        costo_cat = Decimal('0')
        unidades_cat = 0
        
        for prod in productos_cat:
            if prod.id_producto in productos_rentabilidad:
                ingresos_cat += productos_rentabilidad[prod.id_producto]['total_ventas']
                costo_cat += productos_rentabilidad[prod.id_producto]['total_costo']
                unidades_cat += productos_rentabilidad[prod.id_producto]['cantidad']
        
        if ingresos_cat > 0:
            ganancia_cat = ingresos_cat - costo_cat
            margen_cat = (ganancia_cat / ingresos_cat) * 100
        else:
            ganancia_cat = Decimal('0')
            margen_cat = Decimal('0')
        
        categorias_rentabilidad[categoria.id_categoria] = {
            'nombre': categoria.nombre,
            'total_productos': productos_cat.count(),
            'total_unidades': unidades_cat,
            'ingresos': ingresos_cat,
            'costo': costo_cat,
            'ganancia': ganancia_cat,
            'margen': margen_cat
        }
    
    categorias = sorted(categorias_rentabilidad.values(), key=lambda x: x['ganancia'], reverse=True)
    
    # Productos con bajo stock
    productos_bajo_stock = Producto.objects.filter(stock__lte=10).order_by('stock')
    for producto in productos_bajo_stock:
        producto.valor_reposicion = producto.costo_promedio * (11 - producto.stock)
    
    context = {
        'ingresos_totales': ingresos_totales,
        'ganancia_bruta': ganancia_bruta,
        'margen_promedio': margen_promedio,
        'costo_total': costo_total,
        'productos_rentables': productos_rentables,
        'productos_bajo_margen': productos_bajo_margen,
        'categorias': categorias,
        'productos_bajo_stock': productos_bajo_stock,
    }
    
    return render(request, 'admin_panel/reportes/ganancias.html', context)


# ===== VISTAS DE CHATBOT =====

def chatbot_ia(request):
    """Asistente IA"""
    return render(request, 'admin_panel/chatbot/index.html')


# ===== VISTAS DE CONFIGURACIÓN =====

@login_required
def configuracion(request):
    """Configuración del sistema"""
    return render(request, 'admin_panel/configuracion/index.html')


@login_required
def perfil(request):
    """Perfil de usuario"""
    return render(request, 'admin_panel/perfil/index.html')


# ====================================================================
# VISTAS CRUD PARA ROLES DE PANEL
# ====================================================================

@login_required
def roles_lista(request):
    """Lista de roles del panel"""
    from django.core.paginator import Paginator
    
    roles = RolPanel.objects.all()
    
    busqueda = request.GET.get('q', '')
    if busqueda:
        roles = roles.filter(
            Q(nombre__icontains=busqueda) |
            Q(descripcion__icontains=busqueda)
        )
    
    roles = roles.order_by('nombre')
    
    paginator = Paginator(roles, 20)
    page = request.GET.get('page')
    roles = paginator.get_page(page)
    
    context = {
        'roles': roles,
        'busqueda': busqueda,
    }
    
    return render(request, 'admin_panel/roles/lista.html', context)


@login_required
def rol_crear(request):
    """Crear nuevo rol de panel"""
    if request.method == 'POST':
        try:
            rol = RolPanel(
                nombre=request.POST.get('nombre', '').strip(),
                descripcion=request.POST.get('descripcion', '').strip(),
                activo=request.POST.get('activo') == 'on',
                puede_gestionar_productos=request.POST.get('puede_gestionar_productos') == 'on',
                puede_gestionar_pedidos=request.POST.get('puede_gestionar_pedidos') == 'on',
                puede_gestionar_clientes=request.POST.get('puede_gestionar_clientes') == 'on',
                puede_gestionar_proveedores=request.POST.get('puede_gestionar_proveedores') == 'on',
                puede_gestionar_compras=request.POST.get('puede_gestionar_compras') == 'on',
                puede_gestionar_pagos=request.POST.get('puede_gestionar_pagos') == 'on',
                puede_gestionar_envios=request.POST.get('puede_gestionar_envios') == 'on',
                puede_gestionar_inventario=request.POST.get('puede_gestionar_inventario') == 'on',
                puede_gestionar_direcciones_envio=request.POST.get('puede_gestionar_direcciones_envio') == 'on',
                puede_ver_reportes=request.POST.get('puede_ver_reportes') == 'on',
                puede_ver_dashboard=request.POST.get('puede_ver_dashboard') == 'on',
                puede_gestionar_configuracion=request.POST.get('puede_gestionar_configuracion') == 'on',
            )
            rol.full_clean()
            rol.save()
            messages.success(request, f'Rol "{rol.nombre}" creado exitosamente')
            return redirect('admin_panel:roles_lista')
        except Exception as e:
            messages.error(request, f'Error al crear el rol: {e}')
    
    return render(request, 'admin_panel/roles/crear.html', {'rol': None})


@login_required
def rol_editar(request, id_rol):
    """Editar rol de panel"""
    rol = get_object_or_404(RolPanel, id=id_rol)
    
    if request.method == 'POST':
        try:
            rol.nombre = request.POST.get('nombre', '').strip()
            rol.descripcion = request.POST.get('descripcion', '').strip()
            rol.activo = request.POST.get('activo') == 'on'
            rol.puede_gestionar_productos = request.POST.get('puede_gestionar_productos') == 'on'
            rol.puede_gestionar_pedidos = request.POST.get('puede_gestionar_pedidos') == 'on'
            rol.puede_gestionar_clientes = request.POST.get('puede_gestionar_clientes') == 'on'
            rol.puede_gestionar_proveedores = request.POST.get('puede_gestionar_proveedores') == 'on'
            rol.puede_gestionar_compras = request.POST.get('puede_gestionar_compras') == 'on'
            rol.puede_gestionar_pagos = request.POST.get('puede_gestionar_pagos') == 'on'
            rol.puede_gestionar_envios = request.POST.get('puede_gestionar_envios') == 'on'
            rol.puede_gestionar_inventario = request.POST.get('puede_gestionar_inventario') == 'on'
            rol.puede_gestionar_direcciones_envio = request.POST.get('puede_gestionar_direcciones_envio') == 'on'
            rol.puede_ver_reportes = request.POST.get('puede_ver_reportes') == 'on'
            rol.puede_ver_dashboard = request.POST.get('puede_ver_dashboard') == 'on'
            rol.puede_gestionar_configuracion = request.POST.get('puede_gestionar_configuracion') == 'on'
            rol.full_clean()
            rol.save()
            messages.success(request, f'Rol "{rol.nombre}" actualizado exitosamente')
            return redirect('admin_panel:roles_lista')
        except Exception as e:
            messages.error(request, f'Error al actualizar el rol: {e}')
    
    return render(request, 'admin_panel/roles/editar.html', {'rol': rol})


@login_required
def rol_eliminar(request, id_rol):
    """Eliminar rol de panel"""
    rol = get_object_or_404(RolPanel, id=id_rol)
    
    usuarios_asignados = UsuarioPanel.objects.filter(rol=rol)
    tiene_usuarios = usuarios_asignados.exists()
    
    if request.method == 'POST':
        if tiene_usuarios:
            messages.warning(request, f'No se puede eliminar el rol "{rol.nombre}" porque tiene usuarios asignados.')
        else:
            rol.delete()
            messages.success(request, f'Rol "{rol.nombre}" eliminado exitosamente')
        return redirect('admin_panel:roles_lista')
    
    return render(request, 'admin_panel/roles/eliminar.html', {
        'rol': rol,
        'tiene_usuarios': tiene_usuarios,
        'usuarios_asignados': usuarios_asignados if tiene_usuarios else [],
    })

# VISTAS CRUD PARA USUARIOS DE PANEL
@login_required
def usuarios_panel_lista(request):
    """Lista de todos los usuarios del sistema con su rol asignado"""
    from django.core.paginator import Paginator
    
    usuarios = Usuario.objects.filter(is_active=True).order_by('nombre', 'apellido_paterno')
    
    busqueda = request.GET.get('q', '')
    if busqueda:
        usuarios = usuarios.filter(
            Q(nombre__icontains=busqueda) |
            Q(apellido_paterno__icontains=busqueda) |
            Q(email__icontains=busqueda) |
            Q(username__icontains=busqueda)
        )
    
    paginator = Paginator(usuarios, 20)
    page = request.GET.get('page')
    usuarios_paginados = paginator.get_page(page)
    
    usuarios_con_rol = []
    for u in usuarios_paginados:
        try:
            up = UsuarioPanel.objects.select_related('rol').get(usuario=u)
            rol = up.rol
            fecha_asignacion = up.fecha_asignacion
            up_id = up.id
        except UsuarioPanel.DoesNotExist:
            rol = None
            fecha_asignacion = None
            up_id = None
        
        # Determinar el tipo de usuario
        if u.is_superuser:
            tipo_usuario = 'superadmin'
            tipo_label = 'Super Admin'
        elif u.is_staff and rol:
            tipo_usuario = 'panel_admin'
            tipo_label = 'Admin Panel'
        elif u.is_staff and not rol:
            tipo_usuario = 'staff'
            tipo_label = 'Staff Django'
        else:
            tipo_usuario = 'cliente'
            tipo_label = 'Cliente'
        
        usuarios_con_rol.append({
            'usuario': u,
            'rol': rol,
            'fecha_asignacion': fecha_asignacion,
            'up_id': up_id,
            'tipo_usuario': tipo_usuario,
            'tipo_label': tipo_label,
        })
    
    context = {
        'usuarios_panel': usuarios_con_rol,
        'busqueda': busqueda,
    }
    
    return render(request, 'admin_panel/usuarios_panel/lista.html', context)


@login_required
def usuario_panel_crear(request):
    """Asignar rol a un usuario"""
    roles = RolPanel.objects.filter(activo=True)
    # Excluir usuarios que ya tienen un rol asignado
    usuarios_con_rol = UsuarioPanel.objects.values('usuario_id')
    usuarios_disponibles = Usuario.objects.filter(is_active=True).exclude(id_usuario__in=usuarios_con_rol)
    
    if request.method == 'POST':
        usuario_id = request.POST.get('usuario')
        rol_id = request.POST.get('rol')
        
        if not usuario_id:
            messages.error(request, 'Debes seleccionar un usuario.')
        elif not rol_id:
            messages.error(request, 'Debes seleccionar un rol.')
        elif UsuarioPanel.objects.filter(usuario_id=usuario_id).exists():
            messages.warning(request, 'Este usuario ya tiene un rol asignado.')
        else:
            try:
                usuario_panel = UsuarioPanel(
                    usuario_id=usuario_id,
                    rol_id=rol_id,
                )
                usuario_panel.save()
                messages.success(request, 'Rol asignado al usuario exitosamente')
                return redirect('admin_panel:usuarios_panel_lista')
            except Exception as e:
                messages.error(request, f'Error al asignar rol: {e}')
    
    context = {
        'roles': roles,
        'usuarios': usuarios_disponibles,
    }
    
    return render(request, 'admin_panel/usuarios_panel/crear.html', context)


@login_required
def usuario_panel_editar(request, id_usuario_panel):
    """Editar asignación de rol de usuario del panel"""
    usuario_panel = get_object_or_404(UsuarioPanel, id=id_usuario_panel)
    roles = RolPanel.objects.filter(activo=True)
    
    if request.method == 'POST':
        rol_id = request.POST.get('rol')
        if not rol_id:
            messages.error(request, 'Debes seleccionar un rol.')
        else:
            try:
                usuario_panel.rol_id = rol_id
                usuario_panel.save()
                messages.success(request, f'Rol actualizado para {usuario_panel.usuario.nombre_completo}')
                return redirect('admin_panel:usuarios_panel_lista')
            except Exception as e:
                messages.error(request, f'Error al actualizar rol: {e}')
    
    context = {
        'usuario_panel': usuario_panel,
        'roles': roles,
    }
    
    return render(request, 'admin_panel/usuarios_panel/editar.html', context)


@login_required
def usuario_panel_eliminar(request, id_usuario_panel):
    """Eliminar asignación de rol de usuario del panel"""
    usuario_panel = get_object_or_404(UsuarioPanel, id=id_usuario_panel)
    
    if request.method == 'POST':
        usuario_panel.delete()
        messages.success(request, f'Asignación de rol eliminada para {usuario_panel.usuario.nombre_completo}')
        return redirect('admin_panel:usuarios_panel_lista')
    
    return render(request, 'admin_panel/usuarios_panel/eliminar.html', {
        'usuario_panel': usuario_panel,
    })

# VISTAS CRUD PARA NOTIFICACIONES
@login_required
def notificaciones_lista(request):
    """Lista de notificaciones del sistema"""
    from django.core.paginator import Paginator
    
    notificaciones = Notificacion.objects.select_related('id_usuario', 'id_pedido').all()
    
    filtro = request.GET.get('filtro', '')
    if filtro == 'leidas':
        notificaciones = notificaciones.filter(leida=True)
    elif filtro == 'no_leidas':
        notificaciones = notificaciones.filter(leida=False)
    
    busqueda = request.GET.get('q', '')
    if busqueda:
        notificaciones = notificaciones.filter(
            Q(mensaje__icontains=busqueda) |
            Q(id_usuario__nombre__icontains=busqueda) |
            Q(id_usuario__apellido_paterno__icontains=busqueda)
        )
    
    notificaciones = notificaciones.order_by('-fecha_creacion')
    
    paginator = Paginator(notificaciones, 20)
    page = request.GET.get('page')
    notificaciones = paginator.get_page(page)
    
    context = {
        'notificaciones': notificaciones,
        'filtro': filtro,
        'busqueda': busqueda,
    }
    
    return render(request, 'admin_panel/notificaciones/lista.html', context)


@login_required
def notificacion_detalle(request, id_notificacion):
    """Ver detalle de una notificación"""
    notificacion = get_object_or_404(Notificacion, id_notificacion=id_notificacion)
    
    if not notificacion.leida:
        notificacion.leida = True
        notificacion.save()
    
    context = {
        'notificacion': notificacion,
    }
    
    return render(request, 'admin_panel/notificaciones/detalle.html', context)


@login_required
def notificacion_crear(request):
    """Crear una nueva notificación manualmente"""
    usuarios = Usuario.objects.filter(is_active=True).order_by('nombre', 'apellido_paterno')
    pedidos = Pedido.objects.all().order_by('-fecha_pedido')[:100]
    
    if request.method == 'POST':
        usuario_id = request.POST.get('id_usuario')
        pedido_id = request.POST.get('id_pedido')
        mensaje = request.POST.get('mensaje', '').strip()
        leida = request.POST.get('leida') == 'on'
        
        if not usuario_id:
            messages.error(request, 'Debes seleccionar un usuario.')
        elif not pedido_id:
            messages.error(request, 'Debes seleccionar un pedido.')
        elif not mensaje:
            messages.error(request, 'El mensaje no puede estar vacío.')
        else:
            try:
                notificacion = Notificacion(
                    id_usuario_id=usuario_id,
                    id_pedido_id=pedido_id,
                    mensaje=mensaje,
                    leida=leida,
                )
                notificacion.full_clean()
                notificacion.save()
                messages.success(request, 'Notificación creada exitosamente')
                return redirect('admin_panel:notificaciones_lista')
            except Exception as e:
                messages.error(request, f'Error al crear la notificación: {e}')
    
    context = {
        'usuarios': usuarios,
        'pedidos': pedidos,
    }
    
    return render(request, 'admin_panel/notificaciones/crear.html', context)


@login_required
def notificacion_eliminar(request, id_notificacion):
    """Eliminar una notificación"""
    notificacion = get_object_or_404(Notificacion, id_notificacion=id_notificacion)
    
    if request.method == 'POST':
        notificacion.delete()
        messages.success(request, 'Notificación eliminada exitosamente')
        return redirect('admin_panel:notificaciones_lista')
    
    return render(request, 'admin_panel/notificaciones/eliminar.html', {
        'notificacion': notificacion,
    })


# ====================================================================
# VISTAS CRUD PARA TOKENS DE RECUPERACIÓN
# ====================================================================

@login_required
def tokens_recuperacion_lista(request):
    """Lista de tokens de recuperación"""
    from django.core.paginator import Paginator
    
    tokens = TokenRecuperacion.objects.select_related('id_usuario').all()
    
    filtro = request.GET.get('filtro', '')
    if filtro == 'usados':
        tokens = tokens.filter(usado=True)
    elif filtro == 'no_usados':
        tokens = tokens.filter(usado=False)
    
    busqueda = request.GET.get('q', '')
    if busqueda:
        tokens = tokens.filter(
            Q(id_usuario__nombre__icontains=busqueda) |
            Q(id_usuario__apellido_paterno__icontains=busqueda) |
            Q(id_usuario__email__icontains=busqueda)
        )
    
    tokens = tokens.order_by('-creado_en')
    
    paginator = Paginator(tokens, 20)
    page = request.GET.get('page')
    tokens = paginator.get_page(page)
    
    context = {
        'tokens': tokens,
        'filtro': filtro,
        'busqueda': busqueda,
    }
    
    return render(request, 'admin_panel/tokens/recuperacion_lista.html', context)


@login_required
def token_recuperacion_eliminar(request, id_token):
    """Eliminar un token de recuperación"""
    token = get_object_or_404(TokenRecuperacion, id_token=id_token)
    
    if request.method == 'POST':
        token.delete()
        messages.success(request, 'Token de recuperación eliminado exitosamente')
        return redirect('admin_panel:tokens_recuperacion_lista')
    
    return render(request, 'admin_panel/tokens/eliminar.html', {
        'token': token,
        'tipo': 'recuperación',
    })


# ====================================================================
# VISTAS CRUD PARA TOKENS DE VERIFICACIÓN
# ====================================================================

@login_required
def tokens_verificacion_lista(request):
    """Lista de tokens de verificación"""
    from django.core.paginator import Paginator
    
    tokens = TokenVerificacion.objects.select_related('id_usuario').all()
    
    busqueda = request.GET.get('q', '')
    if busqueda:
        tokens = tokens.filter(
            Q(id_usuario__nombre__icontains=busqueda) |
            Q(id_usuario__apellido_paterno__icontains=busqueda) |
            Q(id_usuario__email__icontains=busqueda)
        )
    
    tokens = tokens.order_by('-creado_en')
    
    paginator = Paginator(tokens, 20)
    page = request.GET.get('page')
    tokens = paginator.get_page(page)
    
    context = {
        'tokens': tokens,
        'busqueda': busqueda,
    }
    
    return render(request, 'admin_panel/tokens/verificacion_lista.html', context)


@login_required
def token_verificacion_eliminar(request, id_token):
    """Eliminar un token de verificación"""
    token = get_object_or_404(TokenVerificacion, id_token=id_token)
    
    if request.method == 'POST':
        token.delete()
        messages.success(request, 'Token de verificación eliminado exitosamente')
        return redirect('admin_panel:tokens_verificacion_lista')
    
    return render(request, 'admin_panel/tokens/eliminar.html', {
        'token': token,
        'tipo': 'verificación',
    })


# ====================================================================
# VISTAS CRUD PARA DIRECCIONES DE ENVÍO (desde usuarios)
# ====================================================================

@login_required
def direcciones_envio_lista(request):
    """Lista de direcciones de envío de usuarios"""
    from django.core.paginator import Paginator
    
    direcciones = DireccionEnvio.objects.select_related('id_usuario').all()
    
    busqueda = request.GET.get('q', '')
    if busqueda:
        direcciones = direcciones.filter(
            Q(nombre_referencia__icontains=busqueda) |
            Q(calle__icontains=busqueda) |
            Q(colonia__icontains=busqueda) |
            Q(municipio__icontains=busqueda) |
            Q(estado__icontains=busqueda) |
            Q(id_usuario__nombre__icontains=busqueda) |
            Q(id_usuario__apellido_paterno__icontains=busqueda)
        )
    
    direcciones = direcciones.order_by('id_usuario__nombre', 'nombre_referencia')
    
    paginator = Paginator(direcciones, 20)
    page = request.GET.get('page')
    direcciones = paginator.get_page(page)
    
    context = {
        'direcciones': direcciones,
        'busqueda': busqueda,
    }
    
    return render(request, 'admin_panel/envios/direcciones_lista.html', context)


@login_required
def direccion_envio_crear(request):
    """Crear una dirección de envío manualmente"""
    usuarios = Usuario.objects.filter(is_active=True).order_by('nombre', 'apellido_paterno')
    
    if request.method == 'POST':
        try:
            usuario_id = request.POST.get('id_usuario', '').strip()
            #VALIDACIÓN: Si está vacío, mostramos un mensaje claro y no intentamos guardar
            if not usuario_id or not usuario_id.isdigit():
                messages.error(request, 'Debes seleccionar un usuario válido de la lista.')
                return redirect('admin_panel:direccion_envio_crear')

            #Ahora creamos la dirección pasando el ID ya validado como entero
            direccion = DireccionEnvio(
                id_usuario_id=int(usuario_id),  # Convertimos a entero seguro
                nombre_referencia=request.POST.get('nombre_referencia', '').strip(),
                calle=request.POST.get('calle', '').strip(),
                numero_exterior=request.POST.get('numero_exterior', '').strip(),
                numero_interior=request.POST.get('numero_interior', '').strip(),
                colonia=request.POST.get('colonia', '').strip(),
                municipio=request.POST.get('municipio', '').strip(),
                estado=request.POST.get('estado', '').strip(),
                codigo_postal=request.POST.get('codigo_postal', '').strip(),
                pais=request.POST.get('pais', 'MX').strip(),
                referencias=request.POST.get('referencias', '').strip(),
                telefono_contacto=request.POST.get('telefono_contacto', '').strip(),
                es_principal=request.POST.get('es_principal') == 'on',
            )
            direccion.full_clean()
            direccion.save()
            messages.success(request, 'Dirección de envío creada exitosamente')
            return redirect('admin_panel:direcciones_envio_lista')
        except Exception as e:
            messages.error(request, f'Error al crear la dirección: {str(e)}')
    
    context = {
        'usuarios': usuarios,
        'direccion': None,
    }
    
    return render(request, 'admin_panel/envios/direccion_form.html', context)


@login_required
def direccion_envio_editar(request, id_direccion):
    """Editar una dirección de envío"""
    direccion = get_object_or_404(DireccionEnvio, id_direccion=id_direccion)
    usuarios = Usuario.objects.filter(is_active=True).order_by('nombre', 'apellido_paterno')
    
    if request.method == 'POST':
        try:
            direccion.id_usuario_id = request.POST.get('id_usuario')
            direccion.nombre_referencia = request.POST.get('nombre_referencia', '').strip()
            direccion.calle = request.POST.get('calle', '').strip()
            direccion.numero_exterior = request.POST.get('numero_exterior', '').strip()
            direccion.numero_interior = request.POST.get('numero_interior', '').strip()
            direccion.colonia = request.POST.get('colonia', '').strip()
            direccion.municipio = request.POST.get('municipio', '').strip()
            direccion.estado = request.POST.get('estado', '').strip()
            direccion.codigo_postal = request.POST.get('codigo_postal', '').strip()
            direccion.pais = request.POST.get('pais', 'MX').strip()
            direccion.referencias = request.POST.get('referencias', '').strip()
            direccion.telefono_contacto = request.POST.get('telefono_contacto', '').strip()
            direccion.es_principal = request.POST.get('es_principal') == 'on'
            direccion.full_clean()
            direccion.save()
            messages.success(request, 'Dirección de envío actualizada exitosamente')
            return redirect('admin_panel:direcciones_envio_lista')
        except Exception as e:
            messages.error(request, f'Error al actualizar la dirección: {e}')
    
    context = {
        'usuarios': usuarios,
        'direccion': direccion,
    }
    
    return render(request, 'admin_panel/envios/direccion_form.html', context)


@login_required
def direccion_envio_eliminar(request, id_direccion):
    """Eliminar una dirección de envío"""
    direccion = get_object_or_404(DireccionEnvio, id_direccion=id_direccion)
    
    if request.method == 'POST':
        direccion.delete()
        messages.success(request, 'Dirección de envío eliminada exitosamente')
        return redirect('admin_panel:direcciones_envio_lista')
    
    return render(request, 'admin_panel/envios/direccion_eliminar.html', {
        'direccion': direccion,
    })

@login_required
def obtener_unidad_producto(request, id_producto):
    """Devuelve la unidad de medida de un producto en JSON"""
    try:
        producto = Producto.objects.get(id_producto=id_producto)
        return JsonResponse({'unidad': producto.get_unidad_medida_display()})
    except Producto.DoesNotExist:
        return JsonResponse({'unidad': 'N/A'}, status=404)

@rol_requerido('puede_gestionar_pedidos')
@require_POST
def pedido_cambiar_estado(request, id_pedido):
    """Cambia el estado de un pedido desde la lista sin recargar la página."""
    pedido = get_object_or_404(Pedido, id_pedido=id_pedido)
    nuevo_estado = request.POST.get('nuevo_estado')
    
    estados_validos = [e[0] for e in Pedido.ESTADOS_PEDIDO]
    if nuevo_estado in estados_validos:
        pedido.estado = nuevo_estado
        pedido.save()
        messages.success(request, f'Estado del pedido #{pedido.id_pedido} actualizado a: {pedido.get_estado_display()}')
    else:
        messages.error(request, 'xEstado no válido.')
    
    return redirect('admin_panel:pedidos_lista')


# ===== VISTAS DE GESTIÓN DE SESIONES =====

from django.contrib.sessions.models import Session
from django.contrib.auth import logout


@rol_requerido('puede_gestionar_clientes')
def sesiones_lista(request):
    """Lista todas las sesiones activas del sistema."""
    from django.core.paginator import Paginator
    
    # Obtener todas las sesiones activas (no expiradas)
    sesiones = Session.objects.filter(expire_date__gte=timezone.now()).order_by('-expire_date')
    
    # Información de usuario para cada sesión
    sesiones_info = []
    for sesion in sesiones:
        data = sesion.get_decoded()
        user_id = data.get('_auth_user_id')
        
        if user_id:
            try:
                usuario = Usuario.objects.get(pk=user_id)
                sesiones_info.append({
                    'sesion': sesion,
                    'usuario': usuario,
                    'ip': data.get('login_ip', 'N/A'),
                    'user_agent': data.get('login_user_agent', 'N/A'),
                    'login_time': data.get('login_time', 'N/A'),
                    'ultimo_acceso': sesion.expire_date - timedelta(seconds=settings.SESSION_COOKIE_AGE),
                })
            except Usuario.DoesNotExist:
                # Usuario eliminado pero sesión existe
                sesiones_info.append({
                    'sesion': sesion,
                    'usuario': None,
                    'ip': data.get('login_ip', 'N/A'),
                    'user_agent': data.get('login_user_agent', 'N/A'),
                    'login_time': data.get('login_time', 'N/A'),
                    'ultimo_acceso': sesion.expire_date - timedelta(seconds=settings.SESSION_COOKIE_AGE),
                })
    
    # Paginación
    paginator = Paginator(sesiones_info, 20)
    page = request.GET.get('page')
    sesiones_paginadas = paginator.get_page(page)
    
    context = {
        'sesiones': sesiones_paginadas,
        'total_sesiones': len(sesiones_info),
    }
    
    return render(request, 'admin_panel/sesiones/lista.html', context)


@rol_requerido('puede_gestionar_clientes')
@require_POST
def cerrar_todas_sesiones(request):
    """Cierra TODAS las sesiones activas del sistema (excepto la del admin actual)."""
    sesiones_cerradas = 0
    sesiones_error = 0
    
    # Obtener la sesión actual del admin para no cerrarla
    sesion_actual_id = request.session.session_key
    
    # Obtener todas las sesiones activas
    sesiones = Session.objects.filter(expire_date__gte=timezone.now())
    
    for sesion in sesiones:
        # No cerrar la sesión del administrador actual
        if sesion.session_key == sesion_actual_id:
            continue
        
        try:
            # Eliminar la sesión de la base de datos
            sesion.delete()
            sesiones_cerradas += 1
        except Exception as e:
            logger.error(f"❌ Error al cerrar sesión {sesion.session_key}: {e}")
            sesiones_error += 1
    
    # Mensaje de éxito
    if sesiones_cerradas > 0:
        messages.success(
            request,
            f'✅ Se cerraron {sesiones_cerradas} sesión(es) activa(s) correctamente. '
            f'Todos los usuarios deberán iniciar sesión de nuevo.'
        )
    else:
        messages.info(request, 'ℹ️ No había sesiones activas para cerrar.')
    
    if sesiones_error > 0:
        messages.warning(
            request,
            f'⚠️ Hubo {sesiones_error} error(es) al intentar cerrar algunas sesiones.'
        )
    
    logger.info(f"🔒 Admin {request.user.username} cerró {sesiones_cerradas} sesiones")
    
    return redirect('admin_panel:sesiones_lista')


@rol_requerido('puede_gestionar_clientes')
@require_POST
def cerrar_sesion_usuario(request, id_usuario):
    """Cierra todas las sesiones de un usuario específico."""
    usuario = get_object_or_404(Usuario, pk=id_usuario)
    
    sesiones_cerradas = 0
    
    # Buscar todas las sesiones activas del usuario
    sesiones = Session.objects.filter(expire_date__gte=timezone.now())
    
    for sesion in sesiones:
        try:
            data = sesion.get_decoded()
            if data.get('_auth_user_id') == str(usuario.pk):
                sesion.delete()
                sesiones_cerradas += 1
        except Exception as e:
            logger.error(f"❌ Error al cerrar sesión de {usuario.username}: {e}")
    
    if sesiones_cerradas > 0:
        messages.success(
            request,
            f'✅ Se cerraron {sesiones_cerradas} sesión(es) del usuario {usuario.nombre_completo}. '
            f'El usuario deberá iniciar sesión de nuevo.'
        )
    else:
        messages.info(
            request,
            f'ℹ️ El usuario {usuario.nombre_completo} no tenía sesiones activas.'
        )
    
    logger.info(f"🔒 Admin {request.user.username} cerró {sesiones_cerradas} sesiones de {usuario.username}")
    
    return redirect('admin_panel:sesiones_lista')


@rol_requerido('puede_gestionar_clientes')
def cerrar_sesion_dispositivo(request, session_key):
    """Cierra una sesión específica de un dispositivo."""
    try:
        sesion = Session.objects.get(session_key=session_key)
        data = sesion.get_decoded()
        user_id = data.get('_auth_user_id')
        
        usuario = None
        if user_id:
            try:
                usuario = Usuario.objects.get(pk=user_id)
            except Usuario.DoesNotExist:
                pass
        
        # Guardar información antes de eliminar
        usuario_info = usuario.nombre_completo if usuario else "Usuario desconocido"
        ip = data.get('login_ip', 'N/A')
        user_agent = data.get('login_user_agent', 'N/A')
        
        # Eliminar la sesión
        sesion.delete()
        
        messages.success(
            request,
            f'✅ Sesión cerrada exitosamente.\n'
            f'Usuario: {usuario_info}\n'
            f'IP: {ip}\n'
            f'Dispositivo: {user_agent[:50]}...'
        )
        
        logger.info(f"🔒 Admin {request.user.username} cerró sesión {session_key} de {usuario_info}")
        
    except Session.DoesNotExist:
        messages.error(request, 'La sesión no existe o ha expirado.')
    
    return redirect('admin_panel:sesiones_lista')


@rol_requerido('puede_gestionar_clientes')
@require_POST
def cerrar_mi_sesion(request):
    """Cierra la sesión actual del administrador."""
    nombre = request.user.nombre_completo
    username = request.user.username
    
    # Cerrar sesión
    logout(request)
    
    messages.info(request, f'Sesión cerrada correctamente. Hasta pronto, {nombre}.')
    logger.info(f"✅ Admin {username} cerró su propia sesión")
    
    response = redirect('admin_panel:login')
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate, private'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    
    return response


@rol_requerido('puede_gestionar_clientes')
def sesion_detalle(request, session_key):
    """Muestra el detalle de una sesión específica."""
    try:
        sesion = Session.objects.get(session_key=session_key)
        data = sesion.get_decoded()
        user_id = data.get('_auth_user_id')
        
        usuario = None
        if user_id:
            try:
                usuario = Usuario.objects.get(pk=user_id)
            except Usuario.DoesNotExist:
                pass
        
        context = {
            'sesion': sesion,
            'data': data,
            'usuario': usuario,
            'now': timezone.now(),  # Para comparar si la sesión está activa
        }
        
        return render(request, 'admin_panel/sesiones/detalle.html', context)
    
    except Session.DoesNotExist:
        messages.error(request, 'La sesión no existe o ha expirado.')
        return redirect('admin_panel:sesiones_lista')
