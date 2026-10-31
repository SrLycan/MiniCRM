from datetime import timedelta

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.db.models import Count, Max, OuterRef, Subquery
from django.db.models.functions import TruncWeek
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView

from .forms import ClientForm, ClientStatusForm, WhatsAppReplyForm
from .models import Client, WhatsAppMessage, normalize_search_text
from .serializers import parse_json_object, serialize_client, serialize_message
from .whatsapp import (
    WebhookRejected,
    build_simulated_message,
    build_simulated_reply,
    receive_webhook,
    sign,
    whatsapp_number_of,
)

PAGE_SIZE = 10
MAX_PAGE_SIZE = 100
SEARCH_MAX_LENGTH = 100
MAX_CONVERSATIONS = 100
MAX_CHAT_MESSAGES = 200
STATS_WEEKS = 6
RECENT_CLIENTS = 5
SORTABLE_FIELDS = {"name", "company", "email", "status", "created_at"}
DEFAULT_SORT = "-created_at"


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "clients/dashboard.html"
    extra_context = {"active_page": "dashboard", "statuses": Client.Status.choices}


class ClientListView(LoginRequiredMixin, TemplateView):
    template_name = "clients/client_list.html"
    extra_context = {"active_page": "clients", "statuses": Client.Status.choices}


class BoardView(LoginRequiredMixin, TemplateView):
    template_name = "clients/board.html"
    extra_context = {"active_page": "board", "statuses": Client.Status.choices}


class WhatsAppView(LoginRequiredMixin, TemplateView):
    template_name = "clients/whatsapp.html"
    extra_context = {"active_page": "whatsapp", "statuses": Client.Status.choices}


def error_response(code: str, message: str, status: int, errors: dict | None = None) -> JsonResponse:
    return JsonResponse({"code": code, "message": message, "errors": errors or {}}, status=status)


def validation_error_response(errors: dict) -> JsonResponse:
    return error_response("VALIDATION_ERROR", "Revisa los campos marcados.", 400, errors)


def parse_page_size(value: str | None) -> int:
    """Admite un tamaño de página propio, acotado, y usa el normal si no es un número."""
    try:
        return min(max(int(value), 1), MAX_PAGE_SIZE)
    except (TypeError, ValueError):
        return PAGE_SIZE


class ApiView(View):
    """Base de la API: exige sesión y responde JSON en vez de redirigir al login."""

    def dispatch(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        if not request.user.is_authenticated:
            return error_response("AUTH_REQUIRED", "Tu sesión expiró. Inicia sesión.", 401)
        return super().dispatch(request, *args, **kwargs)

    def http_method_not_allowed(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        return error_response("METHOD_NOT_ALLOWED", "Método no permitido.", 405)


def save_client_form(form: ClientForm | ClientStatusForm, success_status: int) -> JsonResponse:
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

        query = request.GET.get("q", "").strip()[:SEARCH_MAX_LENGTH]
        if query:
            clients = clients.filter(search_text__contains=normalize_search_text(query))

        status = request.GET.get("status", "")
        if status:
            if status not in Client.Status.values:
                return error_response("INVALID_FILTER", "El estado indicado no existe.", 400)
            clients = clients.filter(status=status)

        sort = request.GET.get("sort", DEFAULT_SORT)
        if sort.removeprefix("-") not in SORTABLE_FIELDS:
            sort = DEFAULT_SORT
        clients = clients.order_by(sort, "-id")

        page_size = parse_page_size(request.GET.get("page_size"))
        page = Paginator(clients, page_size).get_page(request.GET.get("page"))
        return JsonResponse(
            {
                "results": [serialize_client(client) for client in page],
                "pagination": {
                    "page": page.number,
                    "pages": page.paginator.num_pages,
                    "total": page.paginator.count,
                    "page_size": page_size,
                },
            }
        )

    def post(self, request: HttpRequest) -> JsonResponse:
        data = parse_json_object(request.body)
        if data is None:
            return error_response("INVALID_JSON", "La solicitud no es válida.", 400)
        return save_client_form(ClientForm(data), success_status=201)


class ClientScopedApiView(ApiView):
    """Base de las rutas de un cliente: responde 404 si ya no existe."""

    def dispatch(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        if request.user.is_authenticated and not Client.objects.filter(pk=kwargs["pk"]).exists():
            return error_response("CLIENT_NOT_FOUND", "El cliente ya no existe.", 404)
        return super().dispatch(request, *args, **kwargs)


class ClientDetailApiView(ClientScopedApiView):
    def get(self, request: HttpRequest, pk: int) -> JsonResponse:
        return JsonResponse(serialize_client(Client.objects.get(pk=pk)))

    def put(self, request: HttpRequest, pk: int) -> JsonResponse:
        data = parse_json_object(request.body)
        if data is None:
            return error_response("INVALID_JSON", "La solicitud no es válida.", 400)
        form = ClientForm(data, instance=Client.objects.get(pk=pk))
        return save_client_form(form, success_status=200)

    def patch(self, request: HttpRequest, pk: int) -> JsonResponse:
        data = parse_json_object(request.body)
        if data is None:
            return error_response("INVALID_JSON", "La solicitud no es válida.", 400)
        form = ClientStatusForm(data, instance=Client.objects.get(pk=pk))
        return save_client_form(form, success_status=200)

    def delete(self, request: HttpRequest, pk: int) -> HttpResponse:
        Client.objects.filter(pk=pk).delete()
        return HttpResponse(status=204)


@method_decorator(csrf_exempt, name="dispatch")
class WhatsAppWebhookView(View):
    """Sin sesión ni CSRF: quien llama es un servicio y lo autentica la firma del cuerpo."""

    http_method_not_allowed = ApiView.http_method_not_allowed

    def post(self, request: HttpRequest) -> JsonResponse:
        signature = request.headers.get("X-Hub-Signature-256", "")
        try:
            receive_webhook(request.body, signature, settings.WHATSAPP_APP_SECRET)
        except WebhookRejected as rejection:
            return error_response(rejection.code, rejection.message, rejection.status)
        # Meta reintenta si no recibe un 200, también cuando el mensaje ya se procesó.
        return JsonResponse({"status": "ok"})


def receive_simulated_message(body: bytes) -> list[WhatsAppMessage]:
    """Firma aquí el mensaje para que el secreto nunca llegue al navegador."""
    secret = settings.WHATSAPP_APP_SECRET
    return receive_webhook(body, sign(body, secret), secret)


class WhatsAppSimulationApiView(ApiView):
    def post(self, request: HttpRequest) -> JsonResponse:
        try:
            message = receive_simulated_message(build_simulated_message())[0]
        except WebhookRejected as rejection:
            return error_response(rejection.code, rejection.message, rejection.status)
        return JsonResponse(serialize_client(message.client), status=201)


class ConversationListApiView(ApiView):
    def get(self, request: HttpRequest) -> JsonResponse:
        latest = WhatsAppMessage.objects.filter(client=OuterRef("pk")).order_by("-created_at", "-id")
        clients = (
            Client.objects.filter(messages__isnull=False)
            .annotate(
                last_message_at=Max("messages__created_at"),
                last_message_body=Subquery(latest.values("body")[:1]),
                last_message_direction=Subquery(latest.values("direction")[:1]),
            )
            .order_by("-last_message_at")[:MAX_CONVERSATIONS]
        )
        return JsonResponse(
            {
                "results": [
                    {
                        "client": serialize_client(client),
                        "last_message": {
                            "body": client.last_message_body,
                            "direction": client.last_message_direction,
                            "created_at": client.last_message_at.isoformat(),
                        },
                    }
                    for client in clients
                ]
            }
        )


class ConversationDetailApiView(ClientScopedApiView):
    def get(self, request: HttpRequest, pk: int) -> JsonResponse:
        client = Client.objects.get(pk=pk)
        latest = client.messages.order_by("-created_at", "-id")[:MAX_CHAT_MESSAGES]
        return JsonResponse(
            {
                "client": serialize_client(client),
                "can_chat": bool(whatsapp_number_of(client)),
                "messages": [serialize_message(message) for message in reversed(latest)],
            }
        )


def chat_unavailable_response() -> JsonResponse:
    message = "Este cliente necesita un teléfono válido para chatear."
    return error_response("PHONE_REQUIRED", message, 400)


class ConversationMessagesApiView(ClientScopedApiView):
    def post(self, request: HttpRequest, pk: int) -> JsonResponse:
        client = Client.objects.get(pk=pk)
        if not whatsapp_number_of(client):
            return chat_unavailable_response()

        data = parse_json_object(request.body)
        if data is None:
            return error_response("INVALID_JSON", "La solicitud no es válida.", 400)
        form = WhatsAppReplyForm(data)
        if not form.is_valid():
            return validation_error_response(form.errors)

        message = client.messages.create(
            direction=WhatsAppMessage.Direction.OUTBOUND, body=form.cleaned_data["body"]
        )
        return JsonResponse(serialize_message(message), status=201)


class ConversationSimulatedReplyApiView(ClientScopedApiView):
    def post(self, request: HttpRequest, pk: int) -> JsonResponse:
        client = Client.objects.get(pk=pk)
        if not whatsapp_number_of(client):
            return chat_unavailable_response()
        try:
            message = receive_simulated_message(build_simulated_reply(client))[0]
        except WebhookRejected as rejection:
            return error_response(rejection.code, rejection.message, rejection.status)
        return JsonResponse(serialize_message(message), status=201)


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
