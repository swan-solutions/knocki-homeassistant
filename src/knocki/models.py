"""Models for Knocki API."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Self


@dataclass(slots=True)
class TokenResponse:
    """Token response from Knocki API."""

    token: str
    user_id: str

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Self:
        """Parse token response from API."""
        return cls(
            token=data["data"][0]["attributes"]["id"],
            user_id=data["included"][0]["attributes"]["id"],
        )
