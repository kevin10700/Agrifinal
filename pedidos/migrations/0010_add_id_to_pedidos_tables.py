from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pedidos', '0009_add_id_to_notificacion'),
    ]

    operations = [
        # Agregar columna id a pedidos_pedido
        migrations.RunSQL(
            "ALTER TABLE pedidos_pedido ADD COLUMN id INT AUTO_INCREMENT PRIMARY KEY;",
            reverse_sql="ALTER TABLE pedidos_pedido DROP COLUMN id;",
        ),
        # Agregar columna id a pedidos_itempedido
        migrations.RunSQL(
            "ALTER TABLE pedidos_itempedido ADD COLUMN id INT AUTO_INCREMENT PRIMARY KEY;",
            reverse_sql="ALTER TABLE pedidos_itempedido DROP COLUMN id;",
        ),
        # Agregar columna id a pedidos_carritoitem
        migrations.RunSQL(
            "ALTER TABLE pedidos_carritoitem ADD COLUMN id INT AUTO_INCREMENT PRIMARY KEY;",
            reverse_sql="ALTER TABLE pedidos_carritoitem DROP COLUMN id;",
        ),
        # Agregar columna id a pedidos_entrega
        migrations.RunSQL(
            "ALTER TABLE pedidos_entrega ADD COLUMN id INT AUTO_INCREMENT PRIMARY KEY;",
            reverse_sql="ALTER TABLE pedidos_entrega DROP COLUMN id;",
        ),
        # Agregar columna id a pedidos_comentarioproducto
        migrations.RunSQL(
            "ALTER TABLE pedidos_comentarioproducto ADD COLUMN id INT AUTO_INCREMENT PRIMARY KEY;",
            reverse_sql="ALTER TABLE pedidos_comentarioproducto DROP COLUMN id;",
        ),
        # Agregar columna id a pedidos_pago
        migrations.RunSQL(
            "ALTER TABLE pedidos_pago ADD COLUMN id INT AUTO_INCREMENT PRIMARY KEY;",
            reverse_sql="ALTER TABLE pedidos_pago DROP COLUMN id;",
        ),
    ]
