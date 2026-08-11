import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.contrib.sites.shortcuts import get_current_site
from django.urls import reverse
from django.db import transaction, IntegrityError
from django.contrib.sessions.models import Session

# Importaciones de la aplicación
from .models import Usuario, TokenVerificacion, TokenRecuperacion, RefreshToken
from .forms import (
    RegistroForm, LoginForm, PerfilForm,
    SolicitarRecuperacionForm, NuevaContrasenaForm
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# SERVICIO DE CORREO ELECTRONICO
# ─────────────────────────────────────────────

def enviar_correo(asunto, mensaje_texto, destinatario, link=None, mensaje_html=None):
    """Auxiliar para envío seguro de correos multiformato."""
    try:
        correo = EmailMultiAlternatives(
            subject=asunto,
            body=mensaje_texto,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[destinatario],
        )

        if mensaje_html:
            correo.attach_alternative(mensaje_html, "text/html")

        correo.send(fail_silently=False)
        return True

    except Exception as e:
        logger.error(f"❌ ERROR ENVIANDO CORREO A {destinatario}: {e}")
        return False


# ─────────────────────────────────────────────
# REGISTRO Y VERIFICACIÓN DE CUENTA
# ─────────────────────────────────────────────

def registro(request):
    if request.user.is_authenticated:
        return redirect('productos:lista')

    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    user = form.save(commit=False)
                    user.is_active = True
                    if hasattr(user, 'correo_verificado'):
                        user.correo_verificado = True
                    if hasattr(user, 'is_new_user'):
                        user.is_new_user = True
                    user.save()

                logger.info(f"✅ Usuario {user.username} registrado con éxito.")
                messages.success(
                    request,
                    '🎉 ¡Registro exitoso! Ya puedes iniciar sesión con tu cuenta.'
                )
                return redirect('usuarios:login')

            except IntegrityError as e:
                logger.error(f"❌ Error de integridad al registrar: {e}")
                messages.error(request, '❌ El nombre de usuario o correo electrónico ya se encuentra registrado.')
            except Exception as e:
                logger.error(f"❌ Error al registrar usuario: {e}", exc_info=True)
                messages.error(request, '❌ Ocurrió un error en el servidor. Inténtalo de nuevo.')
        else:
            logger.warning(f"⚠️ Errores de validación en formulario: {form.errors}")
            messages.error(request, '❌ Por favor, corrige los errores señalados en el formulario.')
    else:
        form = RegistroForm()

    return render(request, 'usuarios/registro.html', {'form': form})


def verificar_email(request, token):
    """Verifica el correo mediante un token o redirige si la verificación previa ya ocurrió."""
    try:
        token_obj = TokenVerificacion.objects.get(token=token, usado=False)
        user = token_obj.usuario
        user.correo_verificado = True
        user.save()
        token_obj.usado = True
        token_obj.save()
        messages.success(request, "🎉 Tu correo ha sido verificado correctamente.")
    except TokenVerificacion.DoesNotExist:
        messages.info(request, "ℹ️ El enlace de verificación ya fue utilizado o no es válido.")
    except Exception as e:
        logger.error(f"❌ Error al verificar email: {e}")
        messages.error(request, "❌ Ocurrió un error al procesar la verificación.")

    return redirect('usuarios:login')


# ─────────────────────────────────────────────
# LOGIN / LOGOUT
# ─────────────────────────────────────────────

@never_cache
def iniciar_sesion(request):
    if request.user.is_authenticated:
        logger.info(f"Usuario {request.user.username} ya autenticado, redirigiendo")
        return redirect('productos:lista')

    if request.method == 'POST':
        list(messages.get_messages(request))
        
        username = request.POST.get('username')
        logger.info(f"🔑 Intento de login - Usuario: {username}")
        
        form = LoginForm(request, data=request.POST)
        
        if form.is_valid():
            user = form.get_user()
            
            if user is not None:
                if not user.is_active:
                    logger.warning(f"⚠️ Intento de login con cuenta desactivada: {username}")
                    messages.error(
                        request,
                        '❌ Tu cuenta ha sido desactivada. Contacta al administrador si consideras que es un error.'
                    )
                    return render(request, 'usuarios/login.html', {'form': form})   
                
                login(request, user)
                messages.success(request, f'¡Bienvenido de nuevo, {user.nombre}!')
                logger.info(f"✅ Login exitoso para {user.username}")
                
                if user.is_staff:
                    return redirect('admin_panel:dashboard')
                return redirect('productos:lista')
            else:
                messages.error(request, '❌ Error al obtener la sesión de usuario.')
        else:
            logger.error(f"❌ Error de validación en login para {username}: {form.errors}")
            
            error_ocurred = False
            for field, errors in form.errors.items():
                for error in errors:
                    error_str = str(error).lower()
                    if any(term in error_str for term in ['inactiva', 'desactivada', 'active']):
                        messages.error(request, '❌ Tu cuenta ha sido desactivada.')
                        error_ocurred = True
                        break
                    elif any(term in error_str for term in ['verificad', 'correo', 'email']):
                        messages.error(request, '❌ Debes verificar tu correo electrónico antes de ingresar.')
                        error_ocurred = True
                        break
                    elif any(term in error_str for term in ['incorrecta', 'inválida', 'invalid']):
                        messages.error(request, '❌ Usuario o contraseña incorrectos.')
                        error_ocurred = True
                        break
                if error_ocurred:
                    break
            
            if not error_ocurred:
                messages.error(request, '❌ Datos de acceso incorrectos. Por favor, inténtalo nuevamente.')
    else:
        form = LoginForm()

    return render(request, 'usuarios/login.html', {'form': form})


@login_required
@never_cache
def cerrar_sesion(request):
    """Cierra la sesión activa del usuario y revoca sus tokens de actualización."""
    nombre = request.user.nombre
    username = request.user.username
    
    RefreshToken.objects.filter(usuario=request.user, revocado_en__isnull=True).update(
        revocado_en=timezone.now()
    )
    
    logout(request)
    
    logger.info(f"✅ Sesión cerrada correctamente para {username}")
    messages.info(request, f'Hasta pronto, {nombre}. ¡Te esperamos de nuevo!')
    
    response = redirect('productos:lista')
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate, private'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    
    return response


# ─────────────────────────────────────────────
# PERFIL & ONBOARDING
# ─────────────────────────────────────────────

@login_required
def perfil(request):
    if request.method == 'POST':
        form = PerfilForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, '✅ Perfil actualizado correctamente.')
            return redirect('usuarios:perfil')
        else:
            messages.error(request, '❌ Revisa los campos marcados para corregir los errores.')
    else:
        form = PerfilForm(instance=request.user)

    return render(request, 'usuarios/perfil.html', {
        'form': form,
        'usuario': request.user,
    })


@login_required
def completar_onboarding(request):
    if request.method != 'POST':
        return JsonResponse({'detail': 'Método no permitido'}, status=405)
    
    request.user.onboarding_completado = True
    request.user.is_new_user = False
    request.user.save(update_fields=['onboarding_completado', 'is_new_user'])
    return JsonResponse({'onboarding_completado': True})


# ─────────────────────────────────────────────
# RECUPERACIÓN DE CONTRASEÑA
# ─────────────────────────────────────────────

def solicitar_recuperacion(request):
    if request.method == 'POST':
        form = SolicitarRecuperacionForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            try:
                user = Usuario.objects.get(correo=email)

                TokenRecuperacion.objects.filter(usuario=user).delete()
                token_obj = TokenRecuperacion.objects.create(usuario=user)

                link = request.build_absolute_uri(
                    reverse('usuarios:restablecer_contrasena', args=[token_obj.token])
                )

                asunto = 'Recupera tu contraseña en Agrivale 🔑'
                mensaje_texto = (
                    f'Hola {user.nombre},\n\n'
                    f'Recibimos una solicitud para restablecer tu contraseña.\n'
                    f'Haz clic en el siguiente enlace (válido por 30 minutos):\n\n'
                    f'{link}\n\n'
                    f'Si no solicitaste esto, ignora este mensaje.'
                )
                mensaje_html = f"""
                    <div style="font-family: Arial, sans-serif; padding: 20px; color: #333;">
                        <h2>Restablecimiento de contraseña 🔑</h2>
                        <p>Hola <strong>{user.nombre}</strong>,</p>
                        <p>Recibimos una solicitud para restablecer la contraseña de tu cuenta en Agrivale.</p>
                        <p style="margin: 25px 0;">
                            <a href="{link}" style="background-color: #0288d1; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; font-weight: bold;">
                                Restablecer contraseña
                            </a>
                        </p>
                        <p>O copia y pega el siguiente enlace en tu navegador:</p>
                        <p><a href="{link}">{link}</a></p>
                        <hr style="margin-top: 30px; border: none; border-top: 1px solid #ccc;">
                        <p style="font-size: 12px; color: #777;">Si no solicitaste este cambio, puedes ignorar este mensaje.</p>
                    </div>
                """

                enviar_correo(
                    asunto=asunto,
                    mensaje_texto=mensaje_texto,
                    destinatario=user.correo,
                    mensaje_html=mensaje_html
                )

            except Usuario.DoesNotExist:
                pass

            messages.info(request, 'Se ha enviado un correo con instrucciones a tu email en caso de estar registrado. Revisa tu bandeja de entrada.')
            return redirect('usuarios:login')
    else:
        form = SolicitarRecuperacionForm()

    return render(request, 'usuarios/solicitar_recuperacion.html', {'form': form})


def restablecer_contrasena(request, token):
    try:
        token_obj = TokenRecuperacion.objects.get(token=token, usado=False)
    except TokenRecuperacion.DoesNotExist:
        messages.error(
            request,
            'ℹ️ Este enlace de recuperación ya fue utilizado o no es válido.'
        )
        return redirect('usuarios:solicitar_recuperacion')

    if token_obj.ha_expirado():
        token_obj.delete()
        messages.error(
            request,
            '❌ El enlace ha expirado (límite 30 minutos). Por favor genera uno nuevo.'
        )
        return redirect('usuarios:solicitar_recuperacion')

    if request.method == 'POST':
        form = NuevaContrasenaForm(request.POST)
        if form.is_valid():
            nueva = form.cleaned_data['password1']
            user = token_obj.usuario
            user.set_password(nueva)
            user.save()

            token_obj.usado = True
            token_obj.save()

            messages.success(request, '✅ Contraseña actualizada correctamente. Puedes iniciar sesión.')
            return redirect('usuarios:login')
    else:
        form = NuevaContrasenaForm()

    return render(request, 'usuarios/restablecer_contrasena.html', {
        'form': form,
        'token': token,
    })


# ─────────────────────────────────────────────
# GESTIÓN DE SESIONES MULTIDISPOSITIVO
# ─────────────────────────────────────────────

@login_required
def cerrar_sesiones_otros_dispositivos(request):
    """Muestra y cierra sesiones activas del usuario en otros dispositivos."""
    sesiones_usuario = []
    sesion_actual = request.session.session_key
    
    todas_sesiones = Session.objects.filter(expire_date__gte=timezone.now())
    
    for sesion in todas_sesiones:
        try:
            data = sesion.get_decoded()
            user_id = data.get('_auth_user_id')
            
            if user_id == str(request.user.pk):
                es_sesion_actual = (sesion.session_key == sesion_actual)
                sesiones_usuario.append({
                    'sesion': sesion,
                    'ip': data.get('login_ip', 'N/A'),
                    'user_agent': data.get('login_user_agent', 'N/A'),
                    'login_time': data.get('login_time', 'N/A'),
                    'es_actual': es_sesion_actual,
                })
        except Exception as e:
            logger.error(f"❌ Error al decodificar sesión: {e}")
    
    if request.method == 'POST':
        sesiones_cerradas = 0
        for sesion_info in sesiones_usuario:
            if not sesion_info['es_actual']:
                try:
                    sesion_info['sesion'].delete()
                    sesiones_cerradas += 1
                except Exception as e:
                    logger.error(f"❌ Error al eliminar la sesión: {e}")
        
        if sesiones_cerradas > 0:
            messages.success(
                request,
                f'Se cerraron {sesiones_cerradas} sesión(es) activas en otros dispositivos.'
            )
        else:
            messages.info(request, 'ℹ️ No se encontraron otras sesiones activas.')
        
        return redirect('productos:lista')
    
    context = {
        'sesiones': sesiones_usuario,
        'total_sesiones': len(sesiones_usuario),
        'otras_sesiones': len([s for s in sesiones_usuario if not s['es_actual']]),
    }
    
    return render(request, 'usuarios/cerrar_sesiones_otros_dispositivos.html', context)