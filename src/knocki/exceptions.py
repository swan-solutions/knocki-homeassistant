"""Asynchronous Python client for Knocki."""


class KnockiError(Exception):
    """Generic exception."""


class KnockiConnectionError(KnockiError):
    """Knocki connection exception."""
