# usuarios/migrations/0008_migrar_a_id_estandar.py
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [
        ('usuarios', '0007_usuario_activo'),
    ]

    operations = [
        # 1. Agregar campo 'id' temporal (para no perder datos)
        migrations.AddField(
            model_name='usuario',
            name='id_temp',
            field=models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID', null=True),
        ),
        
        # 2. Copiar los valores de id_usuario a id_temp
        migrations.RunSQL(
            sql='UPDATE usuarios_usuario SET id_temp = id_usuario;',
            reverse_sql='UPDATE usuarios_usuario SET id_usuario = id_temp;',
        ),
        
        # 3. Eliminar la clave primaria actual (id_usuario)
        migrations.RemoveField(
            model_name='usuario',
            name='id_usuario',
        ),
        
        # 4. Cambiar el nombre de id_temp a id
        migrations.RenameField(
            model_name='usuario',
            old_name='id_temp',
            new_name='id',
        ),
        
        # 5. Actualizar las claves foráneas a 'usuario_id'
        migrations.AlterField(
            model_name='direccionenvio',
            name='usuario',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='direcciones',
                to='usuarios.usuario',
                db_column='usuario_id',
            ),
        ),
        migrations.AlterField(
            model_name='tokenverificacion',
            name='usuario',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='tokens_verificacion',
                to='usuarios.usuario',
                db_column='usuario_id',
            ),
        ),
        migrations.AlterField(
            model_name='tokenrecuperacion',
            name='usuario',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='tokens_recuperacion',
                to='usuarios.usuario',
                db_column='usuario_id',
            ),
        ),
        migrations.AlterField(
            model_name='refreshtoken',
            name='usuario',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='refresh_tokens',
                to='usuarios.usuario',
            ),
        ),
    ]