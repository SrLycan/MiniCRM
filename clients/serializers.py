from .models import Client


def serialize_client(client: Client) -> dict:
    return {
        "id": client.pk,
        "name": client.name,
        "company": client.company,
        "email": client.email,
        "phone": client.phone,
        "status": client.status,
        "status_label": client.get_status_display(),
        "created_at": client.created_at.isoformat(),
        "updated_at": client.updated_at.isoformat(),
    }
