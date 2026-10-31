from django.contrib import admin
from django.urls import include, path

from accounts.views import ThrottledLoginView

# Admin usa el mismo login con bloqueo. Sin redirección automática, porque una sesión sin
# permisos de staff volvería aquí en bucle.
admin.site.login = ThrottledLoginView.as_view(redirect_authenticated_user=False)
admin.site.site_header = "Órbita CRM"
admin.site.site_title = "Órbita CRM"
admin.site.index_title = "Administración"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("accounts.urls")),
    path("", include("clients.urls")),
]
