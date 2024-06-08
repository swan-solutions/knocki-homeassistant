"""Asynchronous Python client for Knocki."""

from __future__ import annotations

import asyncio
from asyncio import timeout
from dataclasses import dataclass, field
from importlib import metadata
from typing import TYPE_CHECKING, Any, Callable

from aiohttp import ClientSession
from aiohttp.hdrs import METH_DELETE, METH_GET, METH_POST
from mashumaro.codecs.orjson import ORJSONDecoder
import orjson
from yarl import URL

from knocki.exceptions import KnockiConnectionError
from knocki.models import Event, EventType, TokenResponse, Trigger

if TYPE_CHECKING:
    from typing_extensions import Self


VERSION = metadata.version(__package__)

_URLS = {
    True: "staging.knocki.com",
    False: "production.knocki.com",
}

WEB_SOCKET_URL = "wss://ivg6nmkds4.execute-api.us-east-2.amazonaws.com/production"


@dataclass
class KnockiClient:
    """Main class for handling connections with Knocki."""

    token: str | None = None
    session: ClientSession | None = None
    staging: bool = False
    request_timeout: int = 10
    _close_session: bool = False
    _listeners: dict[EventType, list[Callable[[Event], None]]] = field(
        default_factory=dict
    )

    async def _request(
        self,
        uri: str,
        *,
        method: str = METH_GET,
        data: dict[str, Any] | None = None,
    ) -> str:
        """Handle a request to Knocki."""
        url = URL.build(scheme="https", host=_URLS[self.staging]).joinpath(uri)

        headers = {
            "User-Agent": f"PythonKnocki/{VERSION}",
            "Accept": "application/json",
        }

        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

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

        return await response.text()

    async def login(self, email: str, password: str) -> TokenResponse:
        """Login to Knocki."""
        data = {
            "data": [
                {
                    "type": "tokens",
                    "attributes": {
                        "email": email,
                        "password": password,
                        "type": "auth",
                    },
                }
            ]
        }

        response = await self._request("tokens", method=METH_POST, data=data)

        return TokenResponse.from_api(orjson.loads(response))  # pylint: disable=maybe-no-member

    async def link(self) -> None:
        """Link Knocki account."""
        await self._request("accounts/homeassistant/v1/link", method=METH_POST)

    async def unlink(self) -> None:
        """Unlink Knocki account."""
        await self._request("accounts/homeassistant", method=METH_DELETE)

    async def get_triggers(self) -> list[Trigger]:
        """Get triggers from Knocki."""
        response = await self._request("actions/homeassistant")
        return ORJSONDecoder(list[Trigger]).decode(response)

    async def start_websocket(self) -> None:
        """Start websocket connection."""
        url = WEB_SOCKET_URL + f"?token={self.token}"

        if self.session is None:
            self.session = ClientSession()
            self._close_session = True

        try:
            async with self.session.ws_connect(url) as ws:
                async for msg in ws:
                    event = Event.from_json(msg.data)  # pylint: disable=maybe-no-member
                    for listener in self._listeners.get(event.event, []):
                        listener(event)
        except Exception as exception:
            err_msg = "Error occurred while connecting to Knocki websocket"
            raise KnockiConnectionError(err_msg) from exception

    def register_listener(
        self, event_type: EventType, listener: Callable[[Event], None]
    ) -> Callable[[], None]:
        """Register a listener."""
        if event_type not in self._listeners:
            self._listeners[event_type] = [listener]
        else:
            self._listeners[event_type].append(listener)
        return lambda: self._listeners[event_type].remove(listener)

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
