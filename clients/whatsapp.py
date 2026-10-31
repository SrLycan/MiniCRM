"""Recibe los mensajes de WhatsApp y los asocia a sus clientes.

Usa el formato y la firma de los webhooks de Meta, pero la integración es simulada: la
aplicación no se conecta con Meta, así que nada de lo que se escribe sale a WhatsApp.
"""

import hashlib
import hmac
import json
import re
import secrets
from dataclasses import dataclass

from .models import PLACEHOLDER_EMAIL_DOMAIN, Client, WhatsAppMessage, normalize_phone
from .serializers import parse_json_object

SIGNATURE_PREFIX = "sha256="
WHATSAPP_ID_PATTERN = re.compile(r"\d{7,15}")
NAME_MAX_LENGTH = 120
NAME_MIN_LENGTH = 2
MESSAGE_MAX_LENGTH = 4096
MESSAGE_ID_MAX_LENGTH = 128
EMPTY_MESSAGE_TEXT = "[Mensaje sin texto]"

SIMULATED_NAMES = (
    "Lucía Paredes",
    "Martín Cevallos",
    "Daniela Ortega",
    "Andrés Villacís",
    "Paola Jaramillo",
    "Esteban Moncayo",
)
SIMULATED_FIRST_MESSAGES = (
    "Hola, quiero más información sobre sus servicios.",
    "Buenas tardes, ¿me pueden enviar una cotización?",
    "Hola, vi su publicación y me interesa.",
)
SIMULATED_REPLIES = (
    "Perfecto, muchas gracias.",
    "¿Qué horarios tienen disponibles?",
    "Me parece bien, ¿cómo seguimos?",
    "Déjenme revisarlo y les confirmo.",
)
SIMULATED_COUNTRY_PREFIX = "59399"
SIMULATED_NUMBER_DIGITS = 7
LOCAL_NUMBER_LENGTHS = (8, 9)


@dataclass(frozen=True)
class IncomingMessage:
    whatsapp_id: str
    name: object
    message_id: str | None
    text: str


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


def _message_text(message: dict) -> str:
    text = message.get("text")
    body = text.get("body") if isinstance(text, dict) else None
    if isinstance(body, str) and body.strip():
        return body.strip()[:MESSAGE_MAX_LENGTH]
    return EMPTY_MESSAGE_TEXT


def _message_id(message: dict) -> str | None:
    message_id = message.get("id")
    is_usable = isinstance(message_id, str) and 0 < len(message_id) <= MESSAGE_ID_MAX_LENGTH
    return message_id if is_usable else None


def extract_messages(payload: dict) -> list[IncomingMessage]:
    """Lee los mensajes entrantes, sin los eventos de entrega."""
    messages = []
    for entry in _dict_items(payload, "entry"):
        for change in _dict_items(entry, "changes"):
            value = change.get("value")
            if not isinstance(value, dict):
                continue
            names = _profile_names(value)
            for message in _dict_items(value, "messages"):
                sender = message.get("from")
                if isinstance(sender, str) and WHATSAPP_ID_PATTERN.fullmatch(sender):
                    messages.append(
                        IncomingMessage(
                            whatsapp_id=sender,
                            name=names.get(sender),
                            message_id=_message_id(message),
                            text=_message_text(message),
                        )
                    )
    return messages


def clean_name(name: object, whatsapp_id: str) -> str:
    text = " ".join(name.split())[:NAME_MAX_LENGTH] if isinstance(name, str) else ""
    return text if len(text) >= NAME_MIN_LENGTH else f"WhatsApp +{whatsapp_id}"


def find_or_create_client(whatsapp_id: str, name: object) -> Client:
    """Busca al cliente por su número para conservar sus datos; si no existe, lo crea."""
    client = Client.objects.filter(whatsapp_id=whatsapp_id).first()
    if client:
        return client

    registered = (
        Client.objects.filter(phone_key=normalize_phone(whatsapp_id), whatsapp_id__isnull=True)
        .order_by("created_at", "id")
        .first()
    )
    if registered:
        registered.whatsapp_id = whatsapp_id
        registered.save(update_fields=["whatsapp_id"])
        return registered

    client, _ = Client.objects.get_or_create(
        whatsapp_id=whatsapp_id,
        defaults={
            "name": clean_name(name, whatsapp_id),
            "email": f"{whatsapp_id}@{PLACEHOLDER_EMAIL_DOMAIN}",
            "phone": f"+{whatsapp_id}",
            "status": Client.Status.PROSPECT,
        },
    )
    return client


def store_message(client: Client, message: IncomingMessage) -> WhatsAppMessage:
    values = {
        "client": client,
        "direction": WhatsAppMessage.Direction.INBOUND,
        "body": message.text,
    }
    if message.message_id is None:
        return WhatsAppMessage.objects.create(**values)
    stored, _ = WhatsAppMessage.objects.get_or_create(
        wa_message_id=message.message_id, defaults=values
    )
    return stored


def register_messages(payload: dict) -> list[WhatsAppMessage]:
    stored = []
    for message in extract_messages(payload):
        client = find_or_create_client(message.whatsapp_id, message.name)
        stored.append(store_message(client, message))
    return stored


def receive_webhook(body: bytes, signature: str, secret: str) -> list[WhatsAppMessage]:
    """Único punto de entrada de los mensajes, reales o simulados. Falla cerrado."""
    if not secret:
        raise WebhookRejected("WEBHOOK_NOT_CONFIGURED", "El webhook no está configurado.", 503)
    if not is_valid_signature(body, signature, secret):
        raise WebhookRejected("INVALID_SIGNATURE", "La firma no es válida.", 403)

    payload = parse_json_object(body)
    if payload is None:
        raise WebhookRejected("INVALID_JSON", "La solicitud no es válida.", 400)
    return register_messages(payload)


def whatsapp_number_of(client: Client) -> str:
    """Número internacional del cliente, o vacío si su teléfono no sirve para WhatsApp."""
    if client.whatsapp_id:
        return client.whatsapp_id
    local_number = client.phone_key
    number = f"593{local_number}" if len(local_number) in LOCAL_NUMBER_LENGTHS else local_number
    return number if WHATSAPP_ID_PATTERN.fullmatch(number) else ""


def _encode_message(whatsapp_id: str, name: str, text: str) -> bytes:
    """Arma un mensaje con el formato de los webhooks de Meta."""
    message = {
        "from": whatsapp_id,
        "id": f"wamid.simulado.{secrets.token_hex(8)}",
        "type": "text",
        "text": {"body": text},
    }
    value = {
        "messaging_product": "whatsapp",
        "contacts": [{"profile": {"name": name}, "wa_id": whatsapp_id}],
        "messages": [message],
    }
    payload = {
        "object": "whatsapp_business_account",
        "entry": [{"changes": [{"field": "messages", "value": value}]}],
    }
    return json.dumps(payload).encode()


def build_simulated_message() -> bytes:
    """Mensaje de alguien nuevo, con un número y un nombre de ejemplo."""
    digits = "".join(secrets.choice("0123456789") for _ in range(SIMULATED_NUMBER_DIGITS))
    return _encode_message(
        f"{SIMULATED_COUNTRY_PREFIX}{digits}",
        secrets.choice(SIMULATED_NAMES),
        secrets.choice(SIMULATED_FIRST_MESSAGES),
    )


def build_simulated_reply(client: Client) -> bytes:
    return _encode_message(
        whatsapp_number_of(client), client.name, secrets.choice(SIMULATED_REPLIES)
    )
