from django.contrib.auth import get_user_model
from django.test import Client as HttpClient
from django.test import override_settings
from django.urls import reverse

from clients.models import Client, WhatsAppMessage
from clients.whatsapp import register_messages

from .test_api import ApiTestCase, make_client
from .test_whatsapp import SECRET, meta_payload

CONVERSATIONS_URL = reverse("clients:api_conversations")


def conversation_url(pk: int) -> str:
    return reverse("clients:api_conversation", args=[pk])


def messages_url(pk: int) -> str:
    return reverse("clients:api_conversation_messages", args=[pk])


def reply_url(pk: int) -> str:
    return reverse("clients:api_conversation_simulate_reply", args=[pk])


class ConversationListTests(ApiTestCase):
    def test_lists_only_clients_with_messages(self):
        make_client("Sin mensajes", phone="0991111111")
        register_messages(meta_payload())
        results = self.client.get(CONVERSATIONS_URL).json()["results"]
        self.assertEqual([item["client"]["name"] for item in results], ["Lucía Paredes"])
        self.assertEqual(results[0]["last_message"]["body"], "Hola")
        self.assertEqual(results[0]["last_message"]["direction"], "in")

    def test_most_recent_conversation_goes_first(self):
        register_messages(meta_payload(sender="593991234567", name="Primera"))
        register_messages(meta_payload(sender="593991234568", name="Segunda", message_id="w2"))
        register_messages(meta_payload(sender="593991234567", message_id="w3", text="Última"))
        results = self.client.get(CONVERSATIONS_URL).json()["results"]
        self.assertEqual(results[0]["client"]["name"], "Primera")
        self.assertEqual(results[0]["last_message"]["body"], "Última")
        self.assertEqual(len(results), 2)


class ConversationDetailTests(ApiTestCase):
    def test_returns_messages_in_order(self):
        client = register_messages(meta_payload())[0].client
        register_messages(meta_payload(message_id="w2", text="Segundo"))
        body = self.client.get(conversation_url(client.pk)).json()
        self.assertEqual([m["body"] for m in body["messages"]], ["Hola", "Segundo"])
        self.assertTrue(body["can_chat"])

    def test_registered_client_without_messages_can_start_a_chat(self):
        client = make_client(phone="0991234567")
        body = self.client.get(conversation_url(client.pk)).json()
        self.assertEqual(body["messages"], [])
        self.assertTrue(body["can_chat"])

    def test_client_without_phone_cannot_chat(self):
        client = make_client()
        self.assertFalse(self.client.get(conversation_url(client.pk)).json()["can_chat"])

    def test_missing_client_returns_404(self):
        self.assertEqual(self.client.get(conversation_url(999)).status_code, 404)


class SendMessageTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.client_record = make_client(phone="0991234567")
        self.url = messages_url(self.client_record.pk)

    def test_stores_an_outgoing_message(self):
        response = self.send("post", self.url, {"body": "  Hola, Ana  "})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["direction"], "out")
        self.assertEqual(response.json()["body"], "Hola, Ana")
        self.assertEqual(self.client_record.messages.count(), 1)

    def test_does_not_change_the_client(self):
        self.send("post", self.url, {"body": "Hola"})
        self.client_record.refresh_from_db()
        self.assertEqual(self.client_record.email, "ana.ruiz@example.com")
        self.assertEqual(self.client_record.company, "Acme")

    def test_blank_message_is_rejected(self):
        for body in ({"body": ""}, {"body": "   "}, {}):
            response = self.send("post", self.url, body)
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json()["errors"]["body"], ["Escribe un mensaje."])

    def test_long_message_is_rejected(self):
        response = self.send("post", self.url, {"body": "a" * 1001})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.client_record.messages.count(), 0)

    def test_html_is_stored_as_plain_text(self):
        self.send("post", self.url, {"body": "<script>alert(1)</script>"})
        self.assertEqual(self.client_record.messages.get().body, "<script>alert(1)</script>")

    def test_malformed_json_is_a_clear_error(self):
        response = self.send("post", self.url, "{no es json")
        self.assertEqual(response.json()["code"], "INVALID_JSON")

    def test_client_without_phone_is_refused(self):
        client = make_client("Sin Telefono")
        response = self.send("post", messages_url(client.pk), {"body": "Hola"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "PHONE_REQUIRED")

    def test_missing_client_returns_404(self):
        self.assertEqual(self.send("post", messages_url(999), {"body": "Hola"}).status_code, 404)


@override_settings(WHATSAPP_APP_SECRET=SECRET)
class SimulatedReplyTests(ApiTestCase):
    def test_reply_keeps_the_data_of_a_registered_client(self):
        client = make_client(phone="0991234567", status=Client.Status.CLIENT)
        response = self.client.post(reply_url(client.pk))
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["direction"], "in")

        self.assertEqual(Client.objects.count(), 1)
        client.refresh_from_db()
        self.assertEqual(client.email, "ana.ruiz@example.com")
        self.assertEqual(client.company, "Acme")
        self.assertEqual(client.status, Client.Status.CLIENT)
        self.assertEqual(client.messages.count(), 1)

    def test_several_replies_are_all_stored(self):
        client = make_client(phone="0991234567")
        for _ in range(3):
            self.client.post(reply_url(client.pk))
        self.assertEqual(client.messages.count(), 3)
        self.assertEqual(Client.objects.count(), 1)

    def test_client_without_phone_is_refused(self):
        client = make_client()
        response = self.client.post(reply_url(client.pk))
        self.assertEqual(response.json()["code"], "PHONE_REQUIRED")

    @override_settings(WHATSAPP_APP_SECRET="")
    def test_without_secret_explains_the_failure(self):
        client = make_client(phone="0991234567")
        self.assertEqual(self.client.post(reply_url(client.pk)).status_code, 503)
        self.assertEqual(WhatsAppMessage.objects.count(), 0)


class ConversationSecurityTests(ApiTestCase):
    def test_all_routes_require_a_session(self):
        client = make_client(phone="0991234567")
        self.client.logout()
        self.assertEqual(self.client.get(CONVERSATIONS_URL).status_code, 401)
        self.assertEqual(self.client.get(conversation_url(client.pk)).status_code, 401)
        self.assertEqual(self.send("post", messages_url(client.pk), {"body": "x"}).status_code, 401)
        self.assertEqual(self.client.post(reply_url(client.pk)).status_code, 401)
        self.assertEqual(WhatsAppMessage.objects.count(), 0)

    def test_writing_requires_csrf(self):
        client = make_client(phone="0991234567")
        http = HttpClient(enforce_csrf_checks=True)
        http.force_login(get_user_model().objects.get(username="revisor"))
        response = http.post(
            messages_url(client.pk), '{"body": "x"}', content_type="application/json"
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(http.post(reply_url(client.pk)).status_code, 403)

    def test_deleting_a_client_removes_its_messages(self):
        client = register_messages(meta_payload())[0].client
        client.delete()
        self.assertEqual(WhatsAppMessage.objects.count(), 0)
