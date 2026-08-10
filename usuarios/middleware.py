from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth import logout
from django.contrib import messages
from django.shortcuts import redirect
from django.utils import timezone
import jwt
import logging

from .jwt import decode_token
from .models import Usuario

logger = logging.getLogger(__name__)


class JWTApiAuthenticationMiddleware(MiddlewareMixin):
    """Protege /api/* salvo los endpoints explícitamente públicos."""
    PUBLIC_API_PATHS = {"/api/auth/login/", "/api/auth/refresh/", "/api/auth/logout/", "/api/productos/"}

    def process_request(self, request):
        if not request.path.startswith("/api/") or request.path in self.PUBLIC_API_PATHS:
            return None
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return JsonResponse({"detail": "Sesión expirada, inicia sesión de nuevo", "code": "token_missing"}, status=401)
        try:
            payload = decode_token(header[7:], "access")
            request.api_user = Usuario.objects.get(pk=payload["sub"], is_active=True)
        except (jwt.PyJWTError, Usuario.DoesNotExist):
            return JsonResponse({"detail": "Sesión expirada, inicia sesión de nuevo", "code": "token_invalid"}, status=401)
        return None


class NoCacheAuthenticatedMiddleware(MiddlewareMixin):
    """Evita que el navegador guarde en caché y en el historial las páginas con sesión activa."""
    def process_response(self, request, response):
        # Aplicar a TODAS las páginas (no solo autenticadas)
        # Headers agresivos para prevenir caché y guardado en historial
        response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0, private'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        
        # Headers adicionales de seguridad
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        
        # NOTA: No usamos Clear-Site-Data porque elimina las cookies CSRF y rompe el login
        # Clear-Site-Data: '"cache", "cookies", "storage"'  # COMENTADO - causa error 403
        
        # Prevenir que el navegador guarde la página en el historial
        response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        
        return response


class SessionValidationMiddleware(MiddlewareMixin):
    """
    Middleware que valida el estado de la sesión y detecta cierres incorrectos.
    Se ejecuta en cada request para verificar que la sesión sea válida.
    """
    
    # Rutas que no requieren validación de sesión
    PUBLIC_PATHS = {
        '/usuarios/login/',
        '/usuarios/logout/',
        '/usuarios/registro/',
        '/usuarios/verificar-email/',
        '/usuarios/solicitar-recuperacion/',
        '/usuarios/restablecer-contrasena/',
        '/admin_panel/login/',
        '/admin_panel/logout/',
    }
    
    def process_request(self, request):
        # Solo procesar si el usuario está autenticado
        if not getattr(request, 'user', None) or not request.user.is_authenticated:
            return None
        
        # Saltar rutas públicas
        if request.path in self.PUBLIC_PATHS:
            return None
        
        # Verificar si el usuario sigue activo en la base de datos
        try:
            user = Usuario.objects.get(pk=request.user.pk)
            
            # Si el usuario fue desactivado, cerrar sesión
            if not user.is_active:
                logger.warning(f"⚠️ Usuario {user.username} fue desactivado, cerrando sesión")
                logout(request)
                messages.error(
                    request,
                    '❌ Tu cuenta ha sido desactivada. Si tienes dudas, contacta al administrador.'
                )
                return redirect('usuarios:login')
            
            # Verificar si la sesión en la BD coincide (para sesiones de Django)
            if hasattr(request, 'session'):
                session_key = request.session.session_key
                if session_key:
                    # La sesión existe y es válida
                    pass
            
        except Usuario.DoesNotExist:
            logger.error(f"❌ Usuario {request.user.username} no existe en BD, cerrando sesión")
            logout(request)
            messages.error(
                request,
                '❌ Tu sesión ha sido cerrada incorrectamente. Por favor, inicia sesión de nuevo.'
            )
            return redirect('usuarios:login')
        
        return None


class AdminAccessMiddleware(MiddlewareMixin):
    """
    Middleware que bloquea el acceso al admin de Django para usuarios no autorizados.
    Solo superusers pueden acceder a /admin/.
    Staff y usuarios normales son redirigidos al admin_panel o productos.
    """
    
    def process_request(self, request):
        # Verificar si la ruta es /admin/ o subrutas
        if request.path.startswith('/admin/'):
            # Si el usuario no está autenticado, dejar pasar (Django lo maneja)
            if not getattr(request, 'user', None) or not request.user.is_authenticated:
                return None
            
            # Si está autenticado, verificar que sea superuser
            if not request.user.is_superuser:
                logger.warning(f"⚠️ Usuario {request.user.username} intentó acceder a /admin/ sin permisos")
                
                # Bloquear acceso a /admin/ para todos los que no sean superuser
                messages.error(
                    request,
                    '❌ No tienes permisos para acceder al panel de administración de Django.'
                )
                return redirect('productos:lista')
        
        return None


class SessionSecurityMiddleware(MiddlewareMixin):
    """
    Middleware de seguridad adicional para sesiones.
    Detecta cambios de IP o User-Agent que podrían indicar robo de sesión.
    Detecta sesiones restauradas después de cerrar el navegador.
    """
    
    def process_request(self, request):
        if not getattr(request, 'user', None) or not request.user.is_authenticated:
            return None
        
        # Obtener información del request actual
        current_ip = self._get_client_ip(request)
        current_user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # Obtener información guardada en la sesión
        session_ip = request.session.get('login_ip')
        session_user_agent = request.session.get('login_user_agent')
        session_login_time = request.session.get('login_time')
        session_token = request.session.get('session_token')
        
        # Si es la primera vez que se autentica en esta sesión, guardar los datos
        if not session_ip:
            request.session['login_ip'] = current_ip
            request.session['login_user_agent'] = current_user_agent
            request.session['login_time'] = timezone.now().isoformat()
            # Generar token único para esta sesión
            import uuid
            request.session['session_token'] = str(uuid.uuid4())
            return None
        
        # DETECTAR SESIÓN RESTAURADA: Verificar si el navegador fue cerrado y reabierto
        # sessionStorage se limpia al cerrar el navegador, pero la cookie de sesión de Django permanece
        # Si no hay token en sessionStorage pero sí hay sesión de Django, significa que se restauró
        from django.conf import settings
        
        # Verificar si la sesión tiene más de 8 horas (tiempo máximo de inactividad)
        if session_login_time:
            try:
                login_time = timezone.datetime.fromisoformat(session_login_time)
                tiempo_transcurrido = timezone.now() - login_time
                horas_inactivo = tiempo_transcurrido.total_seconds() / 3600
                
                # Si han pasado más de 8 horas desde el login, cerrar sesión
                if horas_inactivo > 8:
                    logger.warning(f"⚠️ Sesión expirada por inactividad para {request.user.username}: {horas_inactivo:.1f} horas")
                    logout(request)
                    messages.error(
                        request,
                        '❌ Tu sesión ha expirado por inactividad (8 horas). Por favor, inicia sesión de nuevo.'
                    )
                    return redirect('usuarios:login')
            except (ValueError, TypeError):
                pass
        
        # Verificar si hubo cambio de User-Agent (posible robo de sesión)
        # Solo verificar si ambos User-Agents son diferentes y no vacíos
        if session_user_agent and current_user_agent:
            # Comparar solo los primeros 50 caracteres para evitar falsos positivos
            # por parámetros dinámicos del navegador
            session_ua_base = session_user_agent[:50]
            current_ua_base = current_user_agent[:50]
            
            # Solo cerrar sesión si hay un cambio REAL en el navegador/sistema operativo
            if session_ua_base != current_ua_base:
                logger.warning(f"⚠️ Cambio de User-Agent detectado para usuario {request.user.username}")
                logger.warning(f"   IP: {current_ip}")
                logger.warning(f"   User-Agent anterior: {session_user_agent[:100]}")
                logger.warning(f"   User-Agent actual: {current_user_agent[:100]}")
                
                # Cerrar sesión por seguridad
                logout(request)
                messages.error(
                    request,
                    '❌ Se detectó un cambio sospechoso en tu navegador. Por seguridad, tu sesión ha sido cerrada. '
                    'Si fuiste tú, inicia sesión de nuevo.'
                )
                return redirect('usuarios:login')
        
        return None
    
    def _get_client_ip(self, request):
        """Obtiene la IP real del cliente, considerando proxies."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
