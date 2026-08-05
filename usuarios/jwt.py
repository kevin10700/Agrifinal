"""JWT de corta duración para la API. El access token sólo vive en el cliente."""
from datetime import timedelta
from uuid import uuid4

import jwt
from django.conf import settings
from django.utils import timezone

ACCESS_LIFETIME = timedelta(minutes=15)
REFRESH_LIFETIME = timedelta(days=7)
ALGORITHM = "HS256"


def _encode(payload):
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def create_access_token(user):
    now = timezone.now()
    return _encode({"sub": str(user.pk), "type": "access", "iat": now, "exp": now + ACCESS_LIFETIME})


def create_refresh_token(user):
    now = timezone.now()
    jti = uuid4().hex
    token = _encode({"sub": str(user.pk), "type": "refresh", "jti": jti, "iat": now, "exp": now + REFRESH_LIFETIME})
    return token, jti, now + REFRESH_LIFETIME


def decode_token(token, expected_type):
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    if payload.get("type") != expected_type:
        raise jwt.InvalidTokenError("Tipo de token inválido")
    return payload
