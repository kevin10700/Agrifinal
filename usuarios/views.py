import logging
import os
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import send_mail, EmailMultiAlternatives
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
# HELPER DE ENVÍO DE CORREO (RESEND API / SMTP)
# ─────────────────────────────────────────────

from django.core.mail import EmailMultiAlternatives

def enviar_correo(asunto, mensaje_texto, destinatario, link=None, mensaje_html=None):
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
# REGISTRO Y VERIFICACIÓN
# ─────────────────────────────────────────────

def registro(request):
    if request.user.is_authenticated:
        return redirect('productos:lista')

    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            # Activamos y verificamos la cuenta de inmediato
            user.is_active = True
            user.correo_verificado = True
            user.is_new_user = True
            user.save()

            messages.success(
                request,
                f'🎉 ¡Registro exitoso! Bienvenido a Agrivale, {user.nombre}. Ya puedes iniciar sesión.'
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
        form = LoginForm(request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'¡Bienvenido de nuevo, {user.nombre}!')
            if user.is_staff:
                return redirect('admin_panel:dashboard')
            return redirect('productos:lista')
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
                    destinatario=user.email,
                    mensaje_html=mensaje_html
                )

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