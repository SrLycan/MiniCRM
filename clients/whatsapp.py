"""Convierte los mensajes entrantes de WhatsApp en prospectos.

Usa el formato y la firma de los webhooks de Meta, pero la integración es simulada: la
aplicación no se conecta con Meta ni guarda el texto de los mensajes.
"""

import hashlib
import hmac
import json
import re
import secrets

from .models import PLACEHOLDER_EMAIL_DOMAIN, Client
from .serializers import parse_json_object

SIGNATURE_PREFIX = "sha256="
WHATSAPP_ID_PATTERN = re.compile(r"\d{7,15}")
NAME_MAX_LENGTH = 120
NAME_MIN_LENGTH = 2

SIMULATED_NAMES = (
    "Lucía Paredes",
    "Martín Cevallos",
    "Daniela Ortega",
    "Andrés Villacís",
    "Paola Jaramillo",
    "Esteban Moncayo",
)
SIMULATED_COUNTRY_PREFIX = "59399"
SIMULATED_NUMBER_DIGITS = 7


class WebhookRejected(Exception):
    def __init__(self, code: str, message: str, status: int) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


def sign(body: bytes, secret: str) -> str:
    digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return f"{SIGNATURE_PREFIX}{digest}"


def is_valid_signature(body: bytes, signature: str, secret: str) -> bool:
    return hmac.compare_digest(sign(body, secret).encode(), signature.encode())


def _dict_items(container: dict, key: str) -> list[dict]:
    """Lee una lista del mensaje descartando lo que no tenga la forma esperada."""
    value = container.get(key)
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _profile_names(value: dict) -> dict:
    names = {}
    for contact in _dict_items(value, "contacts"):
        profile = contact.get("profile")
        if isinstance(profile, dict):
            names[contact.get("wa_id")] = profile.get("name")
    return names


def extract_senders(payload: dict) -> list[tuple[str, object]]:
    """Devuelve el número y el nombre de quien escribió, sin los eventos de entrega."""
    senders = []
    for entry in _dict_items(payload, "entry"):
        for change in _dict_items(entry, "changes"):
            value = change.get("value")
            if not isinstance(value, dict):
                continue
            names = _profile_names(value)
            for message in _dict_items(value, "messages"):
                sender = message.get("from")
                if isinstance(sender, str) and WHATSAPP_ID_PATTERN.fullmatch(sender):
                    senders.append((sender, names.get(sender)))
    return senders


def clean_name(name: object, whatsapp_id: str) -> str:
    text = " ".join(name.split())[:NAME_MAX_LENGTH] if isinstance(name, str) else ""
    return text if len(text) >= NAME_MIN_LENGTH else f"WhatsApp +{whatsapp_id}"


def register_prospects(payload: dict) -> list[Client]:
    """Crea un prospecto por número; un número conocido devuelve el cliente existente."""
    clients = []
    for whatsapp_id, name in extract_senders(payload):
        client, _ = Client.objects.get_or_create(
            whatsapp_id=whatsapp_id,
            defaults={
                "name": clean_name(name, whatsapp_id),
                "email": f"{whatsapp_id}@{PLACEHOLDER_EMAIL_DOMAIN}",
                "phone": f"+{whatsapp_id}",
                "status": Client.Status.PROSPECT,
            },
        )
        clients.append(client)
    return clients


def receive_webhook(body: bytes, signature: str, secret: str) -> list[Client]:
    """Único punto de entrada de los mensajes, reales o simulados. Falla cerrado."""
    if not secret:
        raise WebhookRejected("WEBHOOK_NOT_CONFIGURED", "El webhook no está configurado.", 503)
    if not is_valid_signature(body, signature, secret):
        raise WebhookRejected("INVALID_SIGNATURE", "La firma no es válida.", 403)

    payload = parse_json_object(body)
    if payload is None:
        raise WebhookRejected("INVALID_JSON", "La solicitud no es válida.", 400)
    return register_prospects(payload)


def build_simulated_message() -> bytes:
    """Arma un mensaje con el formato de Meta, de un número y un nombre de ejemplo."""
    digits = "".join(secrets.choice("0123456789") for _ in range(SIMULATED_NUMBER_DIGITS))
    whatsapp_id = f"{SIMULATED_COUNTRY_PREFIX}{digits}"
    message = {
        "from": whatsapp_id,
        "id": f"wamid.simulado.{secrets.token_hex(8)}",
        "type": "text",
        "text": {"body": "Hola, quiero más información."},
    }
    value = {
        "messaging_product": "whatsapp",
        "contacts": [
            {"profile": {"name": secrets.choice(SIMULATED_NAMES)}, "wa_id": whatsapp_id},
        ],
        "messages": [message],
    }
    payload = {
        "object": "whatsapp_business_account",
        "entry": [{"changes": [{"field": "messages", "value": value}]}],
    }
    return json.dumps(payload).encode()
