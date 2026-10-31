import json
from datetime import timedelta

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.db.models import Count, Q
from django.db.models.functions import TruncWeek
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from .forms import ClientForm
from .models import Client
from .serializers import serialize_client

PAGE_SIZE = 10
STATS_WEEKS = 6
RECENT_CLIENTS = 5
SORTABLE_FIELDS = {"name", "company", "email", "status", "created_at"}
DEFAULT_SORT = "-created_at"


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "clients/dashboard.html"
    extra_context = {"active_page": "dashboard"}


class ClientListView(LoginRequiredMixin, TemplateView):
    template_name = "clients/client_list.html"
    extra_context = {"active_page": "clients", "statuses": Client.Status.choices}


def error_response(code: str, message: str, status: int, errors: dict | None = None) -> JsonResponse:
    return JsonResponse({"code": code, "message": message, "errors": errors or {}}, status=status)


def validation_error_response(errors: dict) -> JsonResponse:
    return error_response("VALIDATION_ERROR", "Revisa los campos marcados.", 400, errors)


def parse_json_body(request: HttpRequest) -> dict | None:
    """Devuelve el cuerpo como diccionario, o None si no es un objeto JSON válido."""
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    return data if isinstance(data, dict) else None


class ApiView(View):
    """Base de la API: exige sesión y responde JSON en vez de redirigir al login."""

    def dispatch(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        if not request.user.is_authenticated:
            return error_response("AUTH_REQUIRED", "Tu sesión expiró. Inicia sesión.", 401)
        return super().dispatch(request, *args, **kwargs)

    def http_method_not_allowed(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        return error_response("METHOD_NOT_ALLOWED", "Método no permitido.", 405)


def save_client_form(form: ClientForm, success_status: int) -> JsonResponse:
    if not form.is_valid():
        return validation_error_response(form.errors)
    try:
        client = form.save()
    except IntegrityError:
        # Dos peticiones simultáneas pueden pasar la validación; la base de datos decide.
        return validation_error_response({"email": ["Ya existe un cliente con este correo."]})
    return JsonResponse(serialize_client(client), status=success_status)


class ClientCollectionApiView(ApiView):
    def get(self, request: HttpRequest) -> JsonResponse:
        clients = Client.objects.all()

        query = request.GET.get("q", "").strip()
        if query:
            clients = clients.filter(Q(name__icontains=query) | Q(company__icontains=query))

        status = request.GET.get("status", "")
        if status:
            if status not in Client.Status.values:
                return error_response("INVALID_FILTER", "El estado indicado no existe.", 400)
            clients = clients.filter(status=status)

        sort = request.GET.get("sort", DEFAULT_SORT)
        if sort.removeprefix("-") not in SORTABLE_FIELDS:
            sort = DEFAULT_SORT
        clients = clients.order_by(sort, "-id")

        page = Paginator(clients, PAGE_SIZE).get_page(request.GET.get("page"))
        return JsonResponse(
            {
                "results": [serialize_client(client) for client in page],
                "pagination": {
                    "page": page.number,
                    "pages": page.paginator.num_pages,
                    "total": page.paginator.count,
                    "page_size": PAGE_SIZE,
                },
            }
        )

    def post(self, request: HttpRequest) -> JsonResponse:
        data = parse_json_body(request)
        if data is None:
            return error_response("INVALID_JSON", "La solicitud no es válida.", 400)
        return save_client_form(ClientForm(data), success_status=201)


class ClientDetailApiView(ApiView):
    def dispatch(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        if request.user.is_authenticated and not Client.objects.filter(pk=kwargs["pk"]).exists():
            return error_response("CLIENT_NOT_FOUND", "El cliente ya no existe.", 404)
        return super().dispatch(request, *args, **kwargs)

    def get(self, request: HttpRequest, pk: int) -> JsonResponse:
        return JsonResponse(serialize_client(Client.objects.get(pk=pk)))

    def put(self, request: HttpRequest, pk: int) -> JsonResponse:
        data = parse_json_body(request)
        if data is None:
            return error_response("INVALID_JSON", "La solicitud no es válida.", 400)
        form = ClientForm(data, instance=Client.objects.get(pk=pk))
        return save_client_form(form, success_status=200)

    def delete(self, request: HttpRequest, pk: int) -> HttpResponse:
        Client.objects.filter(pk=pk).delete()
        return HttpResponse(status=204)


class ClientStatsApiView(ApiView):
    def get(self, request: HttpRequest) -> JsonResponse:
        counts = Client.objects.values("status").annotate(total=Count("id"))
        by_status = {status: 0 for status in Client.Status.values}
        by_status.update({row["status"]: row["total"] for row in counts})

        return JsonResponse(
            {
                "total": sum(by_status.values()),
                "by_status": by_status,
                "weekly_signups": self.weekly_signups(),
                "recent": [
                    serialize_client(client) for client in Client.objects.all()[:RECENT_CLIENTS]
                ],
            }
        )

    @staticmethod
    def weekly_signups() -> list[dict]:
        """Altas por semana, incluidas las semanas sin ninguna."""
        today = timezone.localdate()
        current_week = today - timedelta(days=today.weekday())
        weeks = [current_week - timedelta(weeks=n) for n in range(STATS_WEEKS - 1, -1, -1)]

        rows = (
            Client.objects.filter(created_at__date__gte=weeks[0])
            .annotate(week=TruncWeek("created_at"))
            .values("week")
            .annotate(total=Count("id"))
        )
        totals = {row["week"].date(): row["total"] for row in rows}
        return [{"week": week.isoformat(), "total": totals.get(week, 0)} for week in weeks]
