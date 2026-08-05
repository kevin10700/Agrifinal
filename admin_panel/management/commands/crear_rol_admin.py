from django.core.management.base import BaseCommand
from admin_panel.models import RolPanel


class Command(BaseCommand):
    help = 'Crea el rol de Administrador por defecto para el Panel Administrativo'

    def handle(self, *args, **kwargs):
        # Verificar si ya existe el rol
        rol_admin, created = RolPanel.objects.get_or_create(
            nombre='Administrador',
            defaults={
                'descripcion': 'Rol con todos los permisos para gestionar el panel administrativo',
                'activo': True,
                'puede_gestionar_productos': True,
                'puede_gestionar_pedidos': True,
                'puede_gestionar_clientes': True,
                'puede_gestionar_proveedores': True,
                'puede_gestionar_compras': True,
                'puede_gestionar_pagos': True,
                'puede_gestionar_envios': True,
                'puede_gestionar_inventario': True,
                'puede_gestionar_direcciones_envio': True,
                'puede_ver_reportes': True,
                'puede_ver_dashboard': True,
                'puede_gestionar_configuracion': True,
            }
        )

        if created:
            self.stdout.write(
                self.style.SUCCESS(f'✓ Rol "{rol_admin.nombre}" creado exitosamente')
            )
        else:
            self.stdout.write(
                self.style.WARNING(f'⚠ El rol "{rol_admin.nombre}" ya existe')
            )

        self.stdout.write(
            self.style.SUCCESS('\n✓ Proceso completado. Ahora puedes asignar el rol a los usuarios desde el Django Admin.')
        )