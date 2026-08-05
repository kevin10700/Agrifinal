"""Template tags para el panel de envíos."""
from django import template
from shipping.models import ZonaReparto

register = template.Library()


@register.simple_tag
def zona_reparto(codigo_postal):
    """Devuelve la ZonaReparto que cubre el código postal dado, o None."""
    codigo = str(codigo_postal or "").strip()
    if not codigo.isdigit() or len(codigo) != 5:
        return None
    try:
        return ZonaReparto.objects.filter(
            activo=True,
            codigo_postal_inicio__lte=codigo,
            codigo_postal_fin__gte=codigo,
        ).first()
    except Exception:
        return None
