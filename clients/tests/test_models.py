from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from clients.forms import ClientForm
from clients.models import Client

VALID_DATA = {
    "name": "Juan Pérez",
    "company": "Empresa XYZ",
    "email": "juan@example.com",
    "phone": "0999999999",
    "status": Client.Status.PROSPECT,
}


class ClientConstraintTests(TestCase):
    def test_database_rejects_email_differing_only_in_case(self):
        Client.objects.create(name="Ana", email="ana@example.com")
        with self.assertRaises(IntegrityError), transaction.atomic():
            Client.objects.create(name="Otra Ana", email="ANA@example.com")

    def test_database_rejects_unknown_status(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Client.objects.create(name="Ana", email="ana@example.com", status="vip")

    def test_timestamps_are_set_automatically(self):
        client = Client.objects.create(name="Ana", email="ana@example.com")
        self.assertIsNotNone(client.created_at)
        self.assertIsNotNone(client.updated_at)


class ClientFormTests(TestCase):
    def form_errors(self, **overrides):
        form = ClientForm({**VALID_DATA, **overrides})
        form.is_valid()
        return form.errors

    def test_valid_data_saves_normalized_values(self):
        form = ClientForm({**VALID_DATA, "name": "  Juan Pérez  ", "email": "JUAN@Example.com"})
        self.assertTrue(form.is_valid(), form.errors)
        client = form.save()
        self.assertEqual(client.name, "Juan Pérez")
        self.assertEqual(client.email, "juan@example.com")

    def test_company_and_phone_are_optional(self):
        self.assertEqual(self.form_errors(company="", phone=""), {})

    def test_required_fields_show_clear_messages(self):
        self.assertEqual(self.form_errors(name="")["name"], ["Ingresa el nombre del cliente."])
        self.assertEqual(self.form_errors(email="")["email"], ["Ingresa el correo del cliente."])
        self.assertEqual(self.form_errors(status="")["status"], ["Selecciona un estado."])

    def test_name_needs_two_characters(self):
        self.assertIn("name", self.form_errors(name="A"))

    def test_invalid_email_and_status_are_rejected(self):
        self.assertEqual(self.form_errors(email="correo")["email"], ["Ingresa un correo válido."])
        self.assertIn("status", self.form_errors(status="vip"))

    def test_duplicate_email_is_reported_on_the_email_field(self):
        Client.objects.create(name="Ana", email="juan@example.com")
        errors = self.form_errors(email="JUAN@example.com")
        self.assertEqual(errors["email"], ["Ya existe un cliente con este correo."])
        self.assertNotIn("__all__", errors)

    def test_editing_a_client_keeps_its_own_email_valid(self):
        client = Client.objects.create(name="Ana", email="juan@example.com")
        form = ClientForm(VALID_DATA, instance=client)
        self.assertTrue(form.is_valid(), form.errors)

    def test_phone_format(self):
        for phone in ("0999999999", "+593 99 999 9999", "02-234-5678"):
            self.assertEqual(self.form_errors(phone=phone), {}, phone)
        for phone in ("abc", "123", "1234567890123456", "099+999999"):
            self.assertIn("phone", self.form_errors(phone=phone), phone)

    def test_model_validation_matches_for_other_entry_points(self):
        client = Client(name="Ana", email="ana@example.com", phone="abc")
        with self.assertRaises(ValidationError):
            client.full_clean()
