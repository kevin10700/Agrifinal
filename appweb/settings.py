import os
from pathlib import Path
from dotenv import dotenv_values, load_dotenv
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
SECRET_KEY = os.getenv("SECRET_KEY") or dotenv_values(BASE_DIR / ".env").get("SECRET_KEY")

DEBUG = os.getenv("DEBUG", "False").lower() == "true"

# En desarrollo permite el servidor local aunque DEBUG se mantenga desactivado.
# En producción define ALLOWED_HOSTS en .env con los dominios públicos separados por coma.
ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv("ALLOWED_HOSTS", "127.0.0.1,localhost,.ngrok-free.dev, agrifinal-production.up.railway.app").split(",")
    if host.strip()
]

# ── Ngrok / proxy seguro ──────────────────────────────────
# Permite que Django confíe en el header X-Forwarded-Proto que
# ngrok envía para indicar HTTPS.  Sin esto CSRF rompe porque
# Django cree que está en HTTP y rechaza el origen HTTPS.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Orígenes que Django aceptará como válidos para CSRF cuando el
# sitio se sirve a través de túneles como ngrok.
# El patrón .ngrok-free.dev cubre todos los subdominios gratuitos.
CSRF_TRUSTED_ORIGINS = os.getenv(
    "CSRF_TRUSTED_ORIGINS",
    "https://agrifinal-production.up.railway.app,https://*.ngrok-free.dev,https://*.ngrok.io,http://127.0.0.1:8000,http://localhost:8000",
).split(",")

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

import os
from dotenv import load_dotenv

# Carga las variables del archivo .env
load_dotenv()

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.getenv('DB_NAME'),
        'USER': os.getenv('DB_USER'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': os.getenv('DB_HOST'),
        'PORT': os.getenv('DB_PORT'),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Las contraseñas nuevas se almacenan con bcrypt; Django mantiene soporte de
# hashes anteriores para migrarlos al iniciar sesión.
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
]

LANGUAGE_CODE = 'es-mx'
TIME_ZONE = 'America/Mexico_City'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]
STATIC_ROOT = BASE_DIR / 'staticfiles'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Las cookies secure se activan automáticamente fuera de desarrollo.
JWT_REFRESH_COOKIE = 'agrivale_refresh'
JWT_COOKIE_SECURE = not DEBUG

AUTH_USER_MODEL = 'usuarios.Usuario'
LOGIN_URL = '/usuarios/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

EMAIL_BACKEND       = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST          = 'smtp.gmail.com'
EMAIL_PORT          = 587
EMAIL_USE_TLS       = True
EMAIL_HOST_USER     = os.getenv('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL  = f'Agrivale <{os.getenv("EMAIL_HOST_USER")}>'
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# Envia API. Las credenciales y datos de origen se leen solo desde .env.
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

# settings.py
STRIPE_PUBLIC_KEY = os.getenv("STRIPE_PUBLIC_KEY")
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
MERCADOPAGO_ACCESS_TOKEN = os.getenv("MERCADOPAGO_ACCESS_TOKEN")
MERCADOPAGO_PUBLIC_KEY = os.getenv("MERCADOPAGO_PUBLIC_KEY")
MERCADOPAGO_WEBHOOK_SECRET = os.getenv("MERCADOPAGO_WEBHOOK_SECRET")
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
