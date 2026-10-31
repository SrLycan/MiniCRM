from django.conf import settings
from django.contrib.auth.views import LoginView
from django.shortcuts import resolve_url
from django.http import HttpRequest, HttpResponse

from . import throttle
from .forms import LoginForm


class ThrottledLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True
    honor_next = False

    def get_success_url(self) -> str:
        """La aplicación siempre abre en el Panel; solo Admin vuelve a la página pedida."""
        if self.honor_next:
            return super().get_success_url()
        return resolve_url(settings.LOGIN_REDIRECT_URL)

    def get_context_data(self, **kwargs) -> dict:
        context = super().get_context_data(**kwargs)
        context["demo_hint"] = settings.DEMO_LOGIN_HINT and {
            "username": settings.DEMO_USERNAME,
            "password": settings.DEMO_PASSWORD,
        }
        return context

    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        if throttle.is_locked(request, request.POST.get("username", "")):
            form = self.get_form()
            form.is_bound = False
            context = self.get_context_data(
                form=form, lockout_message="Demasiados intentos. Espera 5 minutos."
            )
            return self.render_to_response(context, status=429)
        return super().post(request, *args, **kwargs)

    def form_invalid(self, form) -> HttpResponse:
        throttle.register_failure(self.request, self.request.POST.get("username", ""))
        return super().form_invalid(form)

    def form_valid(self, form) -> HttpResponse:
        throttle.reset_attempts(self.request, form.get_user().get_username())
        return super().form_valid(form)
