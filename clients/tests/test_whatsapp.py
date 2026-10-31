import json

from django.test import SimpleTestCase, TestCase

from clients.forms import ClientForm, ClientStatusForm
from clients.models import Client
from clients.serializers import serialize_client
from clients.whatsapp import (
    WebhookRejected,
    build_simulated_message,
    clean_name,
    extract_senders,
    is_valid_signature,
    receive_webhook,
    register_prospects,
    sign,
)

SECRET = "secreto-de-prueba"


def meta_payload(sender="593991234567", name="Lucía Paredes") -> dict:
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "contacts": [{"profile": {"name": name}, "wa_id": sender}],
                            "messages": [{"from": sender, "id": "wamid.1", "type": "text"}],
                        },
                    }
                ]
            }
        ],
    }


class SignatureTests(SimpleTestCase):
    def test_known_signature(self):
        # Vector calculado con HMACSHA256 de .NET para no comprobar `sign` contra sí misma.
        self.assertEqual(
            sign(b"hola", "clave"),
            "sha256=67c0066d5104af2bd88decc45269ddb529a0097b8da4cfbbe58ec2a5f63ca50d",
        )

    def test_accepts_its_own_signature(self):
        self.assertTrue(is_valid_signature(b"cuerpo", sign(b"cuerpo", SECRET), SECRET))

    def test_rejects_other_body_secret_or_format(self):
        signature = sign(b"cuerpo", SECRET)
        self.assertFalse(is_valid_signature(b"otro", signature, SECRET))
        self.assertFalse(is_valid_signature(b"cuerpo", signature, "otro-secreto"))
        self.assertFalse(is_valid_signature(b"cuerpo", signature.removeprefix("sha256="), SECRET))
        self.assertFalse(is_valid_signature(b"cuerpo", "", SECRET))
        self.assertFalse(is_valid_signature(b"cuerpo", "sha256=ñandú", SECRET))


class ExtractSendersTests(SimpleTestCase):
    def test_reads_number_and_name(self):
        self.assertEqual(
            extract_senders(meta_payload()), [("593991234567", "Lucía Paredes")]
        )

    def test_ignores_delivery_events(self):
        payload = {"entry": [{"changes": [{"value": {"statuses": [{"id": "wamid.1"}]}}]}]}
        self.assertEqual(extract_senders(payload), [])

    def test_ignores_invalid_numbers(self):
        for sender in ("123", "1" * 16, "59399abc", "+593991234567", 593991234567):
            self.assertEqual(extract_senders(meta_payload(sender=sender)), [])

    def test_survives_unexpected_shapes(self):
        for payload in (
            {},
            {"entry": "x"},
            {"entry": [1, None]},
            {"entry": [{"changes": [{"value": "x"}]}]},
            {"entry": [{"changes": [{"value": {"messages": [{}], "contacts": [{"profile": 1}]}}]}]},
        ):
            self.assertEqual(extract_senders(payload), [])


class CleanNameTests(SimpleTestCase):
    def test_normalizes_spaces(self):
        self.assertEqual(clean_name("  Ana   Ruiz ", "593991234567"), "Ana Ruiz")

    def test_falls_back_to_the_number(self):
        for name in (None, "", " ", "A", 7):
            self.assertEqual(clean_name(name, "593991234567"), "WhatsApp +593991234567")

    def test_limits_the_length(self):
        self.assertEqual(len(clean_name("a" * 200, "593991234567")), 120)


class RegisterProspectsTests(TestCase):
    def test_creates_a_prospect(self):
        client = register_prospects(meta_payload())[0]
        self.assertEqual(client.name, "Lucía Paredes")
        self.assertEqual(client.phone, "+593991234567")
        self.assertEqual(client.status, Client.Status.PROSPECT)
        self.assertEqual(client.whatsapp_id, "593991234567")
        self.assertEqual(client.search_text, "lucia paredes ")

    def test_same_number_does_not_duplicate(self):
        first = register_prospects(meta_payload())[0]
        second = register_prospects(meta_payload(name="Otro nombre"))[0]
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(Client.objects.count(), 1)
        second.refresh_from_db()
        self.assertEqual(second.name, "Lucía Paredes")

    def test_real_email_keeps_the_prospect_identified(self):
        client = register_prospects(meta_payload())[0]
        Client.objects.filter(pk=client.pk).update(email="lucia@example.com")
        register_prospects(meta_payload())
        self.assertEqual(Client.objects.count(), 1)

    def test_several_prospects_coexist(self):
        register_prospects(meta_payload(sender="593991234567"))
        register_prospects(meta_payload(sender="593991234568"))
        self.assertEqual(Client.objects.count(), 2)


class SerializationTests(TestCase):
    def test_hides_the_placeholder_email_and_marks_the_source(self):
        data = serialize_client(register_prospects(meta_payload())[0])
        self.assertEqual(data["email"], "")
        self.assertEqual(data["source"], "whatsapp")

    def test_manual_client_keeps_its_email(self):
        client = Client.objects.create(name="Ana", email="ana@example.com")
        data = serialize_client(client)
        self.assertEqual(data["email"], "ana@example.com")
        self.assertEqual(data["source"], "manual")


class ProspectFormTests(TestCase):
    def setUp(self):
        self.prospect = register_prospects(meta_payload())[0]

    def values(self, email: str) -> dict:
        data = serialize_client(self.prospect)
        return {**data, "email": email}

    def test_editing_requires_a_real_email(self):
        form = ClientForm(self.values(""), instance=self.prospect)
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_editing_keeps_the_origin(self):
        form = ClientForm(self.values("lucia@example.com"), instance=self.prospect)
        self.assertTrue(form.is_valid(), form.errors)
        client = form.save()
        self.assertEqual(client.whatsapp_id, "593991234567")
        self.assertEqual(serialize_client(client)["email"], "lucia@example.com")

    def test_status_changes_without_a_real_email(self):
        form = ClientStatusForm({"status": "client"}, instance=self.prospect)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.save().status, Client.Status.CLIENT)


class ReceiveWebhookTests(TestCase):
    def receive(self, body: bytes, signature: str | None = None, secret: str = SECRET):
        return receive_webhook(body, sign(body, SECRET) if signature is None else signature, secret)

    def assert_rejected(self, code: str, status: int, **kwargs) -> None:
        with self.assertRaises(WebhookRejected) as caught:
            self.receive(**kwargs)
        self.assertEqual((caught.exception.code, caught.exception.status), (code, status))
        self.assertEqual(Client.objects.count(), 0)

    def test_valid_message_creates_a_prospect(self):
        clients = self.receive(json.dumps(meta_payload()).encode())
        self.assertEqual(len(clients), 1)

    def test_empty_secret_fails_closed(self):
        self.assert_rejected(
            "WEBHOOK_NOT_CONFIGURED", 503, body=b"{}", signature=sign(b"{}", ""), secret=""
        )

    def test_invalid_signature(self):
        self.assert_rejected("INVALID_SIGNATURE", 403, body=b"{}", signature="sha256=00")

    def test_signed_body_that_is_not_an_object(self):
        self.assert_rejected("INVALID_JSON", 400, body=b"[1, 2]")

    def test_simulated_message_goes_through_the_same_path(self):
        body = build_simulated_message()
        client = self.receive(body)[0]
        self.assertTrue(client.whatsapp_id.startswith("59399"))
        self.assertEqual(len(client.whatsapp_id), 12)
