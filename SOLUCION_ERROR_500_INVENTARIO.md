# Solución: Error 500 en Inventario/Historial

## Problema Reportado

Error 500 al acceder a la sección de inventario/historial del panel administrativo.

## Cambios Implementados

Se agregó **logging detallado** y **manejo de errores** en las 3 vistas de inventario:

1. `historial_producto` - Historial de un producto específico
2. `historial_productos_lista` - Lista de todos los productos con historial
3. `inventario_movimientos` - Kardex/movimientos de inventario

## Cómo Diagnosticar el Error

### Paso 1: Acceder a la sección problemática

Intenta acceder a:
- `/admin_panel/inventario/historial/` - Lista de productos
- `/admin_panel/inventario/historial/<id_producto>/` - Historial de producto específico
- `/admin_panel/inventario/movimientos/` - Movimientos de inventario (Kardex)

### Paso 2: Revisar los logs

Cuando ocurra el error, revisa la **consola del servidor** (donde ejecutas `python manage.py runserver`).

Deberías ver mensajes como:

```
📊 Cargando lista de historial de productos
✅ Productos cargados: 50
✅ Historial procesado para 50 productos
✅ Renderizando lista de historial de productos
```

O si hay error:

```
❌ Error en historial_productos_lista: [mensaje de error]
```

## Posibles Causas del Error 500

### 1. Error en la base de datos

**Síntoma:** Logs muestran error de conexión o consulta SQL

**Ejemplo de log:**
```
❌ Error en historial_productos_lista: column admin_panel_historial_producto.id_movimiento does not exist
```

**Solución:** Ejecutar migraciones pendientes:
```bash
python manage.py migrate
```

### 2. Template no encontrado

**Síntoma:** Logs muestran error de template

**Ejemplo de log:**
```
❌ Error en historial_productos_lista: TemplateDoesNotExist at /admin_panel/inventario/historial/
admin_panel/inventario/historial_productos.html
```

**Solución:** Verificar que existan los templates:
- `admin_panel/templates/admin_panel/inventario/historial_productos.html`
- `admin_panel/templates/admin_panel/inventario/historial_producto.html`
- `admin_panel/templates/admin_panel/inventario/movimientos.html`

### 3. Error en el template (variable inexistente)

**Síntoma:** El template usa una variable que no existe en el contexto

**Ejemplo de log:**
```
❌ Error en historial_productos_lista: 'producto' is undefined
```

**Solución:** Verificar que el template use las variables correctas del contexto.

### 4. Producto no existe

**Síntoma:** Al acceder a un historial de producto específico que no existe

**Ejemplo de log:**
```
📊 Cargando historial de producto ID: 999
❌ Error en historial_producto (ID: 999): Producto matching query does not exist.
```

**Solución:** Esto ya está manejado con `get_object_or_404`, pero ahora redirige al inventario con un mensaje de error.

### 5. Permisos insuficientes

**Síntoma:** El usuario no tiene el permiso `puede_gestionar_inventario`

**Solución:** Asignar el permiso al rol del usuario en el admin panel.

## Información de Debug

Los logs ahora muestran:

1. **Cuándo se carga cada vista:**
   - `📊 Cargando historial de producto ID: 123`
   - `📊 Cargando lista de historial de productos`
   - `📊 Cargando movimientos de inventario`

2. **Datos cargados:**
   - `✅ Producto encontrado: Nombre del Producto`
   - `✅ Productos cargados: 50`
   - `✅ Historial cargado: 25 registros`
   - `✅ Movimientos cargados: 150`

3. **Renderizado:**
   - `✅ Renderizando historial de Producto X`
   - `✅ Renderizando lista de historial de productos`
   - `✅ Renderizando movimientos de inventario`

4. **Errores (si los hay):**
   - `❌ Error en [vista]: [mensaje de error]`
   - Incluye stack trace completo para debugging

## Acciones Correctivas

Si ves un error en los logs:

1. **Anota el mensaje completo del error**
2. **Verifica la línea del código** que aparece en el stack trace
3. **Revisa que los datos en la base de datos sean correctos**
4. **Verifica que las migraciones estén aplicadas:**
   ```bash
   python manage.py showmigrations admin_panel
   python manage.py migrate
   ```

## Mejora de Experiencia de Usuario

Ahora cuando hay un error:
- **Antes:** Error 500 genérico, pantalla en blanco
- **Ahora:** Mensaje de error específico + redirección al inventario

El usuario ve un mensaje como:
```
Error al cargar el historial: [descripción del error]
```

## Próximos Pasos

1. Accede a la sección de inventario/historial
2. Revisa los logs de la consola
3. Identifica el error específico
4. Aplica la solución correspondiente según la causa

## Contacto

Si después de revisar los logs necesitas ayuda, comparte:
1. El mensaje de error completo del log
2. La URL que estabas intentando acceder
3. El stack trace completo (si aparece)