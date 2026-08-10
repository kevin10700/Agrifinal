from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pedidos', '0008_rename_id_usuario_to_id'),
    ]

    operations = [
        # Agregar columna id sin eliminar datos existentes
        migrations.RunSQL(
            "ALTER TABLE pedidos_notificacion ADD COLUMN id INT AUTO_INCREMENT PRIMARY KEY;",
            reverse_sql="ALTER TABLE pedidos_notificacion DROP COLUMN id;",
        ),
    ]
