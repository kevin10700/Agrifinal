import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.http import JsonResponse

# Importaciones unificadas
from .models import Usuario, TokenVerificacion, TokenRecuperacion, RefreshToken
from .forms import (
    RegistroForm, LoginForm, PerfilForm,
    SolicitarRecuperacionForm, NuevaContrasenaForm
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# REGISTRO Y VERIFICACIÓN
# ─────────────────────────────────────────────

def registro(request):
    if request.user.is_authenticated:
        return redirect('productos:lista')

    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False
            user.correo_verificado = False
            user.is_new_user = True
            user.save()

            # Token de verificación
            token_obj = TokenVerificacion.objects.create(id_usuario=user)

            link = request.build_absolute_uri(
                f'/usuarios/verificar-email/{token_obj.token}/'
            )

            try:
                send_mail(
                    subject='Verifica tu correo en Agrivale 🌿',
                    message=(
                        f'Hola {user.nombre},\n\n'
                        f'Gracias por registrarte en Agrivale.\n'
                        f'Haz clic en el siguiente enlace para verificar tu cuenta '
                        f'(válido por 30 minutos):\n\n{link}\n\n'
                        f'Si no creaste esta cuenta, ignora este mensaje.'
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=False,
                )
                messages.success(
                    request,
                    f'✅ ¡Registro exitoso! Te enviamos un correo a {user.email}. '
                    f'Tienes 30 minutos para verificar tu cuenta antes de que expire el enlace.'
                )
            except Exception as e:
                logger.error(f"❌ ERROR ENVIANDO CORREO DE REGISTRO: {e}")
                messages.warning(
                    request,
                    '⚠️ Tu cuenta fue creada pero no pudimos enviar el correo de verificación. '
                    'Contacta al administrador.'
                )

            return redirect('usuarios:login')
    else:
        form = RegistroForm()

    return render(request, 'usuarios/registro.html', {'form': form})


def verificar_email(request, token):
    try:
        token_obj = TokenVerificacion.objects.get(token=token)
    except TokenVerificacion.DoesNotExist:
        messages.info(
            request,
            'ℹ️ Este enlace de verificación ya fue usado o no es válido. '
            'Si ya verificaste tu correo, simplemente inicia sesión.'
        )
        return redirect('usuarios:login')

    if token_obj.ha_expirado():
        user_to_delete = token_obj.id_usuario
        token_obj.delete()
        user_to_delete.delete() 
        
        messages.error(
            request,
            '❌ El enlace de verificación ha expirado. '
            'Por favor regístrate de nuevo.'
        )
        return redirect('usuarios:registro')

    user = token_obj.id_usuario
    user.is_active = True
    user.correo_verificado = True
    user.save()
    token_obj.delete()

    messages.success(
        request,
        f'🎉 ¡Correo verificado correctamente! Bienvenido a Agrivale, {user.nombre}. '
        f'Ya puedes iniciar sesión.'
    )
    return redirect('usuarios:login')


# Alternativa de verificación que renderiza un template propio
def verificar_correo_view(request, token):
    try:
        token_db = TokenVerificacion.objects.get(token=token)
        usuario = token_db.id_usuario

        if token_db.ha_expirado():
            token_db.delete()
            usuario.delete() 
            return render(request, 'usuarios/verificar_correo.html', {'exito': False})
            
        usuario.correo_verificado = True
        usuario.is_active = True
        usuario.save()
        token_db.delete() 
        return render(request, 'usuarios/verificar_correo.html', {'exito': True})
        
    except TokenVerificacion.DoesNotExist:
        return render(request, 'usuarios/verificar_correo.html', {'exito': False})


# ─────────────────────────────────────────────
# LOGIN / LOGOUT
# ─────────────────────────────────────────────

def iniciar_sesion(request):
    if request.user.is_authenticated:
        return redirect('productos:lista')

    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                if not user.correo_verificado:
                    messages.warning(
                        request,
                        '📧 Debes verificar tu correo electrónico antes de iniciar sesión. '
                        'Revisa tu bandeja de entrada (o spam).'
                    )
                    return redirect('usuarios:login')
                login(request, user)
                messages.success(
                    request,
                    'Inicio de sesión exitoso'
                )
                if user.is_staff:
                    return redirect('admin_panel:dashboard')
                return redirect('productos:lista')
        else:
            messages.error(request, '❌ Usuario o contraseña incorrectos. Intenta de nuevo.')
    else:
        form = LoginForm()

    return render(request, 'usuarios/login.html', {'form': form})


@login_required
def cerrar_sesion(request):
    nombre = request.user.nombre
    RefreshToken.objects.filter(usuario=request.user, revocado_en__isnull=True).update(revocado_en=timezone.now())
    logout(request)
    messages.info(request, f'Hasta pronto, {nombre}. ¡Vuelve pronto!')
    return redirect('productos:lista')


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
            messages.error(request, '❌ Corrige los errores del formulario.')
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
                user = Usuario.objects.get(email=email)

                # Borrar tokens anteriores de recuperación
                TokenRecuperacion.objects.filter(id_usuario=user).delete()
                token_obj = TokenRecuperacion.objects.create(id_usuario=user)

                link = request.build_absolute_uri(
                    f'/usuarios/restablecer-contrasena/{token_obj.token}/'
                )

                try:
                    send_mail(
                        subject='Recupera tu contraseña en Agrivale 🔑',
                        message=(
                            f'Hola {user.nombre},\n\n'
                            f'Recibimos una solicitud para restablecer tu contraseña.\n'
                            f'Haz clic en el siguiente enlace (válido por 30 minutos):\n\n'
                            f'{link}\n\n'
                            f'Si no solicitaste esto, ignora este mensaje.'
                        ),
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[user.email],
                        fail_silently=False,
                    )
                except Exception as e:
                    logger.error(f"❌ ERROR ENVIANDO CORREO DE RECUPERACIÓN: {e}")

            except Usuario.DoesNotExist:
                pass  # No revelamos si el email existe por seguridad

            messages.info(request, 'Se ha enviado un correo de recuperación a tu email. Revisa tu bandeja y spam.')
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
            'ℹ️ Este enlace de recuperación ya fue usado o no es válido. '
            'Solicita uno nuevo si lo necesitas.'
        )
        return redirect('usuarios:solicitar_recuperacion')

    if token_obj.ha_expirado():
        token_obj.delete()
        messages.error(
            request,
            '❌ El enlace para restablecer la contraseña ha expirado (30 minutos). '
            'Por favor solicítalo de nuevo.'
        )
        return redirect('usuarios:solicitar_recuperacion')

    if request.method == 'POST':
        form = NuevaContrasenaForm(request.POST)
        if form.is_valid():
            nueva = form.cleaned_data['password1']
            user = token_obj.id_usuario
            user.set_password(nueva)
            user.save()

            token_obj.usado = True
            token_obj.save()

            messages.success(
                request,
                'Contraseña actualizada correctamente'
            )
            return redirect('usuarios:login')
    else:
        form = NuevaContrasenaForm()

    return render(request, 'usuarios/restablecer_contrasena.html', {
        'form': form,
        'token': token,
    })