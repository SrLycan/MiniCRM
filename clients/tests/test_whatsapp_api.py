import json

from django.contrib.auth import get_user_model
from django.test import Client as HttpClient
from django.test import TestCase, override_settings
from django.urls import reverse

from clients.models import Client
from clients.whatsapp import sign

from .test_api import ApiTestCase
from .test_whatsapp import SECRET, meta_payload

WEBHOOK_URL = reverse("clients:whatsapp_webhook")
SIMULATE_URL = reverse("clients:api_simulate_whatsapp")


@override_settings(WHATSAPP_APP_SECRET=SECRET)
class WhatsAppWebhookTests(TestCase):
    def setUp(self):
        # Con la validación de CSRF activa, como llega una petición real de un servicio.
        self.http = HttpClient(enforce_csrf_checks=True)

    def post(self, body: bytes, signature: str | None) -> object:
        headers = {} if signature is None else {"X-Hub-Signature-256": signature}
        return self.http.post(
            WEBHOOK_URL, body, content_type="application/json", headers=headers
        )

    def post_signed(self, payload: dict) -> object:
        body = json.dumps(payload).encode()
        return self.post(body, sign(body, SECRET))

    def test_signed_message_creates_a_prospect_without_session(self):
        response = self.post_signed(meta_payload())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
        self.assertEqual(Client.objects.get().whatsapp_id, "593991234567")

    def test_repeated_delivery_answers_200_and_does_not_duplicate(self):
        for _ in range(2):
            self.assertEqual(self.post_signed(meta_payload()).status_code, 200)
        self.assertEqual(Client.objects.count(), 1)

    def test_delivery_event_answers_200_without_changes(self):
        response = self.post_signed({"entry": [{"changes": [{"value": {"statuses": [{}]}}]}]})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Client.objects.count(), 0)

    def test_missing_signature_is_rejected(self):
        response = self.post(json.dumps(meta_payload()).encode(), None)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "INVALID_SIGNATURE")
        self.assertEqual(Client.objects.count(), 0)

    def test_tampered_body_is_rejected(self):
        signature = sign(json.dumps(meta_payload()).encode(), SECRET)
        response = self.post(json.dumps(meta_payload(name="Otro")).encode(), signature)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Client.objects.count(), 0)

    def test_malformed_body_with_valid_signature(self):
        response = self.post(b"{no es json", sign(b"{no es json", SECRET))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "INVALID_JSON")

    @override_settings(WHATSAPP_APP_SECRET="")
    def test_without_secret_fails_closed(self):
        response = self.post(b"{}", sign(b"{}", ""))
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["code"], "WEBHOOK_NOT_CONFIGURED")

    def test_only_accepts_post(self):
        response = self.http.get(WEBHOOK_URL)
        self.assertEqual(response.status_code, 405)
        self.assertEqual(response.json()["code"], "METHOD_NOT_ALLOWED")


@override_settings(WHATSAPP_APP_SECRET=SECRET)
class WhatsAppSimulationTests(ApiTestCase):
    def test_creates_a_visible_prospect(self):
        response = self.client.post(SIMULATE_URL)
        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(body["source"], "whatsapp")
        self.assertEqual(body["status"], "prospect")
        self.assertEqual(body["email"], "")
        self.assertTrue(body["phone"].startswith("+59399"))

    def test_response_does_not_expose_the_secret(self):
        self.assertNotIn(SECRET, self.client.post(SIMULATE_URL).content.decode())

    def test_requires_session(self):
        self.client.logout()
        self.assertEqual(self.client.post(SIMULATE_URL).status_code, 401)
        self.assertEqual(Client.objects.count(), 0)

    def test_requires_csrf(self):
        http = HttpClient(enforce_csrf_checks=True)
        http.force_login(get_user_model().objects.get(username="revisor"))
        self.assertEqual(http.post(SIMULATE_URL).status_code, 403)
        self.assertEqual(Client.objects.count(), 0)

    def test_only_accepts_post(self):
        self.assertEqual(self.client.get(SIMULATE_URL).status_code, 405)

    @override_settings(WHATSAPP_APP_SECRET="")
    def test_without_secret_explains_the_failure(self):
        response = self.client.post(SIMULATE_URL)
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["code"], "WEBHOOK_NOT_CONFIGURED")
