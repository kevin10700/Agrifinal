from django.core.management.base import BaseCommand
from usuarios.models import Usuario
from admin_panel.models import UsuarioPanel, RolPanel
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Diagnostica el acceso de usuarios al panel administrativo'

    def add_arguments(self, parser):
        parser.add_argument(
            '--usuario',
            type=str,
            help='Username del usuario a diagnosticar (opcional)'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n=== DIAGNÓSTICO DE ACCESO AL PANEL ===\n'))

        if options['usuario']:
            usuarios = Usuario.objects.filter(username=options['usuario'])
            if not usuarios.exists():
                self.stdout.write(self.style.ERROR(f'Usuario "{options["usuario"]}" no encontrado'))
                return
        else:
            usuarios = Usuario.objects.filter(is_active=True)

        self.stdout.write(f'Total de usuarios activos: {usuarios.count()}\n')

        for usuario in usuarios:
            self.stdout.write(f'\n{"="*60}')
            self.stdout.write(f'Usuario: {usuario.username}')
            self.stdout.write(f'Nombre: {usuario.nombre_completo}')
            self.stdout.write(f'Email: {usuario.correo}')
            self.stdout.write(f'Activo: {usuario.is_active}')
            self.stdout.write(f'is_superuser: {usuario.is_superuser}')
            self.stdout.write(f'is_staff: {usuario.is_staff}')

            # Verificar UsuarioPanel
            try:
                usuario_panel = UsuarioPanel.objects.select_related('rol').get(usuario=usuario)
                self.stdout.write(f'\n✅ Tiene UsuarioPanel asignado:')
                self.stdout.write(f'   ID UsuarioPanel: {usuario_panel.id}')
                
                if usuario_panel.rol:
                    self.stdout.write(f'   Rol: {usuario_panel.rol.nombre}')
                    self.stdout.write(f'   Rol activo: {usuario_panel.rol.activo}')
                    self.stdout.write(f'   Fecha asignación: {usuario_panel.fecha_asignacion}')
                    
                    if usuario_panel.rol.activo:
                        self.stdout.write(self.style.SUCCESS('   ✅ ACCESO AL PANEL: PERMITIDO'))
                    else:
                        self.stdout.write(self.style.WARNING('   ⚠️  ACCESO AL PANEL: DENEGADO (rol inactivo)'))
                else:
                    self.stdout.write(self.style.WARNING('   ⚠️  Rol: Sin rol asignado'))
                    self.stdout.write(self.style.WARNING('   ⚠️  ACCESO AL PANEL: DENEGADO'))
            
            except UsuarioPanel.DoesNotExist:
                self.stdout.write(self.style.WARNING('\n⚠️  No tiene UsuarioPanel asignado'))
                
                if usuario.is_superuser:
                    self.stdout.write(self.style.SUCCESS('   ✅ ACCESO AL PANEL: PERMITIDO (es superuser)'))
                else:
                    self.stdout.write(self.style.ERROR('   ❌ ACCESO AL PANEL: DENEGADO'))
            
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'\n❌ Error al verificar: {str(e)}'))
                logger.error(f"Error al diagnosticar usuario {usuario.username}: {str(e)}")

        # Mostrar resumen de roles
        self.stdout.write(f'\n{"="*60}')
        self.stdout.write(self.style.SUCCESS('\n=== ROLES DISPONIBLES ===\n'))
        
        roles = RolPanel.objects.filter(activo=True)
        if roles.exists():
            for rol in roles:
                usuarios_con_rol = UsuarioPanel.objects.filter(rol=rol).count()
                self.stdout.write(f'• {rol.nombre}: {usuarios_con_rol} usuario(s)')
        else:
            self.stdout.write(self.style.WARNING('No hay roles activos disponibles'))

        roles_inactivos = RolPanel.objects.filter(activo=False).count()
        if roles_inactivos > 0:
            self.stdout.write(f'\n{roles_inactivos} rol(es) inactivo(s)')

        self.stdout.write(f'\n{"="*60}')
        self.stdout.write(self.style.SUCCESS('\n=== RESUMEN ===\n'))
        
        total_usuarios = Usuario.objects.filter(is_active=True).count()
        superusers = Usuario.objects.filter(is_active=True, is_superuser=True).count()
        usuarios_con_panel = UsuarioPanel.objects.filter(rol__activo=True).count()
        
        self.stdout.write(f'Total usuarios activos: {total_usuarios}')
        self.stdout.write(f'Superusers: {superusers}')
        self.stdout.write(f'Usuarios con acceso al panel: {usuarios_con_panel}')
        self.stdout.write(f'Sin acceso al panel: {total_usuarios - superusers - usuarios_con_panel}')
        self.stdout.write('')
