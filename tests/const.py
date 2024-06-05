"""Constants for tests."""

from importlib import metadata

version = metadata.version("knocki")

BASE_URL = "https://production.knocki.com"

UNAUTHORIZED_HEADERS = {
    "User-Agent": f"PythonKnocki/{version}",
    "Accept": "application/json",
}

HEADERS = {
    **UNAUTHORIZED_HEADERS,
    "Authorization": "Bearer test",
}

