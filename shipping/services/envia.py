"""Cliente aislado para la Shipping API de Envia."""

from decimal import Decimal

import requests
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction

from pedidos.models import Entrega


class EnviaAPIError(Exception):
    """Error controlado devuelto por la API de Envia."""

    def __init__(self, message, status_code=None, response_data=None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data


def _configuracion():
    token = getattr(settings, "ENVIA_API_TOKEN", "")
    base_url = getattr(settings, "ENVIA_API_URL", "").rstrip("/")
    environment = getattr(settings, "ENVIA_ENVIRONMENT", "test")

    if not token or not base_url:
        raise EnviaAPIError(
            "Falta configurar ENVIA_API_TOKEN o ENVIA_API_URL en el entorno.",
            status_code=503,
        )
    if environment not in {"test", "production"}:
        raise EnviaAPIError(
            "ENVIA_ENVIRONMENT debe ser 'test' o 'production'.", status_code=503
        )
    return token, base_url


def _request(method, path, payload=None):
    token, base_url = _configuracion()
    try:
        session = requests.Session()
        # El entorno local puede definir un proxy de desarrollo inexistente.
        # Envia debe consultarse directamente por HTTPS.
        session.trust_env = False
        response = session.request(
            method,
            f"{base_url}/{path.lstrip('/')}",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            json=payload,
            timeout=20,
        )
    except requests.Timeout as exc:
        raise EnviaAPIError("Envia no respondió a tiempo.") from exc
    except requests.RequestException as exc:
        raise EnviaAPIError("No fue posible conectar con Envia.") from exc

    try:
        response_data = response.json()
    except ValueError:
        response_data = {"detail": response.text}

    if not response.ok:
        message = response_data.get("message") or response_data.get("detail") or (
            "Envia rechazó la solicitud."
        )
        raise EnviaAPIError(message, response.status_code, response_data)
    return response_data


def validar_codigo_postal(codigo_postal):
    """Consulta Geocodes de Envia para completar estado y ciudad de México."""
    if not codigo_postal or not str(codigo_postal).isdigit() or len(str(codigo_postal)) != 5:
        raise ValidationError({"codigo_postal": "Ingresa un código postal mexicano de 5 dígitos."})
    try:
        session = requests.Session()
        session.trust_env = False
        response = session.get(
            f"https://geocodes.envia.com/zipcode/MX/{codigo_postal}", timeout=10
        )
        data = response.json()
    except requests.Timeout as exc:
        raise EnviaAPIError("La validación del código postal tardó demasiado.") from exc
    except (requests.RequestException, ValueError) as exc:
        raise EnviaAPIError("No fue posible validar el código postal.") from exc

    if not response.ok:
        raise ValidationError({"codigo_postal": "No se encontró ese código postal en Envia."})
    # Envia Geocodes mantiene dos formatos de respuesta. El actual para MX
    # devuelve una lista de localidades; el formato documentado devuelve
    # {success, data}. Aceptamos ambos para no romper el checkout.
    if isinstance(data, list):
        location = data[0] if data else None
        if not location:
            raise ValidationError({"codigo_postal": "No se encontró ese código postal en Envia."})
        state = location.get("state", {})
        state_code = state.get("code", {}).get("2digit", "")
        return {
            "codigo_postal": location.get("zip_code", str(codigo_postal)),
            "estado": state.get("name", ""),
            "estado_codigo": state_code,
            "municipio": location.get("locality", ""),
            "colonias": location.get("suburbs", []),
        }
    if not isinstance(data, dict) or not data.get("success") or not data.get("data"):
        raise ValidationError({"codigo_postal": "No se encontró ese código postal en Envia."})
    location = data["data"]
    return {
        "codigo_postal": location.get("zipcode", location.get("postalCode", str(codigo_postal))),
        "estado": location.get("state", ""),
        "estado_codigo": location.get("state", ""),
        "municipio": location.get("city", ""),
        "colonias": location.get("suburbs", []),
    }


def _valor_decimal(value, field_name):
    try:
        value = Decimal(str(value))
    except (TypeError, ValueError, ArithmeticError) as exc:
        raise ValidationError({field_name: "Debe ser un número válido."}) from exc
    
    # 🔥 CORRECCIÓN AQUÍ: Si el valor es 0 o negativo, lo convertimos a 0.01 para evitar el error
    if value <= 0:
        return Decimal("0.01")
    
    return value


def _normalizar_paquete(paquete):
    required = ("peso", "alto", "ancho", "largo")
    missing = [field for field in required if paquete.get(field) in (None, "")]
    if missing:
        raise ValidationError({field: "Este campo es obligatorio." for field in missing})

    peso = _valor_decimal(paquete["peso"], "peso")
    alto = _valor_decimal(paquete["alto"], "alto")
    ancho = _valor_decimal(paquete["ancho"], "ancho")
    largo = _valor_decimal(paquete["largo"], "largo")
    return {
        "type": paquete.get("tipo", "box"),
        "content": paquete.get("contenido", "Productos Agrivale"),
        "amount": int(paquete.get("cantidad", 1)),
        "declaredValue": float(paquete.get("valor_declarado", 0)),
        "lengthUnit": "CM",
        "weightUnit": "KG",
        "weight": float(peso),
        "dimensions": {
            "length": float(largo),
            "width": float(ancho),
            "height": float(alto),
        },
    }


def _normalizar_opciones(response_data):
    rates = response_data.get("data", [])
    if isinstance(rates, dict):
        rates = [rates]
    return [
        {
            "transportista": rate.get("carrier"),
            "servicio": rate.get("service"),
            "precio": rate.get("totalPrice", rate.get("price")),
            "dias_estimados": rate.get(
                "deliveryDays",
                rate.get("estimatedDays", rate.get("days", rate.get("deliveryEstimate"))),
            ),
        }
        for rate in rates
    ]


def cotizar_envio(origen, destino, paquete, transportista=None):
    """Consulta tarifas con origen/destino y un paquete expresados en kg y cm."""
    if origen is None:
        origen = _origen_configurado()
    if not isinstance(origen, dict) or not isinstance(destino, dict):
        raise ValidationError("Origen y destino deben ser objetos JSON.")

    for address_name, address in (("origen", origen), ("destino", destino)):
        missing = [
            key for key in ("pais", "codigo_postal") if not address.get(key)
        ]
        if missing:
            raise ValidationError(
                {f"{address_name}.{key}": "Este campo es obligatorio." for key in missing}
            )

    # La API actual de Envia exige un transportista incluso para cotizar.
    # Se puede reemplazar desde la petición, y DHL es la integración activa
    # de la cuenta de pruebas de Agrivale.
    shipment = {
        "type": 1,
        "carrier": transportista or getattr(settings, "ENVIA_DEFAULT_CARRIER", "dhl"),
    }

    payload = {
        "origin": _direccion_envia(origen),
        "destination": _direccion_envia(destino),
        "packages": [_normalizar_paquete(paquete)],
        "shipment": shipment,
    }
    response_data = _request("POST", "/ship/rate/", payload)
    return {"opciones": _normalizar_opciones(response_data), "respuesta_json": response_data}


def _direccion_envia(direccion):
    """Convierte nombres de campos del proyecto al formato esperado por Envia."""
    estado = direccion.get("estado", "")
    # El checkout muestra el nombre legible del estado, pero Envia requiere
    # el código de dos letras. Esta equivalencia cubre direcciones guardadas
    # antes de que se validara el código postal en pantalla.
    if str(estado).strip().lower() in {"méxico", "mexico", "estado de méxico", "estado de mexico"}:
        estado = "MX"
    return {
        "name": direccion.get("nombre", ""),
        "phone": direccion.get("telefono", ""),
        "street": direccion.get("calle", ""),
        "city": direccion.get("ciudad", direccion.get("municipio", "")),
        "state": estado,
        "country": direccion["pais"],
        "postalCode": direccion["codigo_postal"],
    }


def _origen_configurado():
    values = {
        "nombre": getattr(settings, "ENVIA_ORIGIN_NAME", ""),
        "telefono": getattr(settings, "ENVIA_ORIGIN_PHONE", ""),
        "calle": getattr(settings, "ENVIA_ORIGIN_STREET", ""),
        "ciudad": getattr(settings, "ENVIA_ORIGIN_CITY", ""),
        "estado": getattr(settings, "ENVIA_ORIGIN_STATE", ""),
        "pais": getattr(settings, "ENVIA_ORIGIN_COUNTRY", ""),
        "codigo_postal": getattr(settings, "ENVIA_ORIGIN_POSTAL_CODE", ""),
    }
    environment_names = {
        "nombre": "ENVIA_ORIGIN_NAME",
        "telefono": "ENVIA_ORIGIN_PHONE",
        "calle": "ENVIA_ORIGIN_STREET",
        "ciudad": "ENVIA_ORIGIN_CITY",
        "estado": "ENVIA_ORIGIN_STATE",
        "pais": "ENVIA_ORIGIN_COUNTRY",
        "codigo_postal": "ENVIA_ORIGIN_POSTAL_CODE",
    }
    missing = [environment_names[key] for key, value in values.items() if not value]
    if missing:
        raise EnviaAPIError(
            "Faltan datos de origen de Envia: " + ", ".join(missing) + ".",
            status_code=503,
        )
    return values


def _destino_del_pedido(pedido):
    direccion = pedido.id_direccion_envio
    if not direccion:
        raise EnviaAPIError("El pedido debe tener una dirección de envío guardada.")
    return {
        "nombre": pedido.nombre_receptor or pedido.id_usuario.nombre_completo,
        "telefono": pedido.telefono_contacto or direccion.telefono_contacto,
        "calle": " ".join(
            filter(None, [direccion.calle, direccion.numero_exterior, direccion.numero_interior])
        ),
        "ciudad": direccion.municipio,
        "estado": direccion.estado,
        "pais": direccion.pais,
        "codigo_postal": direccion.codigo_postal,
    }


def _paquetes_del_pedido(pedido):
    lado_estandar = Decimal("20")

    def peso_unitario(producto):
        if producto.peso_kg > 0:
            return producto.peso_kg
        if producto.unidad_medida == "kg":
            return Decimal("1")
        if producto.unidad_medida == "libra":
            return Decimal("0.453592")
        return Decimal("0")

    packages = []
    for item in pedido.items.select_related("id_producto"):
        producto = item.id_producto
        packages.append(
            _normalizar_paquete(
                {
                    "peso": peso_unitario(producto),
                    # Debe coincidir con la cotización: los artículos
                    # heredados sin empaque definido viajan en la caja
                    # estándar hasta que se capturen sus medidas reales.
                    "alto": producto.alto_cm or lado_estandar,
                    "ancho": producto.ancho_cm or lado_estandar,
                    "largo": producto.largo_cm or lado_estandar,
                    "cantidad": item.cantidad,
                    "contenido": producto.nombre,
                    "valor_declarado": item.get_subtotal(),
                }
            )
        )
    if not packages:
        raise EnviaAPIError("El pedido no tiene productos para enviar.")
    return packages


def crear_envio(pedido, transportista, servicio):
    """Genera una etiqueta Envia y persiste sus datos en la entrega del pedido."""
    if not transportista or not servicio:
        raise ValidationError("Transportista y servicio son obligatorios.")

    payload = {
        "origin": _direccion_envia(_origen_configurado()),
        "destination": _direccion_envia(_destino_del_pedido(pedido)),
        "packages": _paquetes_del_pedido(pedido),
        "settings": {
            "printFormat": getattr(settings, "ENVIA_LABEL_FORMAT", ""),
            "printSize": getattr(settings, "ENVIA_LABEL_SIZE", ""),
        },
        "shipment": {"type": 1, "carrier": transportista, "service": servicio},
    }
    if not payload["settings"]["printFormat"] or not payload["settings"]["printSize"]:
        raise EnviaAPIError(
            "Configura ENVIA_LABEL_FORMAT y ENVIA_LABEL_SIZE.", status_code=503
        )

    response_data = _request("POST", "/ship/generate/", payload)
    data = response_data.get("data", [])
    if isinstance(data, list):
        data = data[0] if data else {}
    if not data:
        raise EnviaAPIError("Envia no devolvió datos de la etiqueta.", response_data=response_data)

    tracking_number = data.get("trackingNumber", "")
    price = Decimal(str(data.get("totalPrice") or 0))
    with transaction.atomic():
        entrega, _ = Entrega.objects.select_for_update().get_or_create(id_pedido=pedido)
        if entrega.tracking_number or entrega.numero_guia:
            raise EnviaAPIError("El pedido ya tiene una guía de envío generada.")
        entrega.paqueteria = data.get("carrier", transportista)
        entrega.transportista = data.get("carrier", transportista)
        entrega.servicio = data.get("service", servicio)
        entrega.numero_guia = tracking_number
        entrega.tracking_number = tracking_number
        entrega.costo_envio = price
        entrega.respuesta_json = response_data
        entrega.save()

        pedido.costo_envio = price
        pedido.numero_rastreo = tracking_number
        pedido.save(update_fields=["costo_envio", "numero_rastreo"])
    return entrega


def rastrear_envio(tracking_number):
    """Consulta el último estado y eventos de una guía de Envia."""
    if not tracking_number:
        raise ValidationError({"tracking_number": "Este campo es obligatorio."})
    return _request("POST", "/ship/generaltrack/", {"trackingNumbers": [tracking_number]})