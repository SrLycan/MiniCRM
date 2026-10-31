from django import forms

from .models import Client


class ClientForm(forms.ModelForm):
    """Única fuente de validación de la API."""

    class Meta:
        model = Client
        fields = ["name", "company", "email", "phone", "status"]
        error_messages = {
            "name": {
                "required": "Ingresa el nombre del cliente.",
                "min_length": "El nombre debe tener al menos 2 caracteres.",
            },
            "email": {
                "required": "Ingresa el correo del cliente.",
                "invalid": "Ingresa un correo válido.",
            },
            "status": {
                "required": "Selecciona un estado.",
                "invalid_choice": "Selecciona un estado válido.",
            },
        }
