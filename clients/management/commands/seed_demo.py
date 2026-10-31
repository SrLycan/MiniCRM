from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from clients.models import Client

PROSPECT = Client.Status.PROSPECT
CLIENT = Client.Status.CLIENT
INACTIVE = Client.Status.INACTIVE

# Nombre, empresa, teléfono, estado y días de antigüedad. Personas y empresas ficticias.
DEMO_CLIENTS = [
    ("Valentina Andrade", "Café del Pacífico", "0991234501", CLIENT, 1),
    ("Mateo Guerrero", "Andes Logística", "0991234502", PROSPECT, 2),
    ("Camila Rivadeneira", "Clínica Santa Lucía", "0991234503", CLIENT, 3),
    ("Sebastián Mora", "Nova Seguros", "0991234504", PROSPECT, 5),
    ("Isabella Cedeño", "Hotel Mirador", "+593 2 234 5605", CLIENT, 6),
    ("Nicolás Vásconez", "", "0991234506", PROSPECT, 7),
    ("Doménica Paredes", "Estudio Lumen", "0991234507", CLIENT, 8),
    ("Joaquín Salazar", "Agroexport Sierra", "0991234508", INACTIVE, 9),
    ("Martina Zambrano", "Café del Pacífico", "0991234509", PROSPECT, 10),
    ("Emilio Cevallos", "TecnoAndina", "0991234510", CLIENT, 11),
    ("Antonella Ortiz", "Colegio Horizonte", "", CLIENT, 13),
    ("Daniel Benítez", "Ferretería El Tornillo", "0991234512", INACTIVE, 14),
    ("Renata Játiva", "Nova Seguros", "0991234513", PROSPECT, 15),
    ("Tomás Espinosa", "Constructora Pichincha", "0991234514", CLIENT, 16),
    ("Paula Villacís", "Estudio Lumen", "0991234515", PROSPECT, 17),
    ("Gabriel Naranjo", "", "0991234516", INACTIVE, 18),
    ("Sofía Maldonado", "Clínica Santa Lucía", "+593 99 123 4517", CLIENT, 20),
    ("Andrés Terán", "Andes Logística", "0991234518", CLIENT, 23),
    ("Luciana Pazmiño", "Hotel Mirador", "0991234519", PROSPECT, 24),
    ("Diego Herrera", "Agroexport Sierra", "0991234520", CLIENT, 28),
    ("Emma Chiriboga", "TecnoAndina", "", PROSPECT, 31),
    ("Felipe Montalvo", "Imprenta Quitumbe", "0991234522", INACTIVE, 33),
    ("Julieta Carrión", "Colegio Horizonte", "0991234523", CLIENT, 36),
    ("Bruno Almeida", "Constructora Pichincha", "0991234524", PROSPECT, 40),
]


def demo_email(name: str) -> str:
    first_name, last_name = name.lower().split()
    plain = f"{first_name}.{last_name}"
    for accented, simple in zip("áéíóúñ", "aeioun"):
        plain = plain.replace(accented, simple)
    return f"{plain}@example.com"


class Command(BaseCommand):
    help = "Crea el usuario demo y clientes de ejemplo. Se puede ejecutar varias veces."

    @transaction.atomic
    def handle(self, *args, **options) -> None:
        self.create_demo_user()
        created_count = sum(self.create_client(*client) for client in DEMO_CLIENTS)
        self.stdout.write(self.style.SUCCESS(f"Datos demo listos: {created_count} clientes nuevos."))

    @staticmethod
    def create_demo_user() -> None:
        if not settings.DEMO_USERNAME or not settings.DEMO_PASSWORD:
            raise CommandError("Define DEMO_USERNAME y DEMO_PASSWORD en el entorno.")

        user, _ = get_user_model().objects.get_or_create(username=settings.DEMO_USERNAME)
        user.first_name = "Equipo"
        user.is_staff = True
        user.is_superuser = True
        user.set_password(settings.DEMO_PASSWORD)
        user.save()

    @staticmethod
    def create_client(name: str, company: str, phone: str, status: str, age_in_days: int) -> bool:
        client, created = Client.objects.get_or_create(
            email=demo_email(name),
            defaults={"name": name, "company": company, "phone": phone, "status": status},
        )
        if created:
            # auto_now_add ignora valores propios, por eso la fecha se ajusta con update().
            created_at = timezone.now() - timedelta(days=age_in_days)
            Client.objects.filter(pk=client.pk).update(created_at=created_at, updated_at=created_at)
        return created
