from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "Órbita CRM"
admin.site.site_title = "Órbita CRM"
admin.site.index_title = "Administración"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("accounts.urls")),
    path("", include("clients.urls")),
]
