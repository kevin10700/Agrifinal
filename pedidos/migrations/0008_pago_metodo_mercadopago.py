from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("pedidos", "0007_alter_entrega_estado"),
    ]

    operations = [
        migrations.AlterField(
            model_name="pago",
            name="metodo",
            field=models.CharField(
                choices=[
                    ("transferencia", "Transferencia Bancaria"),
                    ("oxxo", "Pago en OXXO"),
                    ("tarjeta", "Stripe"),
                    ("mercadopago", "Mercado Pago"),
                ],
                default="transferencia",
                max_length=20,
            ),
        ),
    ]
