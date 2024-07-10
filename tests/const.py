"""Constants for tests."""

BASE_URL = "https://production.knocki.com"

UNAUTHORIZED_HEADERS = {
    "User-Agent": "com.knocki.mobileapp",
    "Accept": "application/json",
}

HEADERS = {
    **UNAUTHORIZED_HEADERS,
    "Authorization": "Bearer test",
}
