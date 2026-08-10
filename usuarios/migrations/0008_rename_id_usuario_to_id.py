# usuarios/migrations/0008_rename_id_usuario_to_id.py
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0007_usuario_activo'),
    ]

    operations = [
        # Renombrar la columna id_usuario a id en la tabla usuarios_usuario
        # Esto evita el conflicto con el campo auto-generado de AbstractUser
        # También renombramos todas las columnas FK que apuntan a id_usuario
        migrations.RunSQL(
            sql="""
                -- Renombrar PK en tabla usuarios
                ALTER TABLE usuarios_usuario 
                CHANGE COLUMN id_usuario id INT AUTO_INCREMENT PRIMARY KEY;
                
                -- Renombrar columnas FK en otras tablas
                ALTER TABLE admin_panel_rolpanel 
                    CHANGE COLUMN id_usuario usuario_id INT;
                ALTER TABLE admin_panel_movimiento_inventario 
                    CHANGE COLUMN id_usuario id INT;
                ALTER TABLE admin_panel_historial_producto 
                    CHANGE COLUMN id_usuario id INT;
                ALTER TABLE usuarios_direccion_envio 
                    CHANGE COLUMN id_usuario id INT;
                ALTER TABLE usuarios_token_verificacion 
                    CHANGE COLUMN id_usuario id INT;
                ALTER TABLE usuarios_token_recuperacion 
                    CHANGE COLUMN id_usuario id INT;
                ALTER TABLE usuarios_refresh_token 
                    CHANGE COLUMN id_usuario id INT;
                ALTER TABLE pedidos_pedido 
                    CHANGE COLUMN id_usuario id INT;
                ALTER TABLE pedidos_carritoitem 
                    CHANGE COLUMN id_usuario id INT;
                ALTER TABLE pedidos_notificacion 
                    CHANGE COLUMN id_usuario id INT;
                ALTER TABLE pedidos_comentarioproducto 
                    CHANGE COLUMN id_usuario id INT;
                ALTER TABLE productos_favorito 
                    CHANGE COLUMN id_usuario id INT;
            """,
            reverse_sql="""
                -- Revertir: renombrar id a id_usuario
                ALTER TABLE usuarios_usuario 
                    CHANGE COLUMN id id_usuario INT AUTO_INCREMENT PRIMARY KEY;
                
                ALTER TABLE admin_panel_rolpanel 
                    CHANGE COLUMN usuario_id id_usuario INT;
                ALTER TABLE admin_panel_movimiento_inventario 
                    CHANGE COLUMN id id_usuario INT;
                ALTER TABLE admin_panel_historial_producto 
                    CHANGE COLUMN id id_usuario INT;
                ALTER TABLE usuarios_direccion_envio 
                    CHANGE COLUMN id id_usuario INT;
                ALTER TABLE usuarios_token_verificacion 
                    CHANGE COLUMN id id_usuario INT;
                ALTER TABLE usuarios_token_recuperacion 
                    CHANGE COLUMN id id_usuario INT;
                ALTER TABLE usuarios_refresh_token 
                    CHANGE COLUMN id id_usuario INT;
                ALTER TABLE pedidos_pedido 
                    CHANGE COLUMN id id_usuario INT;
                ALTER TABLE pedidos_carritoitem 
                    CHANGE COLUMN id id_usuario INT;
                ALTER TABLE pedidos_notificacion 
                    CHANGE COLUMN id id_usuario INT;
                ALTER TABLE pedidos_comentarioproducto 
                    CHANGE COLUMN id id_usuario INT;
                ALTER TABLE productos_favorito 
                    CHANGE COLUMN id id_usuario INT;
            """,
        ),
    ]