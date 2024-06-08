"""Models for Knocki API."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Self

from mashumaro import field_options
from mashumaro.mixins.orjson import DataClassORJSONMixin


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


@dataclass
class Trigger(DataClassORJSONMixin):
    """Trigger model."""

    device_id: str = field(metadata=field_options(alias="device"))
    details: TriggerDetails


@dataclass
class TriggerDetails(DataClassORJSONMixin):
    """Trigger details model."""

    trigger_id: int = field(metadata=field_options(alias="id"))
    name: str = field(metadata=field_options(alias="name"))


class EventType(StrEnum):
    """Event types for Knocki."""

    CREATED = "actionCreated"
    UPDATED = "actionUpdated"
    DELETED = "actionDeleted"
    TRIGGERED = "actionTriggered"


@dataclass
class Event(DataClassORJSONMixin):
    """Event model."""

    event: EventType
    payload: Trigger
