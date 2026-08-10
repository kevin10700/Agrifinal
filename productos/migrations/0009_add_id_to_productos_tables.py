from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('productos', '0008_rename_id_usuario_to_id'),
    ]

    operations = [
        # Agregar columna id a productos_categoria
        migrations.RunSQL(
            "ALTER TABLE productos_categoria ADD COLUMN id INT AUTO_INCREMENT PRIMARY KEY;",
            reverse_sql="ALTER TABLE productos_categoria DROP COLUMN id;",
        ),
        # Agregar columna id a productos_producto
        migrations.RunSQL(
            "ALTER TABLE productos_producto ADD COLUMN id INT AUTO_INCREMENT PRIMARY KEY;",
            reverse_sql="ALTER TABLE productos_producto DROP COLUMN id;",
        ),
        # Agregar columna id a productos_favorito
        migrations.RunSQL(
            "ALTER TABLE productos_favorito ADD COLUMN id INT AUTO_INCREMENT PRIMARY KEY;",
            reverse_sql="ALTER TABLE productos_favorito DROP COLUMN id;",
        ),
    ]
