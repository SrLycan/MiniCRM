import json

from .models import Client, WhatsAppMessage


def parse_json_object(raw_body: bytes) -> dict | None:
    """Devuelve el cuerpo como diccionario, o None si no es un objeto JSON válido."""
    try:
        data = json.loads(raw_body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    return data if isinstance(data, dict) else None


def serialize_client(client: Client) -> dict:
    return {
        "id": client.pk,
        "name": client.name,
        "company": client.company,
        "email": client.email if client.has_real_email else "",
        "phone": client.phone,
        "status": client.status,
        "status_label": client.get_status_display(),
        "source": "whatsapp" if client.whatsapp_id else "manual",
        "created_at": client.created_at.isoformat(),
        "updated_at": client.updated_at.isoformat(),
    }


def serialize_message(message: WhatsAppMessage) -> dict:
    return {
        "id": message.pk,
        "direction": message.direction,
        "body": message.body,
        "created_at": message.created_at.isoformat(),
    }
