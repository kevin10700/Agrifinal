# Solución: Error de Migración MySQL - Modelo Usuario

## Problema Original
```
ValueError: Model usuarios.Usuario can't have more than one auto-generated field.
```

Este error ocurría al intentar aplicar la migración `XXXX_migrar_id_usuario_a_id.py` porque:

1. El modelo `Usuario` extiende `AbstractUser` que provee un campo `id` auto-generado
2. La migración intentaba agregar otro campo `AutoField` (`id_temp`)
3. Django no permite más de un campo auto-generado por modelo

## Solución Implementada

### 1. Eliminación de Migración Problemática
- **Eliminado**: `usuarios/migrations/XXXX_migrar_id_usuario_a_id.py`
  - Esta migración intentaba agregar un `AutoField` temporal, lo cual causaba conflicto

### 2. Nueva Migración con SQL Directo
- **Creado**: `usuarios/migrations/0008_rename_id_usuario_to_id.py`
  - Usa `ALTER TABLE ... CHANGE COLUMN` para renombrar directamente en MySQL
  - Renombra `id_usuario` → `id` en la tabla `usuarios_usuario`
  - También actualiza todas las columnas FK relacionadas en otras tablas:
    - `admin_panel_rolpanel`
    - `admin_panel_movimiento_inventario`
    - `admin_panel_historial_producto`
    - `usuarios_direccion_envio`
    - `usuarios_token_verificacion`
    - `usuarios_token_recuperacion`
    - `usuarios_refresh_token`
    - `pedidos_pedido`
    - `pedidos_carritoitem`
    - `pedidos_notificacion`
    - `pedidos_comentarioproducto`
    - `productos_favorito`

### 3. Actualización de Modelos
Cambiado `db_column='id_usuario'` a `db_column='id'` en todos los ForeignKey fields:

**admin_panel/models.py:**
- `RolPanel.usuario`
- `MovimientoInventario.usuario`
- `HistorialProducto.usuario`

**pedidos/models.py:**
- `Pedido.id_usuario`
- `CarritoItem.id_usuario`
- `Notificacion.id_usuario`
- `ComentarioProducto.id_usuario`

**productos/models.py:**
- `Favorito.id_usuario`

**admin_panel/models.py (UsuarioPanel):**
- Cambiado a `db_column='usuario_id'` para evitar conflicto con el campo `id` auto-generado del modelo

### 4. Compatibilidad con MySQL
- La migración usa SQL nativo de MySQL: `ALTER TABLE ... CHANGE COLUMN`
- No requiere subconsultas con LIMIT ni operaciones complejas
- Compatible con versiones antiguas de MySQL

## Cómo Aplicar la Migración

```bash
python manage.py migrate usuarios
```

Esto ejecutará la migración `0008_rename_id_usuario_to_id` que:
1. Renombra la columna `id_usuario` a `id` en `usuarios_usuario`
2. Actualiza todas las columnas FK relacionadas
3. Mantiene la integridad referencial

## Verificación

- ✅ Django system check: sin errores
- ✅ Python syntax validation: exitosa
- ✅ Commit y push a GitHub: exitoso (commit ea37ec6)

## Nota sobre Sesiones

El middleware de sesiones (`usuarios/middleware.py`) está correctamente configurado y funcionando. Valida:
- Usuario existe en la base de datos
- Usuario está activo
- Sesión es válida

Si hay problemas con sesiones, verificar:
1. Que la migración se aplicó correctamente
2. Que `django.contrib.sessions` está en `INSTALLED_APPS`
3. Que el middleware de sesiones está en `MIDDLEWARE`