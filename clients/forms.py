from django import forms

from .models import Client


STATUS_ERROR_MESSAGES = {
    "required": "Selecciona un estado.",
    "invalid_choice": "Selecciona un estado válido.",
}


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
            "status": STATUS_ERROR_MESSAGES,
        }


class ClientStatusForm(forms.ModelForm):
    """Cambia solo el estado, sin exigir el resto de los datos del cliente."""

    class Meta:
        model = Client
        fields = ["status"]
        error_messages = {"status": STATUS_ERROR_MESSAGES}
