# Configuración de Correo Electrónico en Producción

## Problema Resuelto

Los usuarios no recibían el correo de verificación al registrarse porque:
1. El backend de correo estaba configurado como `console.EmailBackend` (solo imprime en consola)
2. No se enviaba el correo de verificación en el registro

## Cambios Realizados

### 1. Backend de Correo Dinámico

Ahora el sistema usa:
- **Desarrollo (DEBUG=True):** `console.EmailBackend` (imprime en consola)
- **Producción (DEBUG=False):** SMTP real

### 2. Envío de Correo de Verificación

Al registrarse, el usuario:
1. Se crea con `correo_verificado = False`
2. Se genera un token de verificación
3. Se envía un correo HTML con el enlace de verificación
4. El usuario debe hacer clic en el enlace para verificar su correo
5. Solo después de verificar puede iniciar sesión

## Configuración en Producción

### Opción A: Gmail (Recomendado para desarrollo)

1. **Crear contraseña de aplicación en Gmail:**
   - Ve a https://myaccount.google.com/security
   - Activa "Verificación en dos pasos"
   - Ve a "Contraseñas de aplicación"
   - Genera una contraseña para "Correo"

2. **Configurar variables de entorno en tu hosting:**

```bash
# En Railway, Render, Heroku, etc.
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False
EMAIL_HOST_USER=tu_correo@gmail.com
EMAIL_HOST_PASSWORD=tu_contraseña_de_aplicacion
```

**⚠️ IMPORTANTE:** Nunca uses tu contraseña normal de Gmail, usa una contraseña de aplicación.

### Opción B: SendGrid (Recomendado para producción)

1. **Crear cuenta en SendGrid:** https://sendgrid.com
2. **Obtener API Key:**
   - Ve a Settings → API Keys
   - Crea una API Key con permisos de "Mail Send"

3. **Configurar variables de entorno:**

```bash
EMAIL_HOST=smtp.sendgrid.net
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False
EMAIL_HOST_USER=apikey
EMAIL_HOST_PASSWORD=tu_api_key_de_sendgrid
```

### Opción C: Mailgun

1. **Crear cuenta en Mailgun:** https://www.mailgun.com
2. **Configurar variables de entorno:**

```bash
EMAIL_HOST=smtp.mailgun.org
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False
EMAIL_HOST_USER=postmaster@tu-dominio.mailgun.org
EMAIL_HOST_PASSWORD=tu_password_de_mailgun
```

### Opción D: Otro proveedor SMTP

Cualquier proveedor SMTP funciona, solo necesitas:
- `EMAIL_HOST`: servidor SMTP (ej: `smtp.mailtrap.io`)
- `EMAIL_PORT`: puerto (generalmente 587 para TLS, 465 para SSL)
- `EMAIL_USE_TLS`: True o False
- `EMAIL_HOST_USER`: tu usuario SMTP
- `EMAIL_HOST_PASSWORD`: tu contraseña SMTP

## Verificar la Configuración

### En Desarrollo

Cuando te registres, verás el correo impreso en la consola:

```
Content-Type: text/plain; charset="utf-8"
MIME-Version: 1.0
Content-Transfer-Encoding: 7bit
Subject: Verifica tu correo - Agrivale
From: Agrivale <no-reply@agrivale.com>
To: usuario@ejemplo.com
Date: ...
...

Hola Usuario,

Gracias por registrarte en Agrivale...
```

### En Producción

Verifica en los logs del servidor:

```bash
# En Railway/Render/etc.
# Busca en los logs:
✅ Correo de verificación enviado a usuario@ejemplo.com
```

O si hay error:

```bash
❌ ERROR ENVIANDO CORREO A usuario@ejemplo.com: [error details]
```

## Troubleshooting

### "No me llega el correo"

1. **Verificar logs del servidor:**
   - Busca el mensaje `✅ Correo de verificación enviado a...`
   - Si aparece, el correo se envió correctamente
   - Si no aparece, hay un error en el envío

2. **Verificar carpeta de SPAM:**
   - Muchos correos de verificación van a spam
   - Pedir al usuario que revise spam

3. **Verificar configuración SMTP:**
   - Revisa que las variables de entorno estén correctas
   - Verifica que la contraseña de aplicación sea correcta
   - Prueba con un servicio como Mailtrap para testing

4. **Verificar logs de error:**
   ```bash
   ❌ ERROR ENVIANDO CORREO A usuario@ejemplo.com: [error]
   ```
   - Errores comunes:
     - `AuthenticationFailed`: Usuario/contraseña incorrectos
     - `SMTPConnectError`: No se puede conectar al servidor
     - `SMTPException`: Error genérico de SMTP

### "El correo llega pero el enlace no funciona"

1. **Verificar que ALLOWED_HOSTS incluya el dominio:**
   ```python
   ALLOWED_HOSTS = ['*']  # o mejor: ['tu-dominio.com', 'localhost']
   ```

2. **Verificar CSRF_TRUSTED_ORIGINS:**
   ```python
   CSRF_TRUSTED_ORIGINS = [
       "https://tu-dominio.com",
       "https://*.railway.app",
   ]
   ```

3. **Verificar que la URL sea HTTPS en producción:**
   ```python
   # En settings.py
   if not DEBUG:
       # Asegurar que la URL use HTTPS
       dominio = get_current_site(request).domain
       url_verificacion = f"https://{dominio}{reverse('usuarios:verificar_email', args=[token])}"
   ```

## Prueba Rápida

Para probar que el correo funciona:

1. **Registra un nuevo usuario** en la aplicación
2. **Verifica la consola del servidor** (en desarrollo)
3. **Deberías ver:**
   ```
   ✅ Correo de verificación enviado a usuario@ejemplo.com
   ```

4. **En producción:**
   - Revisa los logs del hosting
   - Verifica que el correo llegue (o vaya a spam)

## Variables de Entorno Requeridas en Producción

```bash
# .env o variables del hosting
DEBUG=False
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False
EMAIL_HOST_USER=tu_correo@gmail.com
EMAIL_HOST_PASSWORD=tu_contraseña_aplicacion
```

## Notas de Seguridad

- ⚠️ **Nunca** commits contraseñas o API keys al repositorio
- ✅ Usa variables de entorno (`.env` en desarrollo, variables del hosting en producción)
- ✅ El archivo `.env` debe estar en `.gitignore`
- ✅ Usa contraseñas de aplicación en lugar de contraseñas normales
- ✅ Rota las credenciales periódicamente

## Próximos Pasos

1. Configurar las variables de entorno en tu hosting
2. Probar el registro de un nuevo usuario
3. Verificar que llegue el correo
4. Probar el enlace de verificación
5. Verificar que el usuario pueda iniciar sesión después de verificar