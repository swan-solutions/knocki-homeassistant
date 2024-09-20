"""Asynchronous Python client for Knocki."""

from __future__ import annotations

import asyncio
from asyncio import timeout
from dataclasses import dataclass, field
import logging
from typing import TYPE_CHECKING, Any, Awaitable, Callable

from aiohttp import ClientSession, WSMsgType
from aiohttp.hdrs import METH_DELETE, METH_GET, METH_POST
from mashumaro.codecs.orjson import ORJSONDecoder
import orjson
from yarl import URL

from knocki.exceptions import KnockiConnectionError, KnockiInvalidAuthError
from knocki.models import Event, EventType, TokenResponse, Trigger

if TYPE_CHECKING:
    from typing_extensions import Self


_URLS = {
    True: "stage.knocki.com",
    False: "production.knocki.com",
}

_WEB_SOCKET_URL = {
    True: "wss://ivg6nmkds4.execute-api.us-east-2.amazonaws.com/production",
    False: "wss://gso8jm7sri.execute-api.us-west-2.amazonaws.com/production",
}

LOGGER = logging.getLogger(__package__)


@dataclass
class KnockiClient:
    """Main class for handling connections with Knocki."""

    token: str | None = None
    session: ClientSession | None = None
    staging: bool = False
    request_timeout: int = 10
    _close_session: bool = False
    _listeners: dict[EventType, list[Callable[[Event], Awaitable[None] | None]]] = (
        field(default_factory=dict)
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
            "User-Agent": "com.knocki.mobileapp",
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
        data = orjson.loads(response)  # pylint: disable=maybe-no-member
        if "errors" in data:
            msg = "Invalid credentials"
            raise KnockiInvalidAuthError(msg)
        return TokenResponse.from_api(data)

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
        url = _WEB_SOCKET_URL[self.staging] + f"?token={self.token}"

        if self.session is None:
            self.session = ClientSession()
            self._close_session = True

        while True:
            LOGGER.debug("Connecting to Knocki websocket")
            try:
                async with self.session.ws_connect(url, heartbeat=300) as ws:
                    LOGGER.debug("Connected to Knocki websocket")
                    async for msg in ws:
                        LOGGER.debug(
                            "Received message from Knocki websocket %s", msg.data
                        )  # pylint: disable=maybe-no-member
                        if msg.type == WSMsgType.ERROR:  # pylint: disable=maybe-no-member
                            LOGGER.debug("Error occurred")
                            if exc := ws.exception():
                                LOGGER.error(exc)
                        if msg.type == WSMsgType.CLOSE:  # pylint: disable=maybe-no-member
                            LOGGER.debug("Knocki websocket closed")
                            await ws.close()
                            break
                        LOGGER.debug("Received message from Knocki websocket")
                        event = Event.from_json(msg.data)  # pylint: disable=maybe-no-member
                        for listener in self._listeners.get(event.event, []):
                            if asyncio.iscoroutinefunction(listener):
                                await listener(event)
                            else:
                                listener(event)
            except Exception as exception:
                err_msg = "Error occurred while connecting to Knocki websocket"
                LOGGER.exception(err_msg)
                raise KnockiConnectionError(err_msg) from exception
            finally:
                LOGGER.debug("Reconnecting to Knocki websocket")

    def register_listener(
        self, event_type: EventType, listener: Callable[[Event], Awaitable[None] | None]
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
