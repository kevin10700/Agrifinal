from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.generic import ListView
from django.db.models import Q, F
from django.core.paginator import Paginator
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Producto, Categoria, ProductoAgricola, Favorito
from .forms import ComentarioForm
from .models import Producto
from pedidos.models import CarritoItem

class ProductoListView(ListView):
    model = Producto
    template_name = 'productos/lista.html'
    context_object_name = 'productos'
    paginate_by = 12

    def get_queryset(self):
        queryset = Producto.objects.all()
        q = self.request.GET.get('q')
        if q:
            queryset = queryset.filter(
                Q(nombre__icontains=q) |
                Q(descripcion_corta__icontains=q) |
                Q(descripcion_larga__icontains=q)
            )
        categoria = self.request.GET.get('categoria')
        if categoria:
            queryset = queryset.filter(id_categoria__slug=categoria)  # ← corregido
        orden = self.request.GET.get('orden')
        if orden == 'precio_asc':
            queryset = queryset.order_by('precio')
        elif orden == 'precio_desc':
            queryset = queryset.order_by('-precio')
        elif orden == 'nuevos':
            queryset = queryset.order_by('-fecha_creacion')
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # 🔴 CORREGIDO: 'filters' no existe, es 'filter'
        context['categorias'] = Categoria.objects.filter(activo=True)
        context['categoria_activa'] = self.request.GET.get('categoria')
        return context


class OfertasListView(ListView):
    model = Producto
    template_name = 'productos/ofertas.html'
    context_object_name = 'productos'
    paginate_by = 12

    def get_queryset(self):
        queryset = Producto.objects.filter(
            precio_oferta__isnull=False
        ).exclude(
            precio_oferta__gte=F('precio')
        ).order_by('-precio_oferta')
        q = self.request.GET.get('q')
        if q:
            queryset = queryset.filter(
                Q(nombre__icontains=q) |
                Q(descripcion_corta__icontains=q)
            )
        categoria = self.request.GET.get('categoria')
        if categoria:
            queryset = queryset.filter(id_categoria__slug=categoria)  # ← corregido
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categorias'] = Categoria.objects.filter(activo=True)
        context['categoria_activa'] = self.request.GET.get('categoria')
        context['titulo'] = 'Ofertas Especiales'
        context['subtitulo'] = 'Productos agrícolas con descuentos imperdibles'
        return context


def detalle_producto(request, slug):
    producto = get_object_or_404(Producto, slug=slug)
    producto.vistas += 1
    producto.save()

    comentarios_aprobados = producto.comentarios.filter(aprobado=True)
    total_comentarios = comentarios_aprobados.count()

    distribucion = {}
    porcentajes = {}
    for i in range(1, 6):
        count = comentarios_aprobados.filter(calificacion=i).count()
        distribucion[i] = count
        porcentajes[i] = round((count / total_comentarios) * 100) if total_comentarios > 0 else 0

    if total_comentarios > 0:
        suma = sum(c.calificacion for c in comentarios_aprobados)
        promedio = round(suma / total_comentarios, 1)
    else:
        promedio = 0

    filtro_estrellas = request.GET.get('estrellas')
    if filtro_estrellas and filtro_estrellas.isdigit():
        comentarios = comentarios_aprobados.filter(calificacion=int(filtro_estrellas))
    else:
        comentarios = comentarios_aprobados

    orden = request.GET.get('orden', 'recientes')
    if orden == 'mejores':
        comentarios = comentarios.order_by('-calificacion')
    elif orden == 'peores':
        comentarios = comentarios.order_by('calificacion')
    else:
        comentarios = comentarios.order_by('-fecha_creacion')

    paginator = Paginator(comentarios, 5)
    comentarios_paginados = paginator.get_page(request.GET.get('page'))

    # 🔴 CORREGIDO: Quitado el 'producto.' extra del lado izquierdo del filter
    relacionados = Producto.objects.filter(
        id_categoria=producto.id_categoria
    ).exclude(id_producto=producto.id_producto)[:4]

    context = {
        'producto': producto,
        'comentarios': comentarios_paginados,
        'distribucion': distribucion,
        'porcentajes': porcentajes,
        'promedio': promedio,
        'total_comentarios': total_comentarios,
        'relacionados': relacionados,
        'form': ComentarioForm(),
        'filtro_estrellas': filtro_estrellas,
        'orden': orden,
    }
    return render(request, 'productos/detalle.html', context)


@login_required
def agregar_comentario(request, producto_id):
    producto = get_object_or_404(Producto, id_producto=producto_id)  # ← corregido

    if request.method == 'POST':
        form = ComentarioForm(request.POST, request.FILES)
        if form.is_valid():
            comentario = form.save(commit=False)
            comentario.id_producto = producto      # ← corregido
            comentario.id_usuario = request.user   # ← corregido

            from pedidos.models import Pedido
            compro = Pedido.objects.filter(
                id_usuario=request.user,           # ← corregido
                items__id_producto=producto,       # ← corregido
                estado='entregado'
            ).exists()
            comentario.compra_verificada = compro
            comentario.save()

            messages.success(request, '¡Gracias por tu comentario! Sera revisado por el administrador.')
            return redirect('productos:detalle', slug=producto.slug)
    else:
        form = ComentarioForm()

    return render(request, 'productos/agregar_comentario.html', {
        'form': form,
        'producto': producto
    })

@login_required
def comprar_ahora(request, producto_id):
    """Agrega un único producto al carrito (limpiando lo anterior) y lleva directo al checkout"""
    producto = get_object_or_404(Producto, id_producto=producto_id)
    
    # Limpiamos el carrito actual del usuario para esta compra rápida
    CarritoItem.objects.filter(id_usuario=request.user).delete()
    
    # Creamos el item único con cantidad 1
    CarritoItem.objects.create(
        id_usuario=request.user,
        id_producto=producto,
        cantidad=1
    )
    
    # Redirigimos directo a la pantalla de confirmar pedido en la app de pedidos
    return redirect('pedidos:confirmar')


def api_productos(request):
    """Catálogo público; admite ?categoria= y ?q= por nombre."""
    queryset = ProductoAgricola.objects.filter(activo=True)
    categoria = request.GET.get('categoria')
    if categoria:
        queryset = queryset.filter(categoria=categoria)
    q = request.GET.get('q', '').strip()
    if q:
        queryset = queryset.filter(nombre__icontains=q)
    return JsonResponse({'count': queryset.count(), 'results': list(queryset.values(
        'id', 'nombre', 'categoria', 'uso_principal', 'presentaciones', 'precio_base', 'stock', 'imagen_url', 'activo'
    ))})


# ===================== FAVORITOS =====================

@login_required
def toggle_favorito(request, producto_id):
    """Agrega o elimina un producto de favoritos."""
    print(f"DEBUG: toggle_favorito llamado - usuario: {request.user.username}, producto_id: {producto_id}")
    
    producto = get_object_or_404(Producto, id_producto=producto_id)
    print(f"DEBUG: producto encontrado: {producto.nombre}")
    
    favorito, creado = Favorito.objects.get_or_create(
        id_usuario=request.user,
        id_producto=producto
    )
    print(f"DEBUG: get_or_create - creado: {creado}")
    
    if not creado:
        favorito.delete()
        es_favorito = False
        mensaje = 'Eliminado de favoritos'
        print(f"DEBUG: favorito eliminado")
    else:
        es_favorito = True
        mensaje = 'Agregado a favoritos'
        print(f"DEBUG: favorito creado")
    
    return JsonResponse({
        'es_favorito': es_favorito,
        'mensaje': mensaje
    })


@login_required
def verificar_favorito(request, producto_id):
    """Verifica si un producto es favorito del usuario sin cambiar su estado."""
    producto = get_object_or_404(Producto, id_producto=producto_id)
    es_favorito = Favorito.objects.filter(
        id_usuario=request.user,
        id_producto=producto
    ).exists()
    
    return JsonResponse({
        'es_favorito': es_favorito
    })


@login_required
def lista_favoritos(request):
    """Muestra la lista de productos favoritos del usuario."""
    favoritos = Favorito.objects.filter(id_usuario=request.user).select_related('id_producto')
    productos = [f.id_producto for f in favoritos]
    
    context = {
        'productos': productos,
        'titulo': 'Mis Favoritos',
        'subtitulo': 'Productos que guardaste para ver más tarde'
    }
    return render(request, 'productos/lista.html', context)