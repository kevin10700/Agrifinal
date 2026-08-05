"""Reglas de reparto propio, independientes de la integración con Envia."""

from shipping.models import ZonaReparto


def buscar_zona_local(codigo_postal):
    """Devuelve los datos de la zona local activa que cubre el CP, o ``None``."""
    codigo = str(codigo_postal or "").strip()
    if not codigo.isdigit() or len(codigo) != 5:
        return None

    codigo_numero = int(codigo)
    for zona in ZonaReparto.objects.filter(activo=True).order_by("codigo_postal_inicio"):
        if int(zona.codigo_postal_inicio) <= codigo_numero <= int(zona.codigo_postal_fin):
            return {
                "zona": zona,
                "costo": zona.costo_envio,
                "tiempo_entrega": zona.tiempo_entrega,
            }
    return None
