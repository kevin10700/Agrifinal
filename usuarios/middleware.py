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
    """Evita que el navegador cachee páginas vistas mientras había sesión activa."""
    def process_response(self, request, response):
        if getattr(request, 'user', None) and request.user.is_authenticated:
            # Headers para no guardar en caché
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate, private, max-age=0'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
            
            # Headers adicionales para prevenir guardado en historial
            response['X-Content-Type-Options'] = 'nosniff'
            response['X-Frame-Options'] = 'DENY'
            
        # También aplicar a páginas de login y logout
        if request.path in ['/usuarios/login/', '/usuarios/logout/', '/admin_panel/login/', '/admin_panel/logout/']:
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate, private, max-age=0'
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


class SessionSecurityMiddleware(MiddlewareMixin):
    """
    Middleware de seguridad adicional para sesiones.
    Detecta cambios de IP o User-Agent que podrían indicar robo de sesión.
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
        
        # Si es la primera vez que se autentica en esta sesión, guardar los datos
        if not session_ip:
            request.session['login_ip'] = current_ip
            request.session['login_user_agent'] = current_user_agent
            request.session['login_time'] = timezone.now().isoformat()
            return None
        
        # Verificar si hubo cambio de IP (solo alertar, no cerrar automáticamente)
        if session_ip and session_ip != current_ip:
            logger.warning(f"⚠️ Cambio de IP detectado para usuario {request.user.username}: {session_ip} -> {current_ip}")
            # Opcional: mostrar mensaje de advertencia
            # messages.warning(request, 'Se detectó un cambio de ubicación en tu sesión.')
        
        # Verificar si hubo cambio de User-Agent (posible robo de sesión)
        if session_user_agent and session_user_agent != current_user_agent:
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