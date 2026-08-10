from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('admin_panel', '0008_rename_id_usuario_to_id'),
    ]

    operations = [
        # Agregar columna id a admin_panel_rolpanel
        migrations.RunSQL(
            "ALTER TABLE admin_panel_rolpanel ADD COLUMN id INT AUTO_INCREMENT PRIMARY KEY;",
            reverse_sql="ALTER TABLE admin_panel_rolpanel DROP COLUMN id;",
        ),
        # Agregar columna id a admin_panel_proveedor
        migrations.RunSQL(
            "ALTER TABLE admin_panel_proveedor ADD COLUMN id INT AUTO_INCREMENT PRIMARY KEY;",
            reverse_sql="ALTER TABLE admin_panel_proveedor DROP COLUMN id;",
        ),
        # Agregar columna id a admin_panel_compra
        migrations.RunSQL(
            "ALTER TABLE admin_panel_compra ADD COLUMN id INT AUTO_INCREMENT PRIMARY KEY;",
            reverse_sql="ALTER TABLE admin_panel_compra DROP COLUMN id;",
        ),
        # Agregar columna id a admin_panel_itemcompra
        migrations.RunSQL(
            "ALTER TABLE admin_panel_itemcompra ADD COLUMN id INT AUTO_INCREMENT PRIMARY KEY;",
            reverse_sql="ALTER TABLE admin_panel_itemcompra DROP COLUMN id;",
        ),
        # Agregar columna id a admin_panel_movimientoinventario
        migrations.RunSQL(
            "ALTER TABLE admin_panel_movimientoinventario ADD COLUMN id INT AUTO_INCREMENT PRIMARY KEY;",
            reverse_sql="ALTER TABLE admin_panel_movimientoinventario DROP COLUMN id;",
        ),
        # Agregar columna id a admin_panel_historialproducto
        migrations.RunSQL(
            "ALTER TABLE admin_panel_historialproducto ADD COLUMN id INT AUTO_INCREMENT PRIMARY KEY;",
            reverse_sql="ALTER TABLE admin_panel_historialproducto DROP COLUMN id;",
        ),
    ]
