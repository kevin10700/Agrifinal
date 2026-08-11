# shipping/services/envia.py
import os
import requests
from django.conf import settings
from django.core.exceptions import ValidationError

# ==========================================
# CONFIGURACIÓN
# ==========================================

ENVIA_API_TOKEN = getattr(settings, "ENVIA_API_TOKEN", os.getenv("ENVIA_API_TOKEN", ""))
ENVIA_API_URL = getattr(settings, "ENVIA_API_URL", os.getenv("ENVIA_API_URL", "https://api-test.envia.com"))

# URLs para Envia API
BASE_URL_QUOTES = f"{ENVIA_API_URL}/v1/rate"
BASE_URL_SHIPMENT = f"{ENVIA_API_URL}/v1/shipment"


class EnviaAPIError(Exception):
    def __init__(self, message, status_code=502, response_data=None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data


def _headers():
    return {
        "Authorization": f"Bearer {ENVIA_API_TOKEN}",
        "Content-Type": "application/json",
    }


def _get_test_rates():
    """Devuelve datos de prueba para cuando Envia no está disponible"""
    return [
        {"carrierName": "DHL", "serviceDescription": "Express", "totalPrice": 150.00, "deliveryEstimate": 2},
        {"carrierName": "Estafeta", "serviceDescription": "Terrestre", "totalPrice": 80.00, "deliveryEstimate": 4},
        {"carrierName": "FedEx", "serviceDescription": "Económico", "totalPrice": 120.00, "deliveryEstimate": 3},
        {"carrierName": "Redpack", "serviceDescription": "Express", "totalPrice": 95.00, "deliveryEstimate": 2}
    ]


def cotizar_envio(origen, destino, paquete):
    """
    Consulta las tarifas disponibles en Envia.com
    """
    # Si no hay token, devolver datos de prueba
    if not ENVIA_API_TOKEN:
        print("⚠️ ENVIA_API_TOKEN no configurado. Usando datos de prueba.")
        return _get_test_rates()
    
    try:
        # Construir payload según la API de Envia
        payload = {
            "origin": {
                "name": origen.get("name", "Agrivale"),
                "company": origen.get("company", "Agrivale"),
                "email": origen.get("email", "contacto@agrivale.com"),
                "phone": origen.get("phone", "5555555555"),
                "address": {
                    "street": origen.get("street", ""),
                    "number": origen.get("number", ""),
                    "district": origen.get("district", ""),
                    "city": origen.get("city", ""),
                    "state": origen.get("state", "MEX"),
                    "country": origen.get("country", "MX"),
                    "postal_code": origen.get("postalCode", "")
                }
            },
            "destination": {
                "name": destino.get("nombre", "Cliente"),
                "company": destino.get("company", ""),
                "email": destino.get("email", ""),
                "phone": destino.get("telefono", ""),
                "address": {
                    "street": destino.get("calle", ""),
                    "number": destino.get("numero_exterior", ""),
                    "district": destino.get("colonia", ""),
                    "city": destino.get("ciudad", ""),
                    "state": destino.get("estado", "MEX"),
                    "country": destino.get("pais", "MX"),
                    "postal_code": destino.get("codigo_postal", "")
                }
            },
            "packages": [paquete] if isinstance(paquete, dict) else paquete
        }
        
        print(f"📦 Cotizando envío a Envia...")
        
        response = requests.post(
            BASE_URL_QUOTES, 
            json=payload, 
            headers=_headers(), 
            timeout=30
        )
        
        print(f"📡 Envia respondió con status: {response.status_code}")
        
        # Si la API falla, devolver datos de prueba
        if response.status_code != 200:
            print(f"⚠️ Envia falló: {response.text}")
            return _get_test_rates()
        
        data = response.json()
        rates = data.get("rates", [])
        
        if not rates:
            print("⚠️ No hay rates disponibles")
            return _get_test_rates()
        
        # Formatear rates para el frontend
        formatted_rates = []
        for rate in rates:
            formatted_rates.append({
                "carrierName": rate.get("carrier", "Desconocido"),
                "serviceDescription": rate.get("service", "Estándar"),
                "totalPrice": float(rate.get("total", 0)),
                "deliveryEstimate": rate.get("delivery_days", 0)
            })
        
        return formatted_rates
        
    except requests.RequestException as e:
        print(f"❌ Error de conexión con Envia: {e}")
        return _get_test_rates()
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        return _get_test_rates()


def crear_envio(payload, carrier=None, service=None):
    """
    Genera la guía de envío en Envia.com
    
    Args:
        payload: Diccionario con los datos del envío (desde el frontend)
        carrier: Transportista seleccionado (opcional)
        service: Servicio seleccionado (opcional)
    """
    # Si no hay token, devolver datos de prueba
    if not ENVIA_API_TOKEN:
        print("⚠️ ENVIA_API_TOKEN no configurado. Usando datos de prueba.")
        return {
            "trackingNumber": f"TEST-{hash(str(payload)) % 1000000:06d}",
            "label": "/media/etiquetas/prueba.pdf"
        }
    
    try:
        # Extraer datos del payload
        destino = payload.get("destino", {})
        paquete = payload.get("paquete", {})
        
        # Construir payload para crear envío
        request_payload = {
            "origin": {
                "name": "Agrivale Store",
                "company": "Agrivale",
                "email": "contacto@agrivale.com",
                "phone": "5555555555",
                "address": {
                    "street": "Galeana 4",
                    "number": "4",
                    "district": "Centro",
                    "city": "Calimaya",
                    "state": "MEX",
                    "country": "MX",
                    "postal_code": "52210"
                }
            },
            "destination": {
                "name": destino.get("nombre", "Cliente"),
                "email": destino.get("email", "cliente@email.com"),
                "phone": destino.get("telefono", "5555555555"),
                "address": {
                    "street": destino.get("calle", ""),
                    "number": destino.get("numero_exterior", ""),
                    "district": destino.get("colonia", ""),
                    "city": destino.get("ciudad", ""),
                    "state": destino.get("estado", "MEX"),
                    "country": destino.get("pais", "MX"),
                    "postal_code": destino.get("codigo_postal", "")
                }
            },
            "packages": [
                {
                    "content": paquete.get("content", "Productos Agrivale"),
                    "amount": paquete.get("amount", 1),
                    "type": paquete.get("type", "box"),
                    "weight": float(paquete.get("weight", 1.0)),
                    "length": float(paquete.get("length", 20.0)),
                    "width": float(paquete.get("width", 15.0)),
                    "height": float(paquete.get("height", 10.0))
                }
            ],
            "shipment": {
                "carrier": carrier or "dhl",
                "service": service or "express",
                "type": 1
            }
        }
        
        print(f"📦 Creando envío en Envia...")
        
        response = requests.post(
            BASE_URL_SHIPMENT,
            json=request_payload,
            headers=_headers(),
            timeout=30
        )
        
        print(f"📡 Envia respondió con status: {response.status_code}")
        
        if response.status_code not in (200, 201):
            print(f"⚠️ Envia falló: {response.text}")
            return {
                "trackingNumber": f"FALLBACK-{hash(str(payload)) % 1000000:06d}",
                "label": "/media/etiquetas/fallback.pdf"
            }
        
        data = response.json()
        
        # Procesar respuesta
        shipment_data = data.get("data", [])
        if isinstance(shipment_data, list) and shipment_data:
            shipment_data = shipment_data[0]
        
        return {
            "trackingNumber": shipment_data.get("trackingNumber", f"ENV-{hash(str(payload)) % 1000000:06d}"),
            "label": shipment_data.get("label", "/media/etiquetas/generada.pdf"),
            "detalle": data
        }
        
    except requests.RequestException as e:
        print(f"❌ Error de conexión: {e}")
        return {
            "trackingNumber": f"ERROR-{hash(str(payload)) % 1000000:06d}",
            "label": "/media/etiquetas/error.pdf"
        }
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        raise EnviaAPIError(f"Error al crear envío: {str(e)}")