"""Asynchronous Python client for Knocki."""

from __future__ import annotations

import asyncio
from asyncio import timeout
from dataclasses import dataclass
from importlib import metadata
from typing import TYPE_CHECKING, Any

import orjson
from aiohttp import ClientSession
from aiohttp.hdrs import METH_GET, METH_PUT, METH_POST
from yarl import URL

from knocki.exceptions import KnockiConnectionError
from knocki.models import TokenResponse

if TYPE_CHECKING:
    from typing_extensions import Self


VERSION = metadata.version(__package__)

_URLS = {
    True: "staging.knocki.com",
    False: "production.knocki.com",
}

@dataclass
class KnockiClient:
    """Main class for handling connections with Knocki."""

    token: str | None = None
    session: ClientSession | None = None
    staging: bool = False
    request_timeout: int = 10
    _close_session: bool = False

    async def _request(
        self,
        uri: str,
        *,
        method: str = METH_GET,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Handle a request to Knocki."""
        url = URL.build(scheme="https", host=_URLS[self.staging]).joinpath(uri)

        headers = {
            "User-Agent": f"PythonKnocki/{VERSION}",
            "Accept": "application/json",
        }

        if self.session is None:
            self.session = ClientSession()
            self._close_session = True

        try:
            async with timeout(self.request_timeout):
                response = await self.session.request(
                    method,
                    url,
                    headers=headers,
                    json=data,
                )
        except asyncio.TimeoutError as exception:
            msg = "Timeout occurred while connecting to Knocki"
            raise KnockiConnectionError(msg) from exception

        content_type = response.headers.get("Content-Type", "")
        if response.status != 200 or "application/json" not in content_type:
            text = await response.text()
            msg = "Unexpected response from Knocki"
            raise KnockiConnectionError(
                msg,
                {"Content-Type": content_type, "response": text},
            )

        return orjson.loads(await response.text())

    async def login(self, email: str, password: str) -> TokenResponse:
        """Login to Knocki."""
        data = {
            "data": [
                {
                    "type": "tokens",
                    "attributes": {
                        "email": email,
                        "password": password,
                        "type": "auth"
                    },
                }
            ]
        }

        response = await self._request("tokens", method=METH_POST, data=data)

        return TokenResponse.from_api(response)

    async def close(self) -> None:
        """Close open client session."""
        if self.session and self._close_session:
            await self.session.close()

    async def __aenter__(self) -> Self:
        """Async enter.

        Returns
        -------
            The KnockiClient object.

        """
        return self

    async def __aexit__(self, *_exc_info: object) -> None:
        """Async exit.

        Args:
        ----
            _exc_info: Exec type.

        """
        await self.close()
