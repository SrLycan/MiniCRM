from unittest import mock

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from clients.models import Client

from .test_auth import API_URLS, DASHBOARD_URL, LOGIN_URL, AuthTestCase

ADMIN_LOGIN_URL = reverse("admin:login")
ADMIN_INDEX_URL = reverse("admin:index")


class LoginLimitsTests(AuthTestCase):
    def test_inputs_declare_their_limits(self):
        response = self.client.get(LOGIN_URL)
        self.assertContains(response, 'maxlength="150"')
        self.assertContains(response, 'maxlength="128"')

    def test_oversized_password_is_rejected_without_hashing_it(self):
        with mock.patch("django.contrib.auth.forms.authenticate") as authenticate:
            response = self.client.post(LOGIN_URL, {"username": "revisor", "password": "x" * 129})
        authenticate.assert_not_called()
        self.assertContains(response, "Usuario o contraseña incorrectos.")

    def test_oversized_username_is_not_reflected_entirely(self):
        response = self.client.post(LOGIN_URL, {"username": "a" * 5000, "password": "x"})
        self.assertContains(response, "Usuario o contraseña incorrectos.")
        self.assertNotContains(response, "a" * 151)

    def test_oversized_attempts_count_towards_the_lockout(self):
        with override_settings(LOGIN_MAX_ATTEMPTS=2):
            for _ in range(2):
                self.client.post(LOGIN_URL, {"username": "revisor", "password": "x" * 200})
            self.assertEqual(self.login().status_code, 429)


class LoginRedirectTests(AuthTestCase):
    def test_always_starts_on_the_dashboard(self):
        response = self.client.post(
            LOGIN_URL,
            {"username": "revisor", "password": "clave-correcta", "next": "/clientes/"},
        )
        self.assertRedirects(response, DASHBOARD_URL)

    def test_external_next_is_ignored(self):
        response = self.client.post(
            LOGIN_URL,
            {
                "username": "revisor",
                "password": "clave-correcta",
                "next": "https://sitio-externo.example/",
            },
        )
        self.assertRedirects(response, DASHBOARD_URL)


@override_settings(LOGIN_MAX_ATTEMPTS_PER_IP=3)
class IpLockoutTests(AuthTestCase):
    def test_trying_many_usernames_locks_the_ip(self):
        for number in range(3):
            self.client.post(LOGIN_URL, {"username": f"usuario{number}", "password": "x"})
        self.assertEqual(self.login().status_code, 429)

    def test_other_ips_keep_working(self):
        for number in range(3):
            self.client.post(LOGIN_URL, {"username": f"usuario{number}", "password": "x"})
        response = self.client.post(
            LOGIN_URL,
            {"username": "revisor", "password": "clave-correcta"},
            REMOTE_ADDR="10.0.0.9",
        )
        self.assertRedirects(response, DASHBOARD_URL)


@override_settings(LOGIN_MAX_ATTEMPTS=2)
class AdminLoginTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = get_user_model().objects.create_user(
            "personal", password="clave-correcta", is_staff=True
        )

    def post(self, password: str) -> object:
        data = {"username": "personal", "password": password, "next": ADMIN_INDEX_URL}
        return self.client.post(ADMIN_LOGIN_URL, data)

    def test_admin_login_is_throttled(self):
        for _ in range(2):
            self.post("incorrecta")
        self.assertEqual(self.post("clave-correcta").status_code, 429)

    def test_staff_can_enter(self):
        self.assertRedirects(self.post("clave-correcta"), ADMIN_INDEX_URL)

    def test_user_without_staff_does_not_loop(self):
        get_user_model().objects.create_user("normal", password="clave-correcta")
        self.client.login(username="normal", password="clave-correcta")
        response = self.client.get(ADMIN_INDEX_URL, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.redirect_chain), 1)


class SecurityHeadersTests(AuthTestCase):
    def test_pages_send_the_policies(self):
        response = self.client.get(LOGIN_URL)
        policy = response.headers["Content-Security-Policy"]
        self.assertIn("script-src 'self'", policy)
        self.assertNotIn("script-src 'self' 'unsafe-inline'", policy)
        self.assertIn("frame-ancestors 'none'", policy)
        self.assertIn("Permissions-Policy", response.headers)

    def test_api_also_sends_them(self):
        self.assertIn("Content-Security-Policy", self.client.get(API_URLS[0]).headers)

    def test_html_has_no_inline_scripts(self):
        self.assertNotRegex(self.client.get(LOGIN_URL).content.decode(), r"<script(?![^>]*\bsrc=)")

    def test_login_does_not_leak_settings(self):
        with self.settings(DEMO_LOGIN_HINT=False, DEMO_PASSWORD="valor-que-no-debe-verse"):
            self.assertNotContains(self.client.get(LOGIN_URL), "valor-que-no-debe-verse")


class ApiLimitsTests(AuthTestCase):
    def test_body_over_the_limit_is_refused(self):
        self.client.force_login(self.user)
        with self.settings(DATA_UPLOAD_MAX_MEMORY_SIZE=100):
            response = self.client.post(
                API_URLS[0], "x" * 101, content_type="application/json"
            )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Client.objects.count(), 0)

    def test_long_search_is_cut(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(API_URLS[0], {"q": "a" * 10_000}).status_code, 200)
