import os
from pathlib import Path
from dotenv import dotenv_values, load_dotenv
import dj_database_url
from django.db.backends.base.base import BaseDatabaseWrapper
import django.db.backends.mysql.features as mysql_features

# 1. Evitamos que Django bloquee el arranque por la versión de MariaDB
BaseDatabaseWrapper.check_database_version_supported = lambda self: None

# 2. Le indicamos a Django que nuestro motor NO soporta la sintaxis RETURNING
@property
def mock_can_return_rows_from_bulk_insert(self):
    return False

mysql_features.DatabaseFeatures.can_return_rows_from_bulk_insert = mock_can_return_rows_from_bulk_insert
mysql_features.DatabaseFeatures.can_return_columns_from_insert = mock_can_return_rows_from_bulk_insert

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# Una variable de Windows vacía no debe anular el valor configurado en .env.
SECRET_KEY = os.getenv("SECRET_KEY") or dotenv_values(BASE_DIR / ".env").get("SECRET_KEY") or "django-insecure-default-fallback-key-12345"

DEBUG = os.getenv("DEBUG", "False").lower() == "true"

ALLOWED_HOSTS = ['*']

# ── Proxy seguro ──────────────────────────────────────────
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# ── CSRF Trusted Origins ──────────────────────────────────
CSRF_TRUSTED_ORIGINS = [
    "https://agrifinal-production.up.railway.app",
    "https://*.ngrok-free.dev",
    "https://*.ngrok.io",
    "http://127.0.0.1:8000",
    "http://localhost:8000",
]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    "django.contrib.humanize",
    "productos",
    "usuarios",
    "chatbot",
    "payments.apps.PaymentsConfig",
    'pedidos.apps.PedidosConfig',
    "shipping.apps.ShippingConfig",
    "admin_panel.apps.AdminPanelConfig",
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Sirve archivos estáticos en producción
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'usuarios.middleware.JWTApiAuthenticationMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'appweb.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'admin_panel.context_processors.alertas_sistema',
            ],
        },
    },
]

WSGI_APPLICATION = 'appweb.wsgi.application'

# ── Base de Datos (Railway vs Desarrollo Local) ──────────
db_from_env = os.getenv("DATABASE_URL") or os.getenv("MYSQL_URL")

if db_from_env:
    parsed_db = dj_database_url.parse(
        db_from_env,
        conn_max_age=600,
        engine='django.db.backends.mysql'
    )
    if parsed_db:
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.mysql',
                'NAME': parsed_db.get('NAME'),
                'USER': parsed_db.get('USER'),
                'PASSWORD': parsed_db.get('PASSWORD'),
                'HOST': parsed_db.get('HOST'),
                'PORT': parsed_db.get('PORT') or '3306',
            }
        }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': os.getenv('DB_NAME', ''),
            'USER': os.getenv('DB_USER', ''),
            'PASSWORD': os.getenv('DB_PASSWORD', ''),
            'HOST': os.getenv('DB_HOST', '127.0.0.1'),
            'PORT': os.getenv('DB_PORT', '3306'),
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
]

LANGUAGE_CODE = 'es-mx'
TIME_ZONE = 'America/Mexico_City'
USE_I18N = True
USE_TZ = True

# ── Archivos Estáticos ────────────────────────────────────
STATIC_URL = 'static/'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]
STATIC_ROOT = BASE_DIR / 'staticfiles'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Compresión y caché de archivos estáticos para WhiteNoise
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

JWT_REFRESH_COOKIE = 'agrivale_refresh'
JWT_COOKIE_SECURE = not DEBUG

AUTH_USER_MODEL = 'usuarios.Usuario'
LOGIN_URL = '/usuarios/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# ── Correo y Servicios Externos (Resend API / SMTP) ───────
RESEND_API_KEY = os.getenv('RESEND_API_KEY')

if RESEND_API_KEY:
    # Usando API de Resend para bypass de bloqueos de puertos SMTP
    DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'Agrivale <onboarding@resend.dev>')
else:
    # Respaldo SMTP tradicional o desarrollo local
    EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend')
    EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
    EMAIL_PORT = int(os.getenv('EMAIL_PORT', 465))
    EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'False').lower() in ('true', '1', 't')
    EMAIL_USE_SSL = os.getenv('EMAIL_USE_SSL', 'True').lower() in ('true', '1', 't')
    EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
    EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
    DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', EMAIL_HOST_USER)
    EMAIL_TIMEOUT = 10

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# Envia API
ENVIA_API_TOKEN = os.getenv("ENVIA_API_TOKEN")
ENVIA_API_URL = os.getenv("ENVIA_API_URL")
ENVIA_ENVIRONMENT = os.getenv("ENVIA_ENVIRONMENT", "test")
ENVIA_DEFAULT_CARRIER = os.getenv("ENVIA_DEFAULT_CARRIER", "dhl")
ENVIA_ORIGIN_NAME = os.getenv("ENVIA_ORIGIN_NAME")
ENVIA_ORIGIN_PHONE = os.getenv("ENVIA_ORIGIN_PHONE")
ENVIA_ORIGIN_STREET = os.getenv("ENVIA_ORIGIN_STREET")
ENVIA_ORIGIN_CITY = os.getenv("ENVIA_ORIGIN_CITY")
ENVIA_ORIGIN_STATE = os.getenv("ENVIA_ORIGIN_STATE")
ENVIA_ORIGIN_COUNTRY = os.getenv("ENVIA_ORIGIN_COUNTRY")
ENVIA_ORIGIN_POSTAL_CODE = os.getenv("ENVIA_ORIGIN_POSTAL_CODE")
ENVIA_LABEL_FORMAT = os.getenv("ENVIA_LABEL_FORMAT")
ENVIA_LABEL_SIZE = os.getenv("ENVIA_LABEL_SIZE")

# Pasarelas de Pago
STRIPE_PUBLIC_KEY = os.getenv("STRIPE_PUBLIC_KEY")
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
MERCADOPAGO_ACCESS_TOKEN = os.getenv("MERCADOPAGO_ACCESS_TOKEN")
MERCADOPAGO_PUBLIC_KEY = os.getenv("MERCADOPAGO_PUBLIC_KEY")
MERCADOPAGO_WEBHOOK_SECRET = os.getenv("MERCADOPAGO_WEBHOOK_SECRET")

# ── Logging de Consola ────────────────────────────────────
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': True,
        },
    },
}