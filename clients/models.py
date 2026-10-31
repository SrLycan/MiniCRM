import re

from django.core.exceptions import ValidationError
from django.core.validators import MinLengthValidator
from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower

PHONE_PATTERN = re.compile(r"^\+?[\d\s-]+$")
PHONE_MIN_DIGITS = 7
PHONE_MAX_DIGITS = 15


def validate_phone(value: str) -> None:
    digit_count = sum(character.isdigit() for character in value)
    is_valid_length = PHONE_MIN_DIGITS <= digit_count <= PHONE_MAX_DIGITS
    if not PHONE_PATTERN.match(value) or not is_valid_length:
        raise ValidationError(
            "Ingresa un teléfono válido, de 7 a 15 dígitos.", code="invalid_phone"
        )


class Client(models.Model):
    class Status(models.TextChoices):
        PROSPECT = "prospect", "Prospecto"
        CLIENT = "client", "Cliente"
        INACTIVE = "inactive", "Inactivo"

    name = models.CharField("nombre", max_length=120, validators=[MinLengthValidator(2)])
    company = models.CharField("empresa", max_length=120, blank=True)
    email = models.EmailField("correo")
    phone = models.CharField("teléfono", max_length=20, blank=True, validators=[validate_phone])
    status = models.CharField(
        "estado", max_length=10, choices=Status.choices, default=Status.PROSPECT
    )
    created_at = models.DateTimeField("creado", auto_now_add=True)
    updated_at = models.DateTimeField("actualizado", auto_now=True)

    class Meta:
        verbose_name = "cliente"
        verbose_name_plural = "clientes"
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["status"], name="client_status_idx"),
            models.Index(fields=["created_at"], name="client_created_at_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                Lower("email"),
                name="client_email_unique_ci",
                violation_error_message="Ya existe un cliente con este correo.",
            ),
            models.CheckConstraint(
                condition=Q(status__in=["prospect", "client", "inactive"]),
                name="client_status_valid",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} <{self.email}>"

    def clean(self) -> None:
        """Normaliza el correo y reporta duplicados en su campo, no como error general."""
        self.email = self.email.strip().lower()
        duplicates = Client.objects.filter(email__iexact=self.email).exclude(pk=self.pk)
        if self.email and duplicates.exists():
            raise ValidationError({"email": "Ya existe un cliente con este correo."})
