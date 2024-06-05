"""Asynchronous Python client for Knocki."""

from typing import AsyncGenerator, Generator

import aiohttp
from aioresponses import aioresponses
import pytest

from knocki import KnockiClient
from syrupy import SnapshotAssertion

from .syrupy import KnockiSnapshotExtension


@pytest.fixture(name="snapshot")
def snapshot_assertion(snapshot: SnapshotAssertion) -> SnapshotAssertion:
    """Return snapshot assertion fixture with the Knocki extension."""
    return snapshot.use_extension(KnockiSnapshotExtension)


@pytest.fixture(name="knocki_client")
async def client() -> AsyncGenerator[KnockiClient, None]:
    """Return a Knocki client."""
    async with aiohttp.ClientSession() as session, KnockiClient(
        session=session,
    ) as knocki_client:
        yield knocki_client


@pytest.fixture(name="authenticated_client")
async def authenticated_client(
    knocki_client: KnockiClient,
) -> KnockiClient:
    """Return an authenticated Knocki client."""
    knocki_client.token = "test"
    return knocki_client


@pytest.fixture(name="responses")
def aioresponses_fixture() -> Generator[aioresponses, None, None]:
    """Return aioresponses fixture."""
    with aioresponses() as mocked_responses:
        yield mocked_responses
