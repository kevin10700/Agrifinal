import os
import requests
from django.conf import settings
from django.core.exceptions import ValidationError

ENVIA_API_KEY = getattr(settings, "ENVIA_API_KEY", os.getenv("ENVIA_API_KEY", ""))
IS_SANDBOX = str(getattr(settings, "ENVIA_SANDBOX", os.getenv("ENVIA_SANDBOX", "True"))).lower() in ("true", "1", "t")

# Endpoints oficiales de Envia.com (Sandbox vs Producción)
BASE_URL_QUERIES = "https://queries-test.envia.com" if IS_SANDBOX else "https://queries.envia.com"
BASE_URL_SHIPPING = "https://api-test.envia.com" if IS_SANDBOX else "https://api.envia.com"


class EnviaAPIError(Exception):
    def __init__(self, message, status_code=502, response_data=None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data


def _headers():
    return {
        "Authorization": f"Bearer {ENVIA_API_KEY}",
        "Content-Type": "application/json",
    }


def cotizar_envio(origen, destino, paquete):
    """
    Consulta las tarifas disponibles en Envia.com
    """
    url = f"{BASE_URL_QUERIES}/rate"
    payload = {
        "origin": origen,
        "destination": destino,
        "packages": [paquete] if isinstance(paquete, dict) else paquete,
        "shipment": {
            "carrier": "fedex", # Puedes omitir o cambiar el carrier por defecto
            "type": 1
        }
    }

    try:
        response = requests.post(url, json=payload, headers=_headers(), timeout=10)
        data = response.json()

        if response.status_code != 200 or "data" not in data:
            raise EnviaAPIError(
                message=data.get("message", "Error al cotizar con Envia"),
                status_code=response.status_code,
                response_data=data
            )
        return data["data"]

    except requests.RequestException as e:
        raise EnviaAPIError(f"Error de conexión con Envia: {str(e)}")


def crear_envio(pedido, carrier, service):
    """
    Genera la guía de envío en Envia.com
    """
    url = f"{BASE_URL_SHIPPING}/ship/generate"
    # Lógica básica para armar el payload con los datos del pedido...
    payload = {
        "origin": {
            "name": "Agrivale Store",
            "company": "Agrivale",
            "email": "contacto@agrivale.com",
            "phone": "5555555555",
            "street": "Av Principal",
            "number": "123",
            "district": "Centro",
            "city": "Toluca",
            "state": "MEX",
            "country": "MX",
            "postalCode": "50000"
        },
        "destination": {
            "name": pedido.id_usuario.get_full_name() or "Cliente",
            "email": pedido.id_usuario.email,
            "phone": getattr(pedido, "telefono", "5555555555"),
            "street": pedido.direccion,
            "number": "1",
            "district": "Centro",
            "city": pedido.ciudad,
            "state": pedido.estado,
            "country": "MX",
            "postalCode": pedido.codigo_postal
        },
        "packages": [
            {
                "content": f"Pedido #{pedido.id_pedido}",
                "amount": 1,
                "type": "box",
                "weight": 1,
                "length": 10,
                "width": 10,
                "height": 10
            }
        ],
        "shipment": {
            "carrier": carrier,
            "service": service,
            "type": 1
        }
    }

    try:
        response = requests.post(url, json=payload, headers=_headers(), timeout=10)
        data = response.json()

        if response.status_code not in (200, 201) or "data" not in data:
            raise EnviaAPIError(
                message=data.get("message", "Error al generar la guía en Envia"),
                status_code=response.status_code,
                response_data=data
            )
        
        # Formatear la respuesta de la guía
        guia_info = data["data"][0] if isinstance(data["data"], list) else data["data"]
        return {
            "tracking_number": guia_info.get("trackingNumber"),
            "carreir": carrier,
            "label_url": guia_info.get("label")
        }

    except requests.RequestException as e:
        raise EnviaAPIError(f"Error de conexión al generar la guía: {str(e)}")