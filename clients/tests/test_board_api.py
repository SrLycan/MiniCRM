from clients.models import Client

from .test_api import COLLECTION_URL, ApiTestCase, detail_url, make_client


class ClientStatusPatchTests(ApiTestCase):
    def test_changes_only_the_status(self):
        client = make_client(phone="0991234567")
        response = self.send("patch", detail_url(client.pk), {"status": "client"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status_label"], "Cliente")

        client.refresh_from_db()
        self.assertEqual(client.status, Client.Status.CLIENT)
        self.assertEqual(client.phone, "0991234567")

    def test_other_fields_in_the_body_are_ignored(self):
        client = make_client()
        self.send("patch", detail_url(client.pk), {"status": "client", "name": "Cambiado"})
        client.refresh_from_db()
        self.assertEqual(client.name, "Ana Ruiz")

    def test_invalid_status_returns_field_error(self):
        client = make_client()
        response = self.send("patch", detail_url(client.pk), {"status": "ganado"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["errors"]["status"], ["Selecciona un estado válido."])

    def test_missing_status_returns_field_error(self):
        client = make_client()
        response = self.send("patch", detail_url(client.pk), {})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["errors"]["status"], ["Selecciona un estado."])

    def test_malformed_json_is_a_clear_error(self):
        client = make_client()
        response = self.send("patch", detail_url(client.pk), "{no es json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "INVALID_JSON")

    def test_missing_client_returns_404(self):
        response = self.send("patch", detail_url(999), {"status": "client"})
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["code"], "CLIENT_NOT_FOUND")

    def test_requires_session(self):
        client = make_client()
        self.client.logout()
        response = self.send("patch", detail_url(client.pk), {"status": "client"})
        self.assertEqual(response.status_code, 401)


class PageSizeTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        for number in range(12):
            make_client(f"Cliente {number}")

    def list_with(self, page_size: str) -> dict:
        return self.client.get(COLLECTION_URL, {"page_size": page_size}).json()

    def test_default_page_size_stays_at_ten(self):
        body = self.client.get(COLLECTION_URL).json()
        self.assertEqual(len(body["results"]), 10)
        self.assertEqual(body["pagination"]["page_size"], 10)

    def test_accepts_a_custom_size(self):
        body = self.list_with("50")
        self.assertEqual(len(body["results"]), 12)
        self.assertEqual(body["pagination"]["page_size"], 50)

    def test_size_is_capped(self):
        self.assertEqual(self.list_with("5000")["pagination"]["page_size"], 100)
        self.assertEqual(self.list_with("0")["pagination"]["page_size"], 1)

    def test_invalid_size_uses_the_default(self):
        self.assertEqual(self.list_with("muchos")["pagination"]["page_size"], 10)
