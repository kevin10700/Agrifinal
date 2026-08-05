from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('productos', '0001_initial')]

    operations = [
        migrations.CreateModel(
            name='ProductoAgricola',
            fields=[
                ('id', models.IntegerField(primary_key=True, serialize=False)),
                ('nombre', models.CharField(db_index=True, max_length=255)),
                ('categoria', models.CharField(choices=[('FERTILIZANTES_QUIMICOS', 'Fertilizantes químicos'), ('ABONOS_ORGANICOS', 'Abonos orgánicos'), ('AGROQUIMICOS', 'Agroquímicos'), ('BOMBAS_RIEGO', 'Bombas y riego'), ('HERRAMIENTAS_PLASTICOS', 'Herramientas y plásticos')], db_index=True, max_length=32)),
                ('uso_principal', models.TextField()), ('presentaciones', models.JSONField(default=list)),
                ('precio_base', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('stock', models.IntegerField(default=0)), ('imagen_url', models.URLField(blank=True)), ('activo', models.BooleanField(default=True)),
            ], options={'db_table': 'productos', 'ordering': ['id']},
        ),
    ]
