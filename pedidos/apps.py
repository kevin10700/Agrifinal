from django.apps import AppConfig


class PedidosConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'pedidos'

    def ready(self):
        # Esta importación le dice a Django que escuche las señales que creamos
        import pedidos.signals