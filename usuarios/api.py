"""Endpoints JSON de autenticación para clientes JS/SPAs."""
import json
import jwt
from django.conf import settings
from django.contrib.auth import authenticate
from django.core.cache import cache
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from .jwt import REFRESH_LIFETIME, create_access_token, create_refresh_token, decode_token
from .models import RefreshToken


def _body(request):
    try:
        return json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return {}


def _set_refresh_cookie(response, token):
    response.set_cookie(settings.JWT_REFRESH_COOKIE, token, max_age=int(REFRESH_LIFETIME.total_seconds()),
                        httponly=True, secure=settings.JWT_COOKIE_SECURE, samesite='Lax', path='/api/auth/')


@require_http_methods(['POST'])
def login_api(request):
    data = _body(request)
    username = data.get('username', '')
    key = f'login-attempts:{request.META.get("REMOTE_ADDR", "unknown")}:{username.lower()}'
    if cache.get(key, 0) >= 5:
        return JsonResponse({'detail': 'Demasiados intentos. Intenta de nuevo en 15 minutos.'}, status=429)
    user = authenticate(request, username=username, password=data.get('password', ''))
    if not user or not user.is_active:
        cache.set(key, cache.get(key, 0) + 1, timeout=15 * 60)
        return JsonResponse({'detail': 'Credenciales inválidas'}, status=401)
    cache.delete(key)
    refresh, jti, expires = create_refresh_token(user)
    RefreshToken.objects.create(usuario=user, jti=jti, expira_en=expires)
    response = JsonResponse({'access_token': create_access_token(user), 'token_type': 'Bearer', 'expires_in': 900,
                             'is_new_user': user.is_new_user and not user.onboarding_completado})
    _set_refresh_cookie(response, refresh)
    return response


@require_http_methods(['POST'])
def refresh_api(request):
    raw = request.COOKIES.get(settings.JWT_REFRESH_COOKIE)
    if not raw:
        return JsonResponse({'detail': 'Sesión expirada, inicia sesión de nuevo'}, status=401)
    try:
        payload = decode_token(raw, 'refresh')
        record = RefreshToken.objects.get(jti=payload['jti'], usuario_id=payload['sub'])
        if not record.vigente:
            raise jwt.InvalidTokenError('Token revocado')
        user = record.usuario
    except (jwt.PyJWTError, KeyError, RefreshToken.DoesNotExist):
        return JsonResponse({'detail': 'Sesión expirada, inicia sesión de nuevo'}, status=401)
    record.revocado_en = timezone.now()
    record.save(update_fields=['revocado_en'])
    refresh, jti, expires = create_refresh_token(user)
    RefreshToken.objects.create(usuario=user, jti=jti, expira_en=expires)
    response = JsonResponse({'access_token': create_access_token(user), 'token_type': 'Bearer', 'expires_in': 900})
    _set_refresh_cookie(response, refresh)
    return response


@require_http_methods(['POST'])
def logout_api(request):
    raw = request.COOKIES.get(settings.JWT_REFRESH_COOKIE)
    if raw:
        try:
            RefreshToken.objects.filter(jti=decode_token(raw, 'refresh').get('jti'), revocado_en__isnull=True).update(revocado_en=timezone.now())
        except jwt.PyJWTError:
            pass
    response = JsonResponse({'detail': 'Sesión cerrada'})
    response.delete_cookie(settings.JWT_REFRESH_COOKIE, path='/api/auth/')
    return response


@require_http_methods(['POST'])
def completar_onboarding_api(request):
    request.api_user.onboarding_completado = True
    request.api_user.is_new_user = False
    request.api_user.save(update_fields=['onboarding_completado', 'is_new_user'])
    return JsonResponse({'onboarding_completado': True})
