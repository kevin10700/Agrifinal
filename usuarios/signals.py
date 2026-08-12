from django.contrib.auth.signals import user_logged_out, user_logged_in
from django.dispatch import receiver
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


@receiver(user_logged_out)
def clear_user_session(sender, request, user, **kwargs):
    """
    Limpiar session_key del usuario al cerrar sesión
    Se ejecuta automáticamente cuando el usuario hace logout
    """
    if user:
        try:
            user.session_key = None
            user.last_session_update = None
            user.save(update_fields=['session_key', 'last_session_update'])
            logger.info(f"✅ Session key limpiado para usuario {user.username}")
        except Exception as e:
            logger.error(f"❌ Error al limpiar session_key para {user.username}: {e}")


@receiver(user_logged_in)
def set_user_session(sender, request, user, **kwargs):
    """
    Guardar session_key al iniciar sesión (respaldo por si la vista no lo hace)
    """
    if user and request:
        try:
            user.session_key = request.session.session_key
            user.last_session_update = timezone.now()
            user.save(update_fields=['session_key', 'last_session_update'])
            logger.info(f"✅ Session key guardado para {user.username}")
        except Exception as e:
            logger.error(f"❌ Error al guardar session_key para {user.username}: {e}")