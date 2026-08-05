from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
import jwt

from .jwt import decode_token
from .models import Usuario


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
