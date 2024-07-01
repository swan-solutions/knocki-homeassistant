"""Asynchronous Python client for Knocki."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

import aiohttp
from aiohttp.hdrs import METH_DELETE, METH_GET, METH_POST
from aioresponses import CallbackResult, aioresponses
import pytest

from knocki import (
    KnockiClient,
    KnockiConnectionError,
    KnockiError,
    KnockiInvalidAuthError,
)

from . import load_fixture
from .const import BASE_URL, HEADERS, UNAUTHORIZED_HEADERS

if TYPE_CHECKING:
    from syrupy import SnapshotAssertion


async def test_putting_in_own_session(
    responses: aioresponses,
) -> None:
    """Test putting in own session."""
    responses.post(
        f"{BASE_URL}/tokens",
        status=200,
        body=load_fixture("tokens.json"),
    )
    async with aiohttp.ClientSession() as session:
        knocki = KnockiClient(session=session)
        await knocki.login("test@test.com", "test")
        assert knocki.session is not None
        assert not knocki.session.closed
        await knocki.close()
        assert not knocki.session.closed


async def test_creating_own_session(
    responses: aioresponses,
) -> None:
    """Test creating own session."""
    responses.post(
        f"{BASE_URL}/tokens",
        status=200,
        body=load_fixture("tokens.json"),
    )
    knocki = KnockiClient()
    await knocki.login("test@test.com", "test")
    assert knocki.session is not None
    assert not knocki.session.closed
    await knocki.close()
    assert knocki.session.closed


async def test_unexpected_server_response(
    responses: aioresponses,
    knocki_client: KnockiClient,
) -> None:
    """Test handling unexpected response."""
    responses.post(
        f"{BASE_URL}/tokens",
        status=200,
        headers={"Content-Type": "plain/text"},
        body="Yes",
    )
    with pytest.raises(KnockiError):
        assert await knocki_client.login("test@test.com", "test")


async def test_timeout(
    responses: aioresponses,
) -> None:
    """Test request timeout."""

    # Faking a timeout by sleeping
    async def response_handler(_: str, **_kwargs: Any) -> CallbackResult:
        """Response handler for this test."""
        await asyncio.sleep(2)
        return CallbackResult(body="Goodmorning!")

    responses.post(
        f"{BASE_URL}/tokens",
        callback=response_handler,
    )
    async with KnockiClient(request_timeout=1) as knocki:
        with pytest.raises(KnockiConnectionError):
            assert await knocki.login("test@test.com", "test")


async def test_login(
    responses: aioresponses, knocki_client: KnockiClient, snapshot: SnapshotAssertion
) -> None:
    """Test logging in."""
    responses.post(
        f"{BASE_URL}/tokens",
        status=200,
        body=load_fixture("tokens.json"),
    )
    assert await knocki_client.login("test@test.com", "test") == snapshot
    responses.assert_called_once_with(
        f"{BASE_URL}/tokens",
        METH_POST,
        headers=UNAUTHORIZED_HEADERS,
        json={
            "data": [
                {
                    "type": "tokens",
                    "attributes": {
                        "email": "test@test.com",
                        "password": "test",
                        "type": "auth",
                    },
                }
            ]
        },
    )


async def test_invalig_login(
    responses: aioresponses, knocki_client: KnockiClient
) -> None:
    """Test logging in."""
    responses.post(
        f"{BASE_URL}/tokens",
        status=200,
        body=load_fixture("invalid_auth.json"),
    )
    with pytest.raises(KnockiInvalidAuthError):
        assert await knocki_client.login("test@test.com", "test")


async def test_link(
    responses: aioresponses, authenticated_client: KnockiClient
) -> None:
    """Test linking."""
    responses.post(f"{BASE_URL}/accounts/homeassistant/v1/link", status=200, body="{}")
    await authenticated_client.link()
    responses.assert_called_once_with(
        f"{BASE_URL}/accounts/homeassistant/v1/link",
        METH_POST,
        headers=HEADERS,
        json=None,
    )


async def test_unlink(
    responses: aioresponses, authenticated_client: KnockiClient
) -> None:
    """Test unlinking."""
    responses.delete(f"{BASE_URL}/accounts/homeassistant", status=200, body="{}")
    await authenticated_client.unlink()
    responses.assert_called_once_with(
        f"{BASE_URL}/accounts/homeassistant",
        METH_DELETE,
        headers=HEADERS,
        json=None,
    )


async def test_get_triggers(
    responses: aioresponses,
    authenticated_client: KnockiClient,
    snapshot: SnapshotAssertion,
) -> None:
    """Test getting triggers."""
    responses.get(
        f"{BASE_URL}/actions/homeassistant",
        status=200,
        body=load_fixture("triggers.json"),
    )
    assert await authenticated_client.get_triggers() == snapshot
    responses.assert_called_once_with(
        f"{BASE_URL}/actions/homeassistant", METH_GET, headers=HEADERS, json=None
    )
