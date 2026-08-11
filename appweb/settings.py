import os
from pathlib import Path
from dotenv import dotenv_values, load_dotenv
import dj_database_url
from django.db.backends.base.base import BaseDatabaseWrapper
import django.db.backends.mysql.features as mysql_features
import cloudinary
import cloudinary.uploader
import cloudinary.api


BaseDatabaseWrapper.check_database_version_supported = lambda self: None
@property
def mock_can_return_rows_from_bulk_insert(self):
    return False

mysql_features.DatabaseFeatures.can_return_rows_from_bulk_insert = mock_can_return_rows_from_bulk_insert
mysql_features.DatabaseFeatures.can_return_columns_from_insert = mock_can_return_rows_from_bulk_insert

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("SECRET_KEY") or dotenv_values(BASE_DIR / ".env").get("SECRET_KEY") or "django-insecure-default-fallback-key-12345"

DEBUG = os.getenv("DEBUG", "False").lower() == "true"

ALLOWED_HOSTS = ['*']
DOMINIO = os.getenv("DOMINIO", "https://agrifinal-production.up.railway.app")
SITE_URL = os.getenv("SITE_URL", "https://agrifinal-production.up.railway.app")

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

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
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'usuarios.middleware.JWTApiAuthenticationMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'usuarios.middleware.AdminAccessMiddleware',
    'usuarios.middleware.SessionValidationMiddleware',
    'usuarios.middleware.SessionSecurityMiddleware',
    'usuarios.middleware.NoCacheAuthenticatedMiddleware',
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

# archivos estaticos
STATIC_URL = 'static/'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]
STATIC_ROOT = BASE_DIR / 'staticfiles'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

#cloudinary para imagenes
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': os.getenv('CLOUDINARY_CLOUD_NAME'),
    'API_KEY': os.getenv('CLOUDINARY_API_KEY'),
    'API_SECRET': os.getenv('CLOUDINARY_API_SECRET'),
}

cloudinary.config(
    cloud_name=CLOUDINARY_STORAGE['CLOUD_NAME'],
    api_key=CLOUDINARY_STORAGE['API_KEY'],
    api_secret=CLOUDINARY_STORAGE['API_SECRET']
)

# configuracion de almacenamientos
STORAGES = {
    "default": {
        "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# archivos multimedia
MEDIA_URL = '/media/'

JWT_REFRESH_COOKIE = 'agrivale_refresh'
JWT_COOKIE_SECURE = not DEBUG

AUTH_USER_MODEL = 'usuarios.Usuario'
LOGIN_URL = '/usuarios/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

# Configuración de sesiones
SESSION_COOKIE_AGE = 60 * 60 * 8        # Sesión dura 8 horas de inactividad máxima
SESSION_EXPIRE_AT_BROWSER_CLOSE = True  # Se cierra automáticamente al cerrar el navegador
SESSION_SAVE_EVERY_REQUEST = True       # Renueva el tiempo de vida en cada request activo
SESSION_COOKIE_HTTPONLY = True          # JS no puede leer la cookie de sesión (seguridad)
SESSION_COOKIE_SECURE = not DEBUG       # Solo se envía por HTTPS en producción
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SECURE = not DEBUG

#correo
if DEBUG:
    # En desarrollo: imprimir correos en consola
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
else:
    # En producción: usar SMTP real
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
    EMAIL_PORT = int(os.getenv('EMAIL_PORT', 587))
    EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True').lower() == 'true'
    EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
    EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
    EMAIL_USE_SSL = False

DEFAULT_FROM_EMAIL = 'Agrivale <no-reply@agrivale.com>'

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

# Stripe API (pagos)
STRIPE_PUBLIC_KEY = os.getenv("STRIPE_PUBLIC_KEY")
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")

# MercadoPago API
MERCADOPAGO_ACCESS_TOKEN = os.getenv("MERCADOPAGO_ACCESS_TOKEN")
MERCADOPAGO_PUBLIC_KEY = os.getenv("MERCADOPAGO_PUBLIC_KEY")
MERCADOPAGO_WEBHOOK_SECRET = os.getenv("MERCADOPAGO_WEBHOOK_SECRET")

#Logging de Consola
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
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True,
        },
        'usuarios': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'admin_panel': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}