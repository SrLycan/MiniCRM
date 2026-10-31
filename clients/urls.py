from django.urls import path

from . import views

app_name = "clients"

urlpatterns = [
    path("", views.DashboardView.as_view(), name="dashboard"),
    path("clientes/", views.ClientListView.as_view(), name="client_list"),
    path("api/clients/", views.ClientCollectionApiView.as_view(), name="api_collection"),
    path("api/clients/stats/", views.ClientStatsApiView.as_view(), name="api_stats"),
    path(
        "api/clients/simulate-whatsapp/",
        views.WhatsAppSimulationApiView.as_view(),
        name="api_simulate_whatsapp",
    ),
    path("api/clients/<int:pk>/", views.ClientDetailApiView.as_view(), name="api_detail"),
    path("api/webhooks/whatsapp/", views.WhatsAppWebhookView.as_view(), name="whatsapp_webhook"),
]
