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
from django.views.decorators.cache import never_cache

@never_cache
def iniciar_sesion(request):
    ...  # sin cambios en el cuerpo

@login_required
@never_cache
def cerrar_sesion(request):
    ...  # sin cambios en el cuerpo


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
# LOGIN / LOGOUT - VERSIÓN CORREGIDA
# ─────────────────────────────────────────────

def iniciar_sesion(request):
    if request.user.is_authenticated:
        logger.info(f"Usuario {request.user.username} ya autenticado, redirigiendo")
        return redirect('productos:lista')

    if request.method == 'POST':
        # Limpiar mensajes antiguos para evitar confusión
        list(messages.get_messages(request))
        
        # Log del intento de login
        username = request.POST.get('username')
        logger.info(f"📝 Intento de login - Usuario: {username}")
        logger.info(f"📝 Datos POST recibidos: {request.POST}")
        
        # ¡IMPORTANTE! Pasa 'request' como primer argumento
        form = LoginForm(request, data=request.POST)
        
        # Log para verificar si el formulario tiene errores antes de is_valid
        logger.info(f"📝 Formulario creado, datos: {form.data}")
        
        if form.is_valid():
            user = form.get_user()
            logger.info(f"✅ Formulario válido, usuario obtenido: {user}")
            
            if user is not None:
                # Verificar si la cuenta está activa
                if not user.is_active:
                    logger.warning(f"⚠️ Intento de login con cuenta desactivada: {username}")
                    messages.error(
                        request,
                        '❌ Tu cuenta ha sido desactivada. '
                        'Si crees que esto es un error, contacta al administrador.'
                    )
                    return render(request, 'usuarios/login.html', {'form': form})
                
                # Verificar si el correo está verificado
                if not user.correo_verificado:
                    logger.warning(f"⚠️ Intento de login con correo no verificado: {username}")
                    messages.error(
                        request,
                        '❌ Debes verificar tu correo electrónico antes de iniciar sesión. '
                        'Revisa tu bandeja de entrada y spam.'
                    )
                    return render(request, 'usuarios/login.html', {'form': form})
                
                # Login exitoso
                login(request, user)
                messages.success(request, f'¡Bienvenido de nuevo, {user.nombre}!')
                logger.info(f"✅ Login exitoso para {user.username}")
                
                # Redirigir según el rol
                if user.is_staff:
                    logger.info(f"👤 Usuario staff, redirigiendo a admin_panel:dashboard")
                    return redirect('admin_panel:dashboard')
                logger.info(f"👤 Usuario normal, redirigiendo a productos:lista")
                return redirect('productos:lista')
            else:
                logger.error("❌ form.get_user() retornó None a pesar de que form.is_valid() es True")
                messages.error(request, '❌ Error al obtener el usuario autenticado.')
        else:
            # Log detallado de errores
            logger.error(f"❌ Formulario inválido")
            logger.error(f"   - Errores completos: {form.errors}")
            logger.error(f"   - Errores no field: {form.non_field_errors()}")
            logger.error(f"   - Campos con errores: {list(form.errors.keys())}")
            
            # Determinar el tipo de error y mostrar mensaje apropiado
            error_ocurred = False
            
            # Verificar errores de campo
            for field, errors in form.errors.items():
                for error in errors:
                    error_str = str(error).lower()
                    
                    # Detectar error de cuenta inactiva
                    if 'inactiva' in error_str or 'desactivada' in error_str or 'active' in error_str:
                        messages.error(
                            request,
                            '❌ Tu cuenta ha sido desactivada. '
                            'Si crees que esto es un error, contacta al administrador.'
                        )
                        error_ocurred = True
                        break
                    
                    # Detectar error de correo no verificado
                    elif 'verificad' in error_str or 'correo' in error_str or 'email' in error_str:
                        messages.error(
                            request,
                            '❌ Debes verificar tu correo electrónico antes de iniciar sesión. '
                            'Revisa tu bandeja de entrada y carpeta de spam.'
                        )
                        error_ocurred = True
                        break
                    
                    # Detectar error de credenciales incorrectas
                    elif 'incorrecta' in error_str or 'inválida' in error_str or 'invalid' in error_str:
                        messages.error(
                            request,
                            '❌ Usuario o contraseña incorrectos. Por favor, verifica tus datos.'
                        )
                        error_ocurred = True
                        break
                    
                    # Otro tipo de error
                    else:
                        messages.error(request, f'❌ {error}')
                        error_ocurred = True
                
                if error_ocurred:
                    break
            
            # Si no se identificó un error específico, mostrar mensaje genérico
            if not error_ocurred:
                messages.error(
                    request,
                    '❌ No se pudo iniciar sesión. Por favor, verifica que tu usuario y contraseña sean correctos.'
                )
            
            # Verificar si el usuario existe en la BD (para diagnóstico)
            try:
                user_obj = Usuario.objects.get(username=username)
                logger.info(f"🔍 Usuario {username} existe en BD:")
                logger.info(f"   - Username: {user_obj.username}")
                logger.info(f"   - is_active: {user_obj.is_active}")
                logger.info(f"   - correo_verificado: {user_obj.correo_verificado}")
                logger.info(f"   - is_staff: {user_obj.is_staff}")
                logger.info(f"   - Password hash: {user_obj.password[:30]}...")
                
                # Verificar contraseña manualmente
                password = request.POST.get('password')
                if password:
                    password_correct = user_obj.check_password(password)
                    logger.info(f"   - Contraseña correcta (check_password): {password_correct}")
                    if not password_correct:
                        logger.warning(f"⚠️ La contraseña ingresada NO coincide con la guardada")
                else:
                    logger.warning(f"⚠️ No se recibió contraseña en el POST")
                    
            except Usuario.DoesNotExist:
                logger.error(f"❌ Usuario {username} NO existe en BD")
                messages.error(
                    request,
                    '❌ El usuario no existe en el sistema. Por favor, verifica el nombre de usuario.'
                )
    else:
        form = LoginForm()
        logger.info("📄 Mostrando formulario de login (GET)")

    return render(request, 'usuarios/login.html', {'form': form})


@login_required
def cerrar_sesion(request):
    """Cierra la sesión del usuario y revoca todos los tokens de refresco."""
    nombre = request.user.nombre
    username = request.user.username
    
    # Revocar todos los refresh tokens activos
    RefreshToken.objects.filter(usuario=request.user, revocado_en__isnull=True).update(
        revocado_en=timezone.now()
    )
    
    # Cerrar sesión de Django
    logout(request)
    
    logger.info(f"✅ Sesión cerrada para usuario {username}")
    messages.info(request, f'Hasta pronto, {nombre}. ¡Vuelve pronto!')
    
    # Redirigir con headers anti-caché (sin Clear-Site-Data para no romper CSRF)
    response = redirect('productos:lista')
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate, private'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    # NOTA: No usamos Clear-Site-Data porque elimina cookies CSRF
    # response['Clear-Site-Data'] = '"cache", "cookies", "storage"'
    
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


def cerrar_sesiones_otros_dispositivos(request):
    """
    Muestra ventana para cerrar sesiones en otros dispositivos.
    Se muestra cuando se detecta una sesión restaurada (navegador cerrado y reabierto).
    """
    from django.contrib.sessions.models import Session
    
    if not request.user.is_authenticated:
        return redirect('usuarios:login')
    
    # Obtener todas las sesiones activas del usuario
    sesiones_usuario = []
    sesion_actual = request.session.session_key
    
    todas_sesiones = Session.objects.filter(expire_date__gte=timezone.now())
    
    for sesion in todas_sesiones:
        try:
            data = sesion.get_decoded()
            user_id = data.get('_auth_user_id')
            
            if user_id == str(request.user.pk):
                # Es una sesión del usuario actual
                es_sesion_actual = sesion.session_key == sesion_actual
                sesiones_usuario.append({
                    'sesion': sesion,
                    'ip': data.get('login_ip', 'N/A'),
                    'user_agent': data.get('login_user_agent', 'N/A'),
                    'login_time': data.get('login_time', 'N/A'),
                    'es_actual': es_sesion_actual,
                })
        except Exception as e:
            logger.error(f"❌ Error al procesar sesión: {e}")
    
    # Cerrar todas las sesiones excepto la actual
    sesiones_cerradas = 0
    if request.method == 'POST':
        for sesion_info in sesiones_usuario:
            if not sesion_info['es_actual']:
                try:
                    sesion = sesion_info['sesion']
                    sesion.delete()
                    sesiones_cerradas += 1
                except Exception as e:
                    logger.error(f"❌ Error al cerrar sesión: {e}")
        
        if sesiones_cerradas > 0:
            messages.success(
                request,
                f'✅ Se cerraron {sesiones_cerradas} sesión(es) en otros dispositivos. '
                f'Ahora puedes continuar de forma segura.'
            )
        else:
            messages.info(request, 'ℹ️ No había otras sesiones activas.')
        
        return redirect('productos:lista')
    
    context = {
        'sesiones': sesiones_usuario,
        'total_sesiones': len(sesiones_usuario),
        'otras_sesiones': len([s for s in sesiones_usuario if not s['es_actual']]),
    }
    
    return render(request, 'usuarios/cerrar_sesiones_otros_dispositivos.html', context)
