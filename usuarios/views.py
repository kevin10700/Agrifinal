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
from django.urls import reverse
from django.db import transaction
from django.contrib.sessions.models import Session

from .models import Usuario, TokenRecuperacion, RefreshToken
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
                    # 1. UserCreationForm.save() ya hashea la contraseña correctamente
                    user = form.save(commit=False)
                    
                    # 2. Asignar los valores predeterminados requeridos por tu modelo
                    user.is_active = True
                    
                    # Verificamos si los campos personalizados existen en tu modelo Usuario antes de asignarlos
                    if hasattr(user, 'correo_verificado'):
                        user.correo_verificado = True
                    if hasattr(user, 'is_new_user'):
                        user.is_new_user = True
                    
                    # 3. Guardar en la Base de Datos
                    user.save()

                logger.info(f"✅ Usuario {user.username} registrado con éxito.")
                messages.success(request, '🎉 ¡Registro exitoso! Ya puedes iniciar sesión con tu cuenta.')
                return redirect('usuarios:login')

            except IntegrityError as e:
                logger.error(f"❌ Error de integridad en BD al registrar usuario: {e}")
                messages.error(request, '❌ El nombre de usuario o correo electrónico ya está registrado en el sistema.')
            except Exception as e:
                logger.error(f"❌ Error inesperado durante el registro: {e}", exc_info=True)
                messages.error(request, '❌ Ocurrió un error en el servidor al procesar tu registro. Inténtalo de nuevo.')
        else:
            logger.warning(f"⚠️ Errores de validación en RegistroForm: {form.errors}")
            # No forzamos un mensaje genérico para no duplicar alertas; 
            # las plantillas mostrarán los errores directamente en los inputs.
            messages.error(request, '❌ Por favor, corrige los errores señalados en el formulario.')
    else:
        form = RegistroForm()

    return render(request, 'usuarios/registro.html', {'form': form})


# ─────────────────────────────────────────────
# LOGIN / LOGOUT
# ─────────────────────────────────────────────

@never_cache
def iniciar_sesion(request):
    if request.user.is_authenticated:
        return redirect('productos:lista')

    if request.method == 'POST':
        # Limpiar mensajes acumulados
        storage = messages.get_messages(request)
        for _ in storage:
            pass
        
        username = request.POST.get('username')
        form = LoginForm(request, data=request.POST)
        
        if form.is_valid():
            user = form.get_user()
            
            if user is not None:
                if not user.is_active:
                    logger.warning(f"⚠️ Intento de login con cuenta desactivada: {username}")
                    messages.error(request, '❌ Tu cuenta ha sido desactivada. Contacta al administrador.')
                else:
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
    nombre = request.user.nombre
    
    # Revocar JWT solo si manejas autenticación híbrida (Web + API)
    RefreshToken.objects.filter(usuario=request.user, revocado_en__isnull=True).update(
        revocado_en=timezone.now()
    )
    
    logout(request)
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

                with transaction.atomic():
                    TokenRecuperacion.objects.filter(usuario=user).delete()
                    token_obj = TokenRecuperacion.objects.create(usuario=user)

                link = request.build_absolute_uri(
                    reverse('usuarios:restablecer_contrasena', args=[token_obj.token])
                )

                asunto = 'Recupera tu contraseña en Agrivale 🔑'
                mensaje_texto = (
                    f'Hola {user.nombre},\n\n'
                    f'Haz clic en el enlace para restablecer tu contraseña (válido por 30 min):\n{link}'
                )
                mensaje_html = f"""
                    <div style="font-family: Arial, sans-serif; padding: 20px; color: #333;">
                        <h2>Restablecimiento de contraseña 🔑</h2>
                        <p>Hola <strong>{user.nombre}</strong>,</p>
                        <p><a href="{link}" style="background-color: #0288d1; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px;">Restablecer contraseña</a></p>
                    </div>
                """

                enviar_correo(asunto, mensaje_texto, user.correo, mensaje_html=mensaje_html)

            except Usuario.DoesNotExist:
                pass  # Evita enumeración de usuarios

            messages.info(request, 'Se ha enviado un correo con instrucciones a tu email en caso de estar registrado.')
            return redirect('usuarios:login')
    else:
        form = SolicitarRecuperacionForm()

    return render(request, 'usuarios/solicitar_recuperacion.html', {'form': form})


def restablecer_contrasena(request, token):
    token_obj = TokenRecuperacion.objects.filter(token=token, usado=False).first()
    
    if not token_obj:
        messages.error(request, 'ℹ️ Este enlace de recuperación ya fue utilizado o no es válido.')
        return redirect('usuarios:solicitar_recuperacion')

    if token_obj.ha_expirado():
        token_obj.delete()
        messages.error(request, '❌ El enlace ha expirado. Por favor genera uno nuevo.')
        return redirect('usuarios:solicitar_recuperacion')

    if request.method == 'POST':
        form = NuevaContrasenaForm(request.POST)
        if form.is_valid():
            nueva = form.cleaned_data['password1']
            
            with transaction.atomic():
                user = token_obj.usuario
                user.set_password(nueva)
                user.save()

                token_obj.usado = True
                token_obj.save()

            messages.success(request, '✅ Contraseña actualizada correctamente. Puedes iniciar sesión.')
            return redirect('usuarios:login')
    else:
        form = NuevaContrasenaForm()

    return render(request, 'usuarios/restablecer_contrasena.html', {'form': form, 'token': token})