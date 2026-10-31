"""Bloqueo temporal del login tras varios intentos fallidos por usuario e IP."""

import hashlib

from django.conf import settings
from django.core.cache import cache
from django.http import HttpRequest


def _attempts_key(request: HttpRequest, username: str) -> str:
    identity = f"{username.strip().lower()}|{request.META.get('REMOTE_ADDR', '')}"
    return f"login-attempts:{hashlib.sha256(identity.encode()).hexdigest()}"


def is_locked(request: HttpRequest, username: str) -> bool:
    attempts = cache.get(_attempts_key(request, username), 0)
    return attempts >= settings.LOGIN_MAX_ATTEMPTS


def register_failure(request: HttpRequest, username: str) -> None:
    key = _attempts_key(request, username)
    cache.add(key, 0, timeout=settings.LOGIN_LOCKOUT_SECONDS)
    cache.incr(key)


def reset_attempts(request: HttpRequest, username: str) -> None:
    cache.delete(_attempts_key(request, username))
