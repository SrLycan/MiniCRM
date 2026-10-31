from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

LOGIN_URL = reverse("accounts:login")
LOGOUT_URL = reverse("accounts:logout")
DASHBOARD_URL = reverse("clients:dashboard")
CLIENTS_URL = reverse("clients:client_list")
BOARD_URL = reverse("clients:board")
API_URLS = [reverse("clients:api_collection"), reverse("clients:api_stats")]


class AuthTestCase(TestCase):
    def setUp(self):
        cache.clear()
        self.user = get_user_model().objects.create_user("revisor", password="clave-correcta")

    def login(self, password: str = "clave-correcta"):
        return self.client.post(LOGIN_URL, {"username": "revisor", "password": password})


class AccessControlTests(AuthTestCase):
    def test_pages_redirect_to_login_without_session(self):
        for url in (DASHBOARD_URL, CLIENTS_URL, BOARD_URL):
            response = self.client.get(url)
            self.assertRedirects(response, f"{LOGIN_URL}?next={url}")

    def test_api_returns_401_without_session(self):
        for url in API_URLS:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 401)
            self.assertEqual(response.json()["code"], "AUTH_REQUIRED")

    def test_api_detail_does_not_reveal_data_without_session(self):
        response = self.client.delete(reverse("clients:api_detail", args=[1]))
        self.assertEqual(response.status_code, 401)


class LoginFlowTests(AuthTestCase):
    def test_valid_credentials_open_the_dashboard(self):
        self.assertRedirects(self.login(), DASHBOARD_URL)

    def test_wrong_password_shows_an_error(self):
        response = self.login("incorrecta")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors)

    def test_logged_in_user_skips_the_login_page(self):
        self.client.force_login(self.user)
        self.assertRedirects(self.client.get(LOGIN_URL), DASHBOARD_URL)

    def test_logout_requires_post_and_ends_the_session(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(LOGOUT_URL).status_code, 405)
        self.assertRedirects(self.client.post(LOGOUT_URL), LOGIN_URL)
        self.assertEqual(self.client.get(API_URLS[0]).status_code, 401)


@override_settings(LOGIN_MAX_ATTEMPTS=3)
class LoginLockoutTests(AuthTestCase):
    def fail_until_locked(self):
        for _ in range(3):
            self.login("incorrecta")

    def test_correct_password_is_refused_while_locked(self):
        self.fail_until_locked()
        response = self.login()
        self.assertEqual(response.status_code, 429)
        self.assertContains(response, "Demasiados intentos", status_code=429)
        self.assertEqual(self.client.get(API_URLS[0]).status_code, 401)

    def test_lockout_does_not_affect_other_users(self):
        get_user_model().objects.create_user("otra", password="clave-correcta")
        self.fail_until_locked()
        response = self.client.post(
            LOGIN_URL, {"username": "otra", "password": "clave-correcta"}
        )
        self.assertRedirects(response, DASHBOARD_URL)

    def test_successful_login_resets_the_counter(self):
        self.login("incorrecta")
        self.login("incorrecta")
        self.login()
        self.client.post(LOGOUT_URL)
        self.login("incorrecta")
        self.login("incorrecta")
        self.assertRedirects(self.login(), DASHBOARD_URL)
