from django.urls import path

from . import views

app_name = "clients"

urlpatterns = [
    path("", views.DashboardView.as_view(), name="dashboard"),
    path("clientes/", views.ClientListView.as_view(), name="client_list"),
    path("tablero/", views.BoardView.as_view(), name="board"),
    path("whatsapp/", views.WhatsAppView.as_view(), name="whatsapp"),
    path("api/clients/", views.ClientCollectionApiView.as_view(), name="api_collection"),
    path("api/clients/stats/", views.ClientStatsApiView.as_view(), name="api_stats"),
    path(
        "api/clients/simulate-whatsapp/",
        views.WhatsAppSimulationApiView.as_view(),
        name="api_simulate_whatsapp",
    ),
    path("api/clients/<int:pk>/", views.ClientDetailApiView.as_view(), name="api_detail"),
    path(
        "api/conversations/",
        views.ConversationListApiView.as_view(),
        name="api_conversations",
    ),
    path(
        "api/conversations/<int:pk>/",
        views.ConversationDetailApiView.as_view(),
        name="api_conversation",
    ),
    path(
        "api/conversations/<int:pk>/messages/",
        views.ConversationMessagesApiView.as_view(),
        name="api_conversation_messages",
    ),
    path(
        "api/conversations/<int:pk>/simulate-reply/",
        views.ConversationSimulatedReplyApiView.as_view(),
        name="api_conversation_simulate_reply",
    ),
    path("api/webhooks/whatsapp/", views.WhatsAppWebhookView.as_view(), name="whatsapp_webhook"),
]
