"""
Declaraciones de funciones (tools) que Gemini puede invocar
para el chatbot de administración de Agrivale.
"""
from google.genai import types
from .admin_context import CONOCIMIENTO_PANEL_ADMIN


def construir_tools_admin():
    declaraciones = [
        # ===== CATEGORÍAS =====
        types.FunctionDeclaration(
            name="crear_categoria",
            description="Crea una nueva categoría de productos.",
            parameters_json_schema={
                "type": "object",
                "properties": {
                    "nombre": {"type": "string"},
                    "icono": {"type": "string", "description": "Nombre de un icono, opcional."},
                    "orden": {"type": "integer", "description": "Orden de aparición, opcional."},
                },
                "required": ["nombre"],
            },
        ),
        types.FunctionDeclaration(
            name="editar_categoria",
            description="Edita el nombre, icono u orden de una categoría existente.",
            parameters_json_schema={
                "type": "object",
                "properties": {
                    "categoria_actual": {"type": "string", "description": "Nombre actual de la categoría a editar."},
                    "nuevo_nombre": {"type": "string"},
                    "icono": {"type": "string"},
                    "orden": {"type": "integer"},
                },
                "required": ["categoria_actual"],
            },
        ),
        types.FunctionDeclaration(
            name="eliminar_categoria",
            description="Elimina una categoría del catálogo. CUIDADO: elimina también sus productos en cascada.",
            parameters_json_schema={
                "type": "object",
                "properties": {"nombre_categoria": {"type": "string"}},
                "required": ["nombre_categoria"],
            },
        ),
        types.FunctionDeclaration(
            name="listar_categorias",
            description="Lista todas las categorías existentes.",
            parameters_json_schema={"type": "object", "properties": {}},
        ),

        # ===== PRODUCTOS =====
        types.FunctionDeclaration(
            name="crear_producto",
            description="NO usar para altas iniciadas desde el chat: el servidor abre un formulario conversacional y confirma antes de crear.",
            parameters_json_schema={
                "type": "object",
                "properties": {
                    "nombre": {"type": "string"},
                    "categoria": {"type": "string", "description": "Nombre de la categoría a la que pertenece."},
                    "descripcion_corta": {"type": "string"},
                    "descripcion_larga": {"type": "string"},
                    "precio": {"type": "number"},
                    "precio_oferta": {"type": "number", "description": "Precio con descuento, opcional."},
                    "stock": {"type": "integer"},
                    "unidad_medida": {
                        "type": "string",
                        "enum": ["kg", "unidad", "libra", "docena", "caja"],
                    },
                    "es_destacado": {"type": "boolean"},
                    "es_nuevo": {"type": "boolean"},
                    "es_organico": {"type": "boolean"},
                    "temporada": {"type": "string"},
                    "origen": {"type": "string"},
                    "certificaciones": {"type": "string"},
                },
                "required": ["nombre", "categoria", "precio"],
            },
        ),
        types.FunctionDeclaration(
            name="editar_producto",
            description="Edita uno o varios campos de un producto ya existente. Solo envía los campos que el administrador quiere cambiar.",
            parameters_json_schema={
                "type": "object",
                "properties": {
                    "nombre_producto": {"type": "string", "description": "Nombre (o parte del nombre) del producto a editar."},
                    "nuevo_nombre": {"type": "string"},
                    "categoria": {"type": "string"},
                    "descripcion_corta": {"type": "string"},
                    "descripcion_larga": {"type": "string"},
                    "precio": {"type": "number"},
                    "precio_oferta": {"type": "number"},
                    "quitar_oferta": {"type": "boolean", "description": "Si es true, elimina el precio de oferta actual."},
                    "stock": {"type": "integer"},
                    "unidad_medida": {"type": "string", "enum": ["kg", "unidad", "libra", "docena", "caja"]},
                    "es_destacado": {"type": "boolean"},
                    "es_nuevo": {"type": "boolean"},
                    "es_organico": {"type": "boolean"},
                    "temporada": {"type": "string"},
                    "origen": {"type": "string"},
                    "certificaciones": {"type": "string"},
                },
                "required": ["nombre_producto"],
            },
        ),
        types.FunctionDeclaration(
            name="eliminar_producto",
            description="Elimina un producto del catálogo permanentemente.",
            parameters_json_schema={
                "type": "object",
                "properties": {"nombre_producto": {"type": "string"}},
                "required": ["nombre_producto"],
            },
        ),
        types.FunctionDeclaration(
            name="subir_imagen_producto",
            description=(
                "Asigna la imagen adjunta en este mensaje como la imagen principal de un producto. "
                "Úsala solo cuando el administrador haya adjuntado una imagen Y mencione un producto."
            ),
            parameters_json_schema={
                "type": "object",
                "properties": {"nombre_producto": {"type": "string"}},
                "required": ["nombre_producto"],
            },
        ),
        types.FunctionDeclaration(
            name="cambiar_stock",
            description="Cambia el stock (inventario) de un producto a un número exacto.",
            parameters_json_schema={
                "type": "object",
                "properties": {
                    "nombre_producto": {"type": "string"},
                    "nuevo_stock": {"type": "integer"},
                },
                "required": ["nombre_producto", "nuevo_stock"],
            },
        ),
        types.FunctionDeclaration(
            name="buscar_productos",
            description="Busca y lista productos por nombre, categoría o si están bajos de stock.",
            parameters_json_schema={
                "type": "object",
                "properties": {
                    "termino": {"type": "string"},
                    "bajo_stock": {"type": "boolean", "description": "Si es true, lista productos con stock <= 5."},
                },
            },
        ),

        # ===== PEDIDOS =====
        types.FunctionDeclaration(
            name="cambiar_estado_pedido",
            description="Cambia el estado de un pedido (pendiente, confirmado, preparando, enviado, entregado, cancelado). Notifica automáticamente al cliente.",
            parameters_json_schema={
                "type": "object",
                "properties": {
                    "numero_pedido": {"type": "integer"},
                    "nuevo_estado": {
                        "type": "string",
                        "enum": ["pendiente", "confirmado", "preparando", "enviado", "entregado", "cancelado"],
                    },
                    "mensaje_extra": {"type": "string", "description": "Nota adicional opcional para el cliente."},
                },
                "required": ["numero_pedido", "nuevo_estado"],
            },
        ),
        types.FunctionDeclaration(
            name="ver_pedido",
            description="Muestra el detalle completo de un pedido específico.",
            parameters_json_schema={
                "type": "object",
                "properties": {"numero_pedido": {"type": "integer"}},
                "required": ["numero_pedido"],
            },
        ),
        types.FunctionDeclaration(
            name="listar_pedidos",
            description="Lista pedidos, opcionalmente filtrados por estado.",
            parameters_json_schema={
                "type": "object",
                "properties": {
                    "estado": {
                        "type": "string",
                        "enum": ["pendiente", "confirmado", "preparando", "enviado", "entregado", "cancelado"],
                    }
                },
            },
        ),
        types.FunctionDeclaration(
            name="resumen_operativo",
            description="Muestra la cola de trabajo: pedidos pendientes, pagos por revisar, cancelaciones y pedidos pagados sin guía. No modifica datos.",
            parameters_json_schema={"type": "object", "properties": {}},
        ),
        types.FunctionDeclaration(
            name="actualizar_pedidos_lote",
            description="Actualiza el estado de varios pedidos identificados por número en una sola operación. Úsala cuando el administrador enumere pedidos, por ejemplo: confirma 12, 15 y 18.",
            parameters_json_schema={
                "type": "object",
                "properties": {
                    "numeros_pedido": {"type": "array", "items": {"type": "integer"}, "description": "Números exactos de los pedidos."},
                    "nuevo_estado": {"type": "string", "enum": ["pendiente", "confirmado", "preparando", "enviado", "entregado", "cancelado"]},
                    "mensaje_extra": {"type": "string", "description": "Nota opcional que recibirán los clientes."},
                },
                "required": ["numeros_pedido", "nuevo_estado"],
            },
        ),
        types.FunctionDeclaration(
            name="procesar_pedido",
            description="Procesa un pedido completo en una sola operación: puede confirmar pago, cambiar estado, asignar transportista/servicio, registrar guía y estado de entrega. Incluye solo los datos indicados por el administrador.",
            parameters_json_schema={
                "type": "object",
                "properties": {
                    "numero_pedido": {"type": "integer"},
                    "marcar_pagado": {"type": "boolean"},
                    "referencia": {"type": "string"},
                    "nuevo_estado": {"type": "string", "enum": ["pendiente", "confirmado", "preparando", "enviado", "entregado", "cancelado"]},
                    "transportista": {"type": "string", "description": "Ejemplo: dhl, redpack o 99MINUTOS."},
                    "servicio": {"type": "string"},
                    "numero_guia": {"type": "string"},
                    "estado_entrega": {"type": "string", "enum": ["pendiente", "en_ruta", "en_transito", "entregado", "incidente"]},
                    "notas": {"type": "string"},
                },
                "required": ["numero_pedido"],
            },
        ),
        types.FunctionDeclaration(
            name="resolver_cancelacion",
            description="Aprueba o rechaza una solicitud de cancelación de pedido.",
            parameters_json_schema={
                "type": "object",
                "properties": {
                    "numero_pedido": {"type": "integer"},
                    "aprobar": {"type": "boolean", "description": "true para aprobar la cancelación, false para rechazarla."},
                    "razon": {"type": "string", "description": "Razón del rechazo, solo si aprobar es false."},
                },
                "required": ["numero_pedido", "aprobar"],
            },
        ),

        # ===== ENTREGAS =====
        types.FunctionDeclaration(
            name="actualizar_entrega",
            description="Crea o actualiza la información de entrega/envío de un pedido (paquetería, número de guía, estado).",
            parameters_json_schema={
                "type": "object",
                "properties": {
                    "numero_pedido": {"type": "integer"},
                    "paqueteria": {"type": "string", "enum": ["99MINUTOS", "REDPACK"]},
                    "numero_guia": {"type": "string"},
                    "estado": {"type": "string", "enum": ["pendiente", "en_ruta", "entregado", "incidente"]},
                    "notas": {"type": "string"},
                },
                "required": ["numero_pedido"],
            },
        ),

        # ===== PAGOS =====
        types.FunctionDeclaration(
            name="marcar_pago_pagado",
            description="Marca el pago de un pedido como pagado/confirmado y notifica al cliente.",
            parameters_json_schema={
                "type": "object",
                "properties": {
                    "numero_pedido": {"type": "integer"},
                    "referencia": {"type": "string"},
                },
                "required": ["numero_pedido"],
            },
        ),
        types.FunctionDeclaration(
            name="marcar_pago_fallido_o_reembolsado",
            description="Marca el pago de un pedido como fallido o reembolsado.",
            parameters_json_schema={
                "type": "object",
                "properties": {
                    "numero_pedido": {"type": "integer"},
                    "nuevo_estado": {"type": "string", "enum": ["fallido", "reembolsado"]},
                },
                "required": ["numero_pedido", "nuevo_estado"],
            },
        ),

        # ===== COMENTARIOS =====
        types.FunctionDeclaration(
            name="aprobar_comentario",
            description="Aprueba una reseña/comentario de producto para que sea pública.",
            parameters_json_schema={
                "type": "object",
                "properties": {"id_comentario": {"type": "integer"}},
                "required": ["id_comentario"],
            },
        ),
        types.FunctionDeclaration(
            name="responder_comentario",
            description="Agrega una respuesta del vendedor a un comentario/reseña de producto.",
            parameters_json_schema={
                "type": "object",
                "properties": {
                    "id_comentario": {"type": "integer"},
                    "respuesta": {"type": "string"},
                },
                "required": ["id_comentario", "respuesta"],
            },
        ),
        types.FunctionDeclaration(
            name="listar_comentarios_pendientes",
            description="Lista los comentarios/reseñas que aún no han sido aprobados.",
            parameters_json_schema={"type": "object", "properties": {}},
        ),

        # ===== USUARIOS =====
        types.FunctionDeclaration(
            name="buscar_usuario",
            description="Busca un usuario por nombre de usuario, nombre o correo, y muestra su información básica.",
            parameters_json_schema={
                "type": "object",
                "properties": {"termino": {"type": "string"}},
                "required": ["termino"],
            },
        ),
        types.FunctionDeclaration(
            name="cambiar_estado_usuario",
            description="Activa o desactiva la cuenta de un usuario (para bloquear acceso), o cambia su condición de staff.",
            parameters_json_schema={
                "type": "object",
                "properties": {
                    "termino": {"type": "string", "description": "Nombre de usuario o correo."},
                    "activo": {"type": "boolean"},
                    "es_staff": {"type": "boolean"},
                },
                "required": ["termino"],
            },
        ),

        types.FunctionDeclaration(
            name="ver_favoritos",
            description="Muestra los productos favoritos de un usuario específico o un resumen general de los productos más favoritados en el sistema.",
            parameters_json_schema={
                "type": "object",
                "properties": {
                    "usuario": {"type": "string", "description": "Nombre de usuario opcional. Si se proporciona, muestra los favoritos de ese usuario. Si no, muestra un resumen general."},
                },
                "required": [],
            },
        ),

        types.FunctionDeclaration(
            name="exportar_reportes",
            description="Exporta reportes de ventas o productos más vendidos en PDF o Excel.",
            parameters_json_schema={
                "type": "object",
                "properties": {
                    "tipo_reporte": {
                        "type": "string",
                        "enum": ["ventas", "productos"],
                        "description": "El tipo de reporte: ventas o productos."
                    },
                    "periodo": {
                        "type": "string",
                        "enum": ["dia", "semana", "mes", "anio"],
                        "description": "Periodo del reporte." 
                    },
                    "formato": {
                        "type": "string",
                        "enum": ["pdf", "excel"],
                        "description": "Formato de exportación." 
                    },
                },
                "required": ["tipo_reporte", "periodo", "formato"],
            },
        ),

        # ===== PROVEEDORES =====
        types.FunctionDeclaration(
            name="crear_proveedor",
            description="Crea un nuevo proveedor con sus datos fiscales y de contacto. El administrador debe proporcionar empresa, RFC y contacto como mínimo.",
            parameters_json_schema={
                "type": "object",
                "properties": {
                    "empresa": {"type": "string", "description": "Nombre de la empresa (obligatorio)."},
                    "rfc": {"type": "string", "description": "RFC del proveedor (obligatorio)."},
                    "contacto": {"type": "string", "description": "Nombre de la persona de contacto (obligatorio)."},
                    "correo": {"type": "string", "description": "Correo electrónico del contacto."},
                    "telefono": {"type": "string"},
                    "whatsapp": {"type": "string"},
                    "calle": {"type": "string"},
                    "numero_exterior": {"type": "string"},
                    "colonia": {"type": "string"},
                    "municipio": {"type": "string"},
                    "estado": {"type": "string"},
                    "codigo_postal": {"type": "string"},
                    "pagina_web": {"type": "string"},
                    "tiempo_entrega": {"type": "integer", "description": "Tiempo de entrega en días."},
                    "descuento": {"type": "number", "description": "Descuento en porcentaje."},
                    "condiciones_pago": {"type": "string", "enum": ["contado", "credito", "mixto"]},
                    "observaciones": {"type": "string"},
                },
                "required": ["empresa", "rfc", "contacto"],
            },
        ),
        types.FunctionDeclaration(
            name="editar_proveedor",
            description="Edita los datos de un proveedor existente por su ID.",
            parameters_json_schema={
                "type": "object",
                "properties": {
                    "proveedor_id": {"type": "integer"},
                    "empresa": {"type": "string"},
                    "rfc": {"type": "string"},
                    "contacto": {"type": "string"},
                    "correo": {"type": "string"},
                    "telefono": {"type": "string"},
                    "whatsapp": {"type": "string"},
                    "calle": {"type": "string"},
                    "numero_exterior": {"type": "string"},
                    "colonia": {"type": "string"},
                    "municipio": {"type": "string"},
                    "estado": {"type": "string"},
                    "codigo_postal": {"type": "string"},
                    "pagina_web": {"type": "string"},
                    "tiempo_entrega": {"type": "integer"},
                    "descuento": {"type": "number"},
                    "condiciones_pago": {"type": "string", "enum": ["contado", "credito", "mixto"]},
                    "observaciones": {"type": "string"},
                },
                "required": ["proveedor_id"],
            },
        ),
        types.FunctionDeclaration(
            name="eliminar_proveedor",
            description="Elimina un proveedor de la base de datos por su ID.",
            parameters_json_schema={
                "type": "object",
                "properties": {"proveedor_id": {"type": "integer"}},
                "required": ["proveedor_id"],
            },
        ),
        types.FunctionDeclaration(
            name="buscar_proveedores",
            description="Busca proveedores por nombre de empresa o RFC.",
            parameters_json_schema={
                "type": "object",
                "properties": {"termino": {"type": "string"}},
                "required": ["termino"],
            },
        ),

        # ===== NOTIFICACIONES =====
        types.FunctionDeclaration(
            name="crear_notificacion",
            description="Crea una notificación manual para un usuario relacionada con un pedido específico.",
            parameters_json_schema={
                "type": "object",
                "properties": {
                    "usuario_id": {"type": "integer", "description": "ID del usuario que recibirá la notificación."},
                    "pedido_id": {"type": "integer", "description": "ID del pedido relacionado."},
                    "mensaje": {"type": "string", "description": "Texto del mensaje de la notificación."},
                    "leida": {"type": "boolean", "description": "Si la notificación debe marcarse como leída."},
                },
                "required": ["usuario_id", "pedido_id", "mensaje"],
            },
        ),
        types.FunctionDeclaration(
            name="listar_notificaciones",
            description="Lista las notificaciones del sistema, opcionalmente filtradas por leídas/no leídas.",
            parameters_json_schema={
                "type": "object",
                "properties": {
                    "filtro": {"type": "string", "enum": ["", "leidas", "no_leidas"]},
                },
            },
        ),
        types.FunctionDeclaration(
            name="eliminar_notificacion",
            description="Elimina una notificación del sistema por su ID.",
            parameters_json_schema={
                "type": "object",
                "properties": {"notificacion_id": {"type": "integer"}},
                "required": ["notificacion_id"],
            },
        ),

        # ===== ZONAS DE REPARTO =====
        types.FunctionDeclaration(
            name="crear_zona_reparto",
            description="Crea una nueva zona de reparto con códigos postales y costo de envío. El administrador debe proporcionar al menos nombre, municipio, estado, CP inicio, CP fin, costo y tiempo de entrega.",
            parameters_json_schema={
                "type": "object",
                "properties": {
                    "nombre": {"type": "string", "description": "Nombre de la zona (ej: Zona Centro)."},
                    "municipio": {"type": "string"},
                    "estado": {"type": "string"},
                    "codigo_postal_inicio": {"type": "string", "description": "CP inicial del rango (5 dígitos)."},
                    "codigo_postal_fin": {"type": "string", "description": "CP final del rango (5 dígitos)."},
                    "costo_envio": {"type": "number", "description": "Costo de envío en pesos."},
                    "tiempo_entrega": {"type": "string", "description": "Tiempo estimado de entrega."},
                    "activo": {"type": "boolean"},
                },
                "required": ["nombre", "municipio", "estado", "codigo_postal_inicio", "codigo_postal_fin", "costo_envio", "tiempo_entrega"],
            },
        ),
        types.FunctionDeclaration(
            name="listar_zonas_reparto",
            description="Lista todas las zonas de reparto configuradas en el sistema.",
            parameters_json_schema={"type": "object", "properties": {}},
        ),

        # ===== ROLES =====
        types.FunctionDeclaration(
            name="listar_roles",
            description="Lista todos los roles de panel existentes.",
            parameters_json_schema={"type": "object", "properties": {}},
        ),

        # ===== COMPRAS =====
        types.FunctionDeclaration(
            name="listar_compras",
            description="Lista las compras a proveedores, opcionalmente filtradas por estado.",
            parameters_json_schema={
                "type": "object",
                "properties": {
                    "estado": {"type": "string", "enum": ["pendiente", "recibida", "cancelada"]},
                },
            },
        ),
        types.FunctionDeclaration(
            name="detalle_compra",
            description="Muestra el detalle de una compra específica con sus ítems.",
            parameters_json_schema={
                "type": "object",
                "properties": {"compra_id": {"type": "integer"}},
                "required": ["compra_id"],
            },
        ),
        types.FunctionDeclaration(
            name="crear_compra",
            description="Crea una nueva orden de compra a proveedor en estado pendiente.",
            parameters_json_schema={
                "type": "object",
                "properties": {
                    "proveedor_id": {"type": "integer", "description": "ID del proveedor. Omitir si es producto propio."},
                    "fecha_compra": {"type": "string", "description": "Fecha en formato AAAA-MM-DD."},
                    "numero_factura": {"type": "string"},
                    "observaciones": {"type": "string"},
                },
                "required": ["fecha_compra"],
            },
        ),
        types.FunctionDeclaration(
            name="eliminar_compra",
            description="Elimina una compra que aún no ha sido recibida.",
            parameters_json_schema={
                "type": "object",
                "properties": {"compra_id": {"type": "integer"}},
                "required": ["compra_id"],
            },
        ),

        # ===== INVENTARIO / KARDEX =====
        types.FunctionDeclaration(
            name="listar_movimientos_inventario",
            description="Lista los movimientos del Kardex (inventario), opcionalmente filtrados por producto o tipo.",
            parameters_json_schema={
                "type": "object",
                "properties": {
                    "producto_id": {"type": "integer"},
                    "tipo": {"type": "string", "enum": [
                        "entrada_compra", "entrada_devolucion",
                        "salida_venta", "salida_merma",
                        "salida_ajuste", "entrada_ajuste",
                    ]},
                },
            },
        ),

        # ===== DASHBOARD =====
        types.FunctionDeclaration(
            name="dashboard_resumen",
            description="Muestra un resumen general del dashboard con KPIs: usuarios, productos, pedidos, ventas, stock, proveedores y compras.",
            parameters_json_schema={"type": "object", "properties": {}},
        ),

        # ===== USUARIOS (listado) =====
        types.FunctionDeclaration(
            name="listar_usuarios",
            description="Lista los usuarios registrados en el sistema.",
            parameters_json_schema={
                "type": "object",
                "properties": {
                    "activo": {"type": "boolean", "description": "Filtrar por activo/inactivo."},
                },
            },
        ),

        # ===== ZONAS DE REPARTO (editar/eliminar) =====
        types.FunctionDeclaration(
            name="editar_zona_reparto",
            description="Edita los datos de una zona de reparto existente por su ID.",
            parameters_json_schema={
                "type": "object",
                "properties": {
                    "zona_id": {"type": "integer"},
                    "nombre": {"type": "string"},
                    "municipio": {"type": "string"},
                    "estado": {"type": "string"},
                    "codigo_postal_inicio": {"type": "string"},
                    "codigo_postal_fin": {"type": "string"},
                    "costo_envio": {"type": "number"},
                    "tiempo_entrega": {"type": "string"},
                    "activo": {"type": "boolean"},
                },
                "required": ["zona_id"],
            },
        ),
        types.FunctionDeclaration(
            name="eliminar_zona_reparto",
            description="Elimina una zona de reparto por su ID.",
            parameters_json_schema={
                "type": "object",
                "properties": {"zona_id": {"type": "integer"}},
                "required": ["zona_id"],
            },
        ),

        # ===== ROLES (crear/editar/eliminar) =====
        types.FunctionDeclaration(
            name="crear_rol",
            description="Crea un nuevo rol de panel administrativo.",
            parameters_json_schema={
                "type": "object",
                "properties": {
                    "nombre": {"type": "string"},
                    "descripcion": {"type": "string"},
                },
                "required": ["nombre"],
            },
        ),
        types.FunctionDeclaration(
            name="editar_rol",
            description="Edita un rol de panel existente por su ID.",
            parameters_json_schema={
                "type": "object",
                "properties": {
                    "rol_id": {"type": "integer"},
                    "nombre": {"type": "string"},
                    "descripcion": {"type": "string"},
                    "activo": {"type": "boolean"},
                },
                "required": ["rol_id"],
            },
        ),
        types.FunctionDeclaration(
            name="eliminar_rol",
            description="Elimina un rol de panel por su ID. No se puede eliminar si tiene usuarios asignados.",
            parameters_json_schema={
                "type": "object",
                "properties": {"rol_id": {"type": "integer"}},
                "required": ["rol_id"],
            },
        ),

        # ===== TOKENS =====
        types.FunctionDeclaration(
            name="listar_tokens_verificacion",
            description="Lista los tokens de verificación de usuarios.",
            parameters_json_schema={"type": "object", "properties": {}},
        ),
        types.FunctionDeclaration(
            name="listar_tokens_recuperacion",
            description="Lista los tokens de recuperación de contraseña.",
            parameters_json_schema={
                "type": "object",
                "properties": {
                    "usados": {"type": "boolean", "description": "Filtrar por usados/no usados."},
                },
            },
        ),

        # ===== DIRECCIONES DE ENVÍO =====
        types.FunctionDeclaration(
            name="listar_direcciones_envio",
            description="Lista las direcciones de envío registradas por los usuarios.",
            parameters_json_schema={
                "type": "object",
                "properties": {
                    "usuario": {"type": "string", "description": "Filtrar por nombre de usuario."},
                },
            },
        ),

        # ===== AYUDA =====
        types.FunctionDeclaration(
            name="ayuda_admin",
            description="Explica qué puede hacer el asistente de administración. Úsala si el mensaje no encaja en ninguna otra función.",
            parameters_json_schema={"type": "object", "properties": {}},
        ),
    ]
    return types.Tool(function_declarations=declaraciones)


INSTRUCCION_SISTEMA_ADMIN = (
    "Eres el asistente interno de administración de Agrivale, una tienda en línea de productos "
    "agrícolas. Hablas con el ADMINISTRADOR del sitio, no con un cliente. Tu trabajo es ejecutar "
    "operaciones de gestión: crear/editar/eliminar productos y categorías, subir imágenes de "
    "productos, gestionar stock, cambiar estados de pedidos, resolver cancelaciones, gestionar "
    "entregas y pagos, aprobar o responder reseñas, y consultar o administrar usuarios. Puedes operar "
    "un pedido completo (pago, preparación y guía) con procesar_pedido, o cambiar varios pedidos "
    "enumerados con actualizar_pedidos_lote. "
    "SIEMPRE debes responder llamando a una función, nunca solo con texto. "
    "Nunca llames crear_producto: el servidor gestiona las altas con un flujo guiado y confirmación explícita. "
    "Si el administrador adjunta una imagen y menciona un producto, usa subir_imagen_producto. "
    "Si menciona un pedido por número (ej. 'pedido 12', '#12'), usa ese número exacto. "
    "Si el mensaje pide algo destructivo (eliminar producto, eliminar categoría), procede igual "
    "ya que el usuario es el administrador con autoridad total sobre el sitio. "
    "Puedes exportar reportes de ventas o productos más vendidos en PDF o Excel usando exportar_reportes. "
    "Si el mensaje no encaja en ninguna función, usa ayuda_admin."
    "\n\n"
    "A continuación tienes el conocimiento detallado del Panel Administrativo de Agrivale. "
    "Úsalo para responder preguntas del administrador sobre cómo usar cada sección, qué campos "
    "tiene cada formulario, qué URLs usar, o cuál es el ciclo de vida de los procesos.\n"
    + CONOCIMIENTO_PANEL_ADMIN
)
