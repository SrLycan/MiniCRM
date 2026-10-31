import json

from django.test import SimpleTestCase, TestCase

from clients.forms import ClientForm, ClientStatusForm
from clients.models import Client, WhatsAppMessage, normalize_phone
from clients.serializers import serialize_client
from clients.whatsapp import (
    WebhookRejected,
    build_simulated_message,
    build_simulated_reply,
    clean_name,
    extract_messages,
    find_or_create_client,
    is_valid_signature,
    receive_webhook,
    register_messages,
    sign,
    whatsapp_number_of,
)

SECRET = "secreto-de-prueba"


def meta_payload(
    sender="593991234567", name="Lucía Paredes", message_id="wamid.1", text="Hola"
) -> dict:
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "contacts": [{"profile": {"name": name}, "wa_id": sender}],
                            "messages": [
                                {
                                    "from": sender,
                                    "id": message_id,
                                    "type": "text",
                                    "text": {"body": text},
                                }
                            ],
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


class ExtractMessagesTests(SimpleTestCase):
    def test_reads_number_name_id_and_text(self):
        message = extract_messages(meta_payload())[0]
        self.assertEqual(message.whatsapp_id, "593991234567")
        self.assertEqual(message.name, "Lucía Paredes")
        self.assertEqual(message.message_id, "wamid.1")
        self.assertEqual(message.text, "Hola")

    def test_ignores_delivery_events(self):
        payload = {"entry": [{"changes": [{"value": {"statuses": [{"id": "wamid.1"}]}}]}]}
        self.assertEqual(extract_messages(payload), [])

    def test_ignores_invalid_numbers(self):
        for sender in ("123", "1" * 16, "59399abc", "+593991234567", 593991234567):
            self.assertEqual(extract_messages(meta_payload(sender=sender)), [])

    def test_message_without_text_keeps_a_notice(self):
        payload = meta_payload()
        del payload["entry"][0]["changes"][0]["value"]["messages"][0]["text"]
        self.assertEqual(extract_messages(payload)[0].text, "[Mensaje sin texto]")

    def test_limits_the_text_and_the_identifier(self):
        message = extract_messages(meta_payload(text="a" * 5000, message_id="b" * 200))[0]
        self.assertEqual(len(message.text), 4096)
        self.assertIsNone(message.message_id)

    def test_survives_unexpected_shapes(self):
        for payload in (
            {},
            {"entry": "x"},
            {"entry": [1, None]},
            {"entry": [{"changes": [{"value": "x"}]}]},
            {"entry": [{"changes": [{"value": {"messages": [{}], "contacts": [{"profile": 1}]}}]}]},
        ):
            self.assertEqual(extract_messages(payload), [])


class NormalizePhoneTests(SimpleTestCase):
    def test_all_formats_of_a_number_match(self):
        for phone in ("0991234567", "099 123 4567", "+593 99 123 4567", "593991234567"):
            self.assertEqual(normalize_phone(phone), "991234567")

    def test_landline_and_foreign_numbers(self):
        self.assertEqual(normalize_phone("+593 2 234 5605"), "22345605")
        self.assertEqual(normalize_phone("+1 555 010 9999"), "15550109999")
        self.assertEqual(normalize_phone(""), "")


class CleanNameTests(SimpleTestCase):
    def test_normalizes_spaces(self):
        self.assertEqual(clean_name("  Ana   Ruiz ", "593991234567"), "Ana Ruiz")

    def test_falls_back_to_the_number(self):
        for name in (None, "", " ", "A", 7):
            self.assertEqual(clean_name(name, "593991234567"), "WhatsApp +593991234567")

    def test_limits_the_length(self):
        self.assertEqual(len(clean_name("a" * 200, "593991234567")), 120)


class RegisterMessagesTests(TestCase):
    def test_creates_a_prospect_with_its_message(self):
        message = register_messages(meta_payload())[0]
        client = message.client
        self.assertEqual(client.name, "Lucía Paredes")
        self.assertEqual(client.phone, "+593991234567")
        self.assertEqual(client.status, Client.Status.PROSPECT)
        self.assertEqual(client.whatsapp_id, "593991234567")
        self.assertEqual(client.search_text, "lucia paredes ")
        self.assertEqual(message.body, "Hola")
        self.assertEqual(message.direction, WhatsAppMessage.Direction.INBOUND)

    def test_same_number_keeps_one_client_and_adds_messages(self):
        first = register_messages(meta_payload())[0].client
        second = register_messages(meta_payload(name="Otro", message_id="wamid.2"))[0].client
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(Client.objects.count(), 1)
        self.assertEqual(first.messages.count(), 2)
        second.refresh_from_db()
        self.assertEqual(second.name, "Lucía Paredes")

    def test_repeated_delivery_does_not_duplicate_the_message(self):
        for _ in range(2):
            register_messages(meta_payload())
        self.assertEqual(WhatsAppMessage.objects.count(), 1)

    def test_several_prospects_coexist(self):
        register_messages(meta_payload(sender="593991234567"))
        register_messages(meta_payload(sender="593991234568", message_id="wamid.2"))
        self.assertEqual(Client.objects.count(), 2)

    def test_real_email_keeps_the_prospect_identified(self):
        client = register_messages(meta_payload())[0].client
        Client.objects.filter(pk=client.pk).update(email="lucia@example.com")
        register_messages(meta_payload(message_id="wamid.2"))
        self.assertEqual(Client.objects.count(), 1)


class RegisteredClientTests(TestCase):
    """El cliente que ya existe conserva sus datos cuando escribe por WhatsApp."""

    def setUp(self):
        self.client_record = Client.objects.create(
            name="Mateo Guerrero",
            company="Andes Logística",
            email="mateo@example.com",
            phone="0991234567",
            status=Client.Status.CLIENT,
        )

    def test_message_goes_to_the_existing_client(self):
        message = register_messages(meta_payload(name="Mateo G."))[0]
        self.assertEqual(message.client.pk, self.client_record.pk)
        self.assertEqual(Client.objects.count(), 1)

    def test_keeps_email_company_name_and_status(self):
        register_messages(meta_payload(name="Mateo G."))
        self.client_record.refresh_from_db()
        self.assertEqual(self.client_record.email, "mateo@example.com")
        self.assertEqual(self.client_record.company, "Andes Logística")
        self.assertEqual(self.client_record.name, "Mateo Guerrero")
        self.assertEqual(self.client_record.status, Client.Status.CLIENT)
        self.assertEqual(self.client_record.phone, "0991234567")
        self.assertEqual(self.client_record.whatsapp_id, "593991234567")

    def test_phone_written_with_spaces_also_matches(self):
        Client.objects.filter(pk=self.client_record.pk).delete()
        other = Client.objects.create(name="Ana", email="ana@example.com", phone="+593 99 123 4567")
        self.assertEqual(find_or_create_client("593991234567", "Ana R.").pk, other.pk)

    def test_oldest_client_wins_when_a_phone_is_repeated(self):
        Client.objects.create(name="Copia", email="copia@example.com", phone="0991234567")
        client = find_or_create_client("593991234567", "Mateo G.")
        self.assertEqual(client.pk, self.client_record.pk)

    def test_client_without_phone_is_not_matched(self):
        Client.objects.create(name="Sin teléfono", email="sin@example.com")
        client = find_or_create_client("593990000000", "Nuevo")
        self.assertEqual(client.name, "Nuevo")


class WhatsAppNumberTests(TestCase):
    def number_for(self, phone: str) -> str:
        return whatsapp_number_of(Client(phone_key=normalize_phone(phone), phone=phone))

    def test_local_number_gets_the_country_code(self):
        self.assertEqual(self.number_for("0991234567"), "593991234567")

    def test_landline_gets_the_country_code(self):
        self.assertEqual(self.number_for("+593 2 234 5605"), "59322345605")

    def test_foreign_number_stays_the_same(self):
        self.assertEqual(self.number_for("+1 555 010 9999"), "15550109999")

    def test_missing_phone_gives_nothing(self):
        self.assertEqual(self.number_for(""), "")

    def test_simulated_reply_keeps_the_client(self):
        client = Client.objects.create(name="Ana", email="ana@example.com", phone="0991234567")
        body = build_simulated_reply(client)
        stored = receive_webhook(body, sign(body, SECRET), SECRET)[0]
        self.assertEqual(stored.client.pk, client.pk)


class SerializationTests(TestCase):
    def test_hides_the_placeholder_email_and_marks_the_source(self):
        data = serialize_client(register_messages(meta_payload())[0].client)
        self.assertEqual(data["email"], "")
        self.assertEqual(data["source"], "whatsapp")

    def test_manual_client_keeps_its_email(self):
        client = Client.objects.create(name="Ana", email="ana@example.com")
        data = serialize_client(client)
        self.assertEqual(data["email"], "ana@example.com")
        self.assertEqual(data["source"], "manual")


class ProspectFormTests(TestCase):
    def setUp(self):
        self.prospect = register_messages(meta_payload())[0].client

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
        messages = self.receive(json.dumps(meta_payload()).encode())
        self.assertEqual(len(messages), 1)

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
        client = self.receive(body)[0].client
        self.assertTrue(client.whatsapp_id.startswith("59399"))
        self.assertEqual(len(client.whatsapp_id), 12)
