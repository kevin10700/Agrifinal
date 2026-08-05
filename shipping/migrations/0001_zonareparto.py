from decimal import Decimal

from django.db import migrations, models


def crear_zonas_iniciales(apps, schema_editor):
    ZonaReparto = apps.get_model("shipping", "ZonaReparto")
    zonas = [
        ("Calimaya", "Calimaya", "Estado de México", "52200", "52230", Decimal("0.00"), "Mismo día"),
        ("Metepec", "Metepec", "Estado de México", "52140", "52189", Decimal("60.00"), "24 horas"),
        ("Toluca", "Toluca", "Estado de México", "50000", "50299", Decimal("80.00"), "24 horas"),
        ("Tenango del Valle", "Tenango del Valle", "Estado de México", "52300", "52349", Decimal("90.00"), "24 horas"),
    ]
    for nombre, municipio, estado, inicio, fin, costo, tiempo in zonas:
        ZonaReparto.objects.get_or_create(
            nombre=nombre,
            defaults={
                "municipio": municipio,
                "estado": estado,
                "codigo_postal_inicio": inicio,
                "codigo_postal_fin": fin,
                "costo_envio": costo,
                "tiempo_entrega": tiempo,
                "activo": True,
            },
        )


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="ZonaReparto",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nombre", models.CharField(max_length=120, unique=True)),
                ("municipio", models.CharField(max_length=100)),
                ("estado", models.CharField(max_length=100)),
                ("codigo_postal_inicio", models.CharField(max_length=5)),
                ("codigo_postal_fin", models.CharField(max_length=5)),
                ("costo_envio", models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ("tiempo_entrega", models.CharField(max_length=100)),
                ("activo", models.BooleanField(default=True)),
            ],
            options={
                "verbose_name": "Zona de reparto",
                "verbose_name_plural": "Zonas de reparto",
                "ordering": ("estado", "municipio", "codigo_postal_inicio"),
            },
        ),
        migrations.RunPython(crear_zonas_iniciales, migrations.RunPython.noop),
    ]
