# Solución: Login en Admin Panel

## Problema Reportado

El usuario encargado del admin_panel no puede iniciar sesión.

## Diagnóstico Paso a Paso

### Paso 1: Verificar Credenciales

Primero, verifica que el usuario pueda autenticarse:

1. Intenta iniciar sesión en la tienda (login normal) con las mismas credenciales
2. Si NO puede iniciar sesión en la tienda:
   - El problema es con la contraseña o el usuario no existe
   - Usa "solicitar recuperación de contraseña"

### Paso 2: Verificar que el usuario existe y está activo

Ejecuta en la shell de Django:

```bash
python manage.py shell
```

Luego:

```python
from usuarios.models import Usuario

usuario = Usuario.objects.get(username='NOMBRE_DEL_USUARIO')

print(f"Username: {usuario.username}")
print(f"Nombre completo: {usuario.nombre_completo}")
print(f"Email: {usuario.correo}")
print(f"Activo: {usuario.is_active}")
print(f"is_superuser: {usuario.is_superuser}")
```

**Posibles problemas:**
- Si `is_active = False` → La cuenta está desactivada
- Si el usuario no existe → Necesita crear la cuenta primero

### Paso 3: Verificar si tiene UsuarioPanel asignado

```python
from admin_panel.models import UsuarioPanel

usuario = Usuario.objects.get(username='NOMBRE_DEL_USUARIO')

try:
    usuario_panel = UsuarioPanel.objects.select_related('rol').get(usuario=usuario)
    print(f"✅ Tiene UsuarioPanel")
    
    if usuario_panel.rol:
        print(f"   Rol: {usuario_panel.rol.nombre}")
        print(f"   Rol activo: {usuario_panel.rol.activo}")
        
        if usuario_panel.rol.activo:
            print("\n✅ ACCESO AL PANEL: PERMITIDO")
        else:
            print("\n❌ ACCESO AL PANEL: DENEGADO (rol inactivo)")
    else:
        print("   ❌ Sin rol asignado")
        
except UsuarioPanel.DoesNotExist:
    print("\n❌ No tiene UsuarioPanel asignado")
    
    if usuario.is_superuser:
        print("   ✅ PERO es superuser")
    else:
        print("   ❌ No es superuser, NO tiene acceso")
```

## Solución Rápida

Si el usuario NO tiene UsuarioPanel:

### Opción A: Usar el Admin de Django

1. Inicia sesión en `/admin/` con un superuser
2. Ve a **Admin Panel → Roles de Panel**
3. Crea un rol (ej: "Administrador") con los permisos necesarios
4. Ve a **Admin Panel → Usuarios de Panel**
5. Agrega el usuario con el rol creado
6. El usuario ya puede acceder en `/admin_panel/login/`

### Opción B: Usar shell de Django

```python
from usuarios.models import Usuario
from admin_panel.models import UsuarioPanel, RolPanel

usuario = Usuario.objects.get(username='NOMBRE_DEL_USUARIO')

rol, created = RolPanel.objects.get_or_create(
    nombre='Administrador',
    defaults={
        'activo': True,
        'puede_gestionar_productos': True,
        'puede_gestionar_pedidos': True,
        'puede_gestionar_clientes': True,
    }
)

usuario_panel = UsuarioPanel.objects.get_or_create(
    usuario=usuario,
    defaults={'rol': rol}
)

print(f"✅ UsuarioPanel creado: {usuario_panel[1]}")
```

## Errores Comunes

### "Usuario o contraseña incorrectos"
- Verificar credenciales en la tienda primero
- Usar recuperación de contraseña si es necesario

### "No tienes permisos para acceder al panel"
- El usuario no tiene UsuarioPanel asignado
- Solución: Asignar UsuarioPanel con RolPanel activo

### "No tienes un rol asignado"
- El UsuarioPanel existe pero no tiene rol
- Solución: Asignar un RolPanel al UsuarioPanel

### "Tu rol está desactivado"
- El RolPanel tiene `activo=False`
- Solución: Cambiar a `activo=True` en el admin