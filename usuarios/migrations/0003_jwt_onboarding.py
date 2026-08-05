from django.db import migrations, models
import django.db.models.deletion

def marcar_usuarios_existentes(apps, schema_editor):
    apps.get_model('usuarios', 'Usuario').objects.update(is_new_user=False)

class Migration(migrations.Migration):
    dependencies = [('usuarios', '0002_alter_tokenrecuperacion_token_and_more')]
    operations = [
        migrations.AddField(model_name='usuario', name='is_new_user', field=models.BooleanField(default=True)),
        migrations.RunPython(marcar_usuarios_existentes, migrations.RunPython.noop),
        migrations.AddField(model_name='usuario', name='onboarding_completado', field=models.BooleanField(default=False)),
        migrations.CreateModel(name='RefreshToken', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('jti', models.CharField(db_index=True, max_length=64, unique=True)),
            ('expira_en', models.DateTimeField()), ('revocado_en', models.DateTimeField(blank=True, null=True)),
            ('creado_en', models.DateTimeField(auto_now_add=True)),
            ('usuario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='refresh_tokens', to='usuarios.usuario')),
        ], options={'db_table': 'usuarios_refresh_token'}),
    ]
