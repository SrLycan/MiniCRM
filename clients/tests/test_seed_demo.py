import io

from django.contrib.auth import authenticate, get_user_model
from django.core.management import CommandError, call_command
from django.test import TestCase, override_settings

from clients.management.commands.seed_demo import DEMO_CLIENTS, demo_email
from clients.models import Client


@override_settings(DEMO_USERNAME="demo", DEMO_PASSWORD="clave-de-prueba")
class SeedDemoTests(TestCase):
    def test_creates_user_and_clients_and_can_run_twice(self):
        call_command("seed_demo", stdout=io.StringIO())
        call_command("seed_demo", stdout=io.StringIO())
        self.assertEqual(Client.objects.count(), len(DEMO_CLIENTS))
        user = authenticate(username="demo", password="clave-de-prueba")
        self.assertIsNotNone(user)
        self.assertTrue(user.is_staff)

    def test_demo_emails_use_a_reserved_domain_without_accents(self):
        self.assertEqual(demo_email("Doménica Paredes"), "domenica.paredes@example.com")

    @override_settings(DEMO_PASSWORD="")
    def test_requires_credentials_from_the_environment(self):
        with self.assertRaises(CommandError):
            call_command("seed_demo", stdout=io.StringIO())



class DemoUserPermissionsTests(TestCase):
    @override_settings(DEMO_USERNAME="demo", DEMO_PASSWORD="clave-de-prueba")
    def test_demo_user_is_not_a_superuser(self):
        call_command("seed_demo", stdout=io.StringIO())
        user = get_user_model().objects.get(username="demo")
        self.assertTrue(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.has_perm("clients.change_client"))
        self.assertFalse(user.has_perm("auth.change_user"))
