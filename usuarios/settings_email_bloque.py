# ──────────────────────────────────────────
# CONFIGURACIÓN DE CORREO
# ──────────────────────────────────────────
# En desarrollo: los correos se imprimen en la consola (no necesitas cuenta SMTP)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
DEFAULT_FROM_EMAIL = 'Agrivale <no-reply@agrivale.com>'

# ── CUANDO VAYAS A PRODUCCIÓN, reemplaza el bloque de arriba por esto: ──
# EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
# EMAIL_HOST = 'smtp.gmail.com'
# EMAIL_PORT = 587
# EMAIL_USE_TLS = True
# EMAIL_HOST_USER = 'tu_correo@gmail.com'
# EMAIL_HOST_PASSWORD = 'tu_contraseña_de_aplicacion'   # no la de Gmail, la "App Password"
# DEFAULT_FROM_EMAIL = f'Agrivale <{EMAIL_HOST_USER}>'