"""Bloqueo temporal del login por usuario e IP, y por IP para frenar barridos de usuarios."""

import hashlib

from django.conf import settings
from django.core.cache import cache
from django.http import HttpRequest


def _client_ip(request: HttpRequest) -> str:
    return request.META.get("REMOTE_ADDR", "")


def _cache_key(prefix: str, identity: str) -> str:
    return f"{prefix}:{hashlib.sha256(identity.encode()).hexdigest()}"


def _attempts_key(request: HttpRequest, username: str) -> str:
    return _cache_key("login-attempts", f"{username.strip().lower()}|{_client_ip(request)}")


def _ip_attempts_key(request: HttpRequest) -> str:
    return _cache_key("login-attempts-ip", _client_ip(request))


def is_locked(request: HttpRequest, username: str) -> bool:
    user_attempts = cache.get(_attempts_key(request, username), 0)
    ip_attempts = cache.get(_ip_attempts_key(request), 0)
    return (
        user_attempts >= settings.LOGIN_MAX_ATTEMPTS
        or ip_attempts >= settings.LOGIN_MAX_ATTEMPTS_PER_IP
    )


def register_failure(request: HttpRequest, username: str) -> None:
    for key in (_attempts_key(request, username), _ip_attempts_key(request)):
        cache.add(key, 0, timeout=settings.LOGIN_LOCKOUT_SECONDS)
        cache.incr(key)


def reset_attempts(request: HttpRequest, username: str) -> None:
    cache.delete(_attempts_key(request, username))
