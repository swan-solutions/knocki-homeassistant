"""Asynchronous Python client for Knocki."""

from __future__ import annotations

from asyncio import timeout
from dataclasses import dataclass
from importlib import metadata
from typing import TYPE_CHECKING, Any

from aiohttp import ClientSession
from aiohttp.hdrs import METH_GET, METH_PUT
from yarl import URL

if TYPE_CHECKING:
    from typing_extensions import Self


VERSION = metadata.version(__package__)


@dataclass
class KnockiClient:
    """Main class for handling connections with Knocki."""

    host: str
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
    ) -> str:
        """Handle a request to Knocki."""
        url = URL.build(scheme="http", host=self.host).joinpath(uri)

        headers = {
            "User-Agent": f"PythonKnocki/{VERSION}",
            "Accept": "application/json",
        }

        if self.session is None:
            self.session = ClientSession()
            self._close_session = True

        async with timeout(self.request_timeout):
            response = await self.session.request(
                method,
                url,
                headers=headers,
                json=data,
            )

        if response.status != 200:
            content_type = response.headers.get("Content-Type", "")
            text = await response.text()
            msg = "Unexpected response from Knocki"
            raise AirGradientConnectionError(
                msg,
                {"Content-Type": content_type, "response": text},
            )

        return await response.text()

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
