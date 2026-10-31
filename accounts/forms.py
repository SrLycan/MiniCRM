from django import forms
from django.contrib.auth.forms import AuthenticationForm

PASSWORD_MAX_LENGTH = 128


class LoginForm(AuthenticationForm):
    """Rechaza contraseñas desmedidas antes de gastar tiempo en calcular su hash."""

    password = forms.CharField(
        label="Contraseña",
        strip=False,
        max_length=PASSWORD_MAX_LENGTH,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )
