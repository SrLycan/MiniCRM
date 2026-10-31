import json
from datetime import timedelta
from unittest import mock

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import Client as HttpClient
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from clients.models import Client

COLLECTION_URL = reverse("clients:api_collection")
STATS_URL = reverse("clients:api_stats")


def detail_url(pk: int) -> str:
    return reverse("clients:api_detail", args=[pk])


def make_client(name: str = "Ana Ruiz", **overrides) -> Client:
    defaults = {
        "email": f"{name.lower().replace(' ', '.')}@example.com",
        "company": "Acme",
        "status": Client.Status.PROSPECT,
    }
    return Client.objects.create(name=name, **{**defaults, **overrides})


class ApiTestCase(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("revisor", password="clave-de-prueba")
        self.client.force_login(self.user)

    def send(self, method: str, url: str, data) -> object:
        body = data if isinstance(data, str) else json.dumps(data)
        return getattr(self.client, method)(url, body, content_type="application/json")


class ClientCreateTests(ApiTestCase):
    def test_creates_client(self):
        response = self.send(
            "post",
            COLLECTION_URL,
            {"name": "Juan Pérez", "email": "juan@example.com", "status": "client"},
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["status_label"], "Cliente")
        self.assertTrue(Client.objects.filter(email="juan@example.com").exists())

    def test_invalid_data_returns_field_errors(self):
        response = self.send("post", COLLECTION_URL, {"name": "", "email": "x", "status": "client"})
        self.assertEqual(response.status_code, 400)
        body = response.json()
        self.assertEqual(body["code"], "VALIDATION_ERROR")
        self.assertEqual(set(body["errors"]), {"name", "email"})

    def test_malformed_json_is_a_clear_error(self):
        for payload in ("{no es json", "[1, 2]"):
            response = self.send("post", COLLECTION_URL, payload)
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json()["code"], "INVALID_JSON")

    def test_database_race_on_email_is_reported_as_validation_error(self):
        with mock.patch("clients.views.ClientForm.save", side_effect=IntegrityError):
            response = self.send(
                "post",
                COLLECTION_URL,
                {"name": "Juan", "email": "juan@example.com", "status": "client"},
            )
        self.assertEqual(response.status_code, 400)
        self.assertIn("email", response.json()["errors"])

    def test_csrf_token_is_required(self):
        strict_client = HttpClient(enforce_csrf_checks=True)
        strict_client.force_login(self.user)
        response = strict_client.post(COLLECTION_URL, "{}", content_type="application/json")
        self.assertEqual(response.status_code, 403)


class ClientListTests(ApiTestCase):
    def names(self, **params) -> list[str]:
        response = self.client.get(COLLECTION_URL, params)
        self.assertEqual(response.status_code, 200)
        return [client["name"] for client in response.json()["results"]]

    def test_search_matches_name_or_company_ignoring_case(self):
        make_client("Ana Ruiz", company="Acme")
        make_client("Luis Mena", company="Nova")
        self.assertEqual(self.names(q="ana"), ["Ana Ruiz"])
        self.assertEqual(self.names(q="NOVA"), ["Luis Mena"])
        self.assertEqual(self.names(q="zzz"), [])

    def test_filter_by_status_combines_with_search(self):
        make_client("Ana Ruiz", status=Client.Status.CLIENT)
        make_client("Ana Mena", status=Client.Status.INACTIVE)
        self.assertEqual(self.names(q="ana", status="client"), ["Ana Ruiz"])

    def test_unknown_status_filter_is_rejected(self):
        response = self.client.get(COLLECTION_URL, {"status": "vip"})
        self.assertEqual(response.status_code, 400)

    def test_sorting_and_invalid_sort_fallback(self):
        make_client("Bruno")
        make_client("Ana")
        self.assertEqual(self.names(sort="name"), ["Ana", "Bruno"])
        self.assertEqual(self.names(sort="-name"), ["Bruno", "Ana"])
        self.assertEqual(self.names(sort="password"), ["Ana", "Bruno"])

    def test_pagination_metadata(self):
        for index in range(12):
            make_client(f"Cliente {index}")
        body = self.client.get(COLLECTION_URL, {"page": 2}).json()
        self.assertEqual(len(body["results"]), 2)
        self.assertEqual(
            body["pagination"], {"page": 2, "pages": 2, "total": 12, "page_size": 10}
        )

    def test_page_out_of_range_returns_last_page(self):
        make_client()
        body = self.client.get(COLLECTION_URL, {"page": 99}).json()
        self.assertEqual(body["pagination"]["page"], 1)


class ClientDetailTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.existing = make_client()

    def test_retrieve(self):
        response = self.client.get(detail_url(self.existing.pk))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["email"], self.existing.email)

    def test_update(self):
        response = self.send(
            "put",
            detail_url(self.existing.pk),
            {"name": "Ana Editada", "email": "nuevo@example.com", "status": "inactive"},
        )
        self.assertEqual(response.status_code, 200)
        self.existing.refresh_from_db()
        self.assertEqual(self.existing.name, "Ana Editada")
        self.assertEqual(self.existing.status, Client.Status.INACTIVE)

    def test_update_rejects_invalid_data(self):
        response = self.send(
            "put", detail_url(self.existing.pk), {"name": "", "email": "", "status": ""}
        )
        self.assertEqual(response.status_code, 400)

    def test_delete(self):
        response = self.client.delete(detail_url(self.existing.pk))
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Client.objects.filter(pk=self.existing.pk).exists())

    def test_missing_client_returns_json_404(self):
        url = detail_url(self.existing.pk + 1)
        for response in (self.client.get(url), self.client.delete(url), self.send("put", url, {})):
            self.assertEqual(response.status_code, 404)
            self.assertEqual(response.json()["code"], "CLIENT_NOT_FOUND")

    def test_unsupported_method_returns_json_405(self):
        response = self.client.patch(detail_url(self.existing.pk))
        self.assertEqual(response.status_code, 405)
        self.assertEqual(response.json()["code"], "METHOD_NOT_ALLOWED")


class ClientStatsTests(ApiTestCase):
    def test_totals_include_states_without_clients(self):
        make_client("Ana", status=Client.Status.CLIENT)
        make_client("Luis", status=Client.Status.CLIENT)
        body = self.client.get(STATS_URL).json()
        self.assertEqual(body["total"], 2)
        self.assertEqual(body["by_status"], {"prospect": 0, "client": 2, "inactive": 0})

    def test_weekly_signups_cover_six_weeks_and_ignore_older_clients(self):
        make_client("Reciente")
        old_client = make_client("Antiguo")
        Client.objects.filter(pk=old_client.pk).update(
            created_at=timezone.now() - timedelta(weeks=20)
        )
        signups = self.client.get(STATS_URL).json()["weekly_signups"]
        self.assertEqual(len(signups), 6)
        self.assertEqual(sum(week["total"] for week in signups), 1)
        self.assertEqual(signups[-1]["total"], 1)

    def test_recent_lists_latest_five(self):
        for index in range(7):
            make_client(f"Cliente {index}")
        recent = self.client.get(STATS_URL).json()["recent"]
        self.assertEqual(len(recent), 5)
        self.assertEqual(recent[0]["name"], "Cliente 6")
