from django.apps import AppConfig


class UsuariosConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'usuarios'

    def ready(self):
        """
        Registrar señales cuando la aplicación esté lista
        """
        import usuarios.signals  # ✅ Importar las señales
        


