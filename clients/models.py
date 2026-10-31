import re
import unicodedata

from django.core.exceptions import ValidationError
from django.core.validators import MinLengthValidator
from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower

PHONE_PATTERN = re.compile(r"^\+?[\d\s-]+$")
PHONE_MIN_DIGITS = 7
PHONE_MAX_DIGITS = 15
ECUADOR_PREFIX = "593"
ECUADOR_MIN_INTERNATIONAL_DIGITS = 11

# WhatsApp no entrega correo y el modelo lo exige. `.invalid` es un dominio reservado
# que nunca recibe correo, así que este valor no se confunde con uno real.
PLACEHOLDER_EMAIL_DOMAIN = "whatsapp.invalid"


def validate_phone(value: str) -> None:
    digit_count = sum(character.isdigit() for character in value)
    is_valid_length = PHONE_MIN_DIGITS <= digit_count <= PHONE_MAX_DIGITS
    if not PHONE_PATTERN.match(value) or not is_valid_length:
        raise ValidationError(
            "Ingresa un teléfono válido, de 7 a 15 dígitos.", code="invalid_phone"
        )


def normalize_phone(phone: str) -> str:
    """Reduce un teléfono a su número nacional: 099..., +593 99... y 59399... son el mismo."""
    digits = "".join(character for character in phone if character.isdigit())
    if digits.startswith(ECUADOR_PREFIX) and len(digits) >= ECUADOR_MIN_INTERNATIONAL_DIGITS:
        return digits.removeprefix(ECUADOR_PREFIX)
    return digits.removeprefix("0")


def normalize_search_text(text: str) -> str:
    """Quita acentos y mayúsculas, que SQLite no ignora al buscar texto en español."""
    decomposed = unicodedata.normalize("NFKD", text)
    without_accents = "".join(c for c in decomposed if not unicodedata.combining(c))
    return without_accents.casefold()


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
    search_text = models.CharField(max_length=241, blank=True, editable=False)
    phone_key = models.CharField(max_length=20, blank=True, db_index=True, editable=False)
    whatsapp_id = models.CharField(
        "número de WhatsApp", max_length=15, null=True, blank=True, unique=True, editable=False
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

    @property
    def has_real_email(self) -> bool:
        return not self.email.endswith(f"@{PLACEHOLDER_EMAIL_DOMAIN}")

    def clean(self) -> None:
        """Normaliza el correo y reporta duplicados en su campo, no como error general."""
        self.email = self.email.strip().lower()
        duplicates = Client.objects.filter(email__iexact=self.email).exclude(pk=self.pk)
        if self.email and duplicates.exists():
            raise ValidationError({"email": "Ya existe un cliente con este correo."})

    def save(self, *args, **kwargs) -> None:
        self.search_text = normalize_search_text(f"{self.name} {self.company}")
        self.phone_key = normalize_phone(self.phone)
        super().save(*args, **kwargs)


class WhatsAppMessage(models.Model):
    class Direction(models.TextChoices):
        INBOUND = "in", "Recibido"
        OUTBOUND = "out", "Enviado"

    client = models.ForeignKey(
        Client, verbose_name="cliente", on_delete=models.CASCADE, related_name="messages"
    )
    direction = models.CharField("dirección", max_length=3, choices=Direction.choices)
    body = models.TextField("mensaje")
    # Meta reintenta las entregas: este identificador evita guardar dos veces el mismo mensaje.
    wa_message_id = models.CharField(max_length=128, null=True, blank=True, unique=True)
    created_at = models.DateTimeField("creado", auto_now_add=True)

    class Meta:
        verbose_name = "mensaje de WhatsApp"
        verbose_name_plural = "mensajes de WhatsApp"
        ordering = ["created_at", "id"]
        indexes = [
            models.Index(fields=["client", "created_at"], name="message_client_created_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.get_direction_display()}: {self.body[:40]}"
