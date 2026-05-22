"""Tests for the Nature Remo API adapter."""

import asyncio
from typing import Any

import pytest
from aiohttp import ClientError
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.nature_remo import NatureRemoAPI


class FakeResponse:
    """Minimal aiohttp response test double."""

    def __init__(self, payload: Any) -> None:
        self._payload = payload
        self.raise_for_status_called = False

    async def __aenter__(self) -> "FakeResponse":
        return self

    async def __aexit__(self, *_args: Any) -> None:
        return None

    def raise_for_status(self) -> None:
        self.raise_for_status_called = True

    async def json(self) -> Any:
        return self._payload


class FakeSession:
    """Minimal aiohttp session test double."""

    def __init__(self, *payloads: Any) -> None:
        self._payloads = list(payloads)
        self.calls: list[tuple[str, str, dict[str, Any]]] = []
        self.responses: list[FakeResponse] = []

    def request(self, method: str, url: str, **kwargs: Any) -> FakeResponse:
        self.calls.append((method, url, kwargs))
        response = FakeResponse(self._payloads.pop(0))
        self.responses.append(response)
        return response


class FailingSession:
    """Session test double that raises an aiohttp client error."""

    def request(self, *_args: Any, **_kwargs: Any) -> FakeResponse:
        raise ClientError("boom")


def test_get_fetches_appliances_and_devices() -> None:
    session = FakeSession(
        [{"id": "appliance-1"}],
        [{"id": "device-1"}],
    )
    api = NatureRemoAPI("token", session)  # type: ignore[arg-type]

    data = asyncio.run(api.get())

    assert data == {
        "appliances": {"appliance-1": {"id": "appliance-1"}},
        "devices": {"device-1": {"id": "device-1"}},
    }
    assert session.calls == [
        (
            "GET",
            "https://api.nature.global/1/appliances",
            {"headers": {"Authorization": "Bearer token"}},
        ),
        (
            "GET",
            "https://api.nature.global/1/devices",
            {"headers": {"Authorization": "Bearer token"}},
        ),
    ]
    assert all(response.raise_for_status_called for response in session.responses)


def test_post_returns_json_payload() -> None:
    session = FakeSession({"ok": True})
    api = NatureRemoAPI("token", session)  # type: ignore[arg-type]

    data = asyncio.run(api.post("/appliances/id/aircon_settings", {"button": "power-off"}))

    assert data == {"ok": True}
    assert session.calls == [
        (
            "POST",
            "https://api.nature.global/1/appliances/id/aircon_settings",
            {
                "data": {"button": "power-off"},
                "headers": {"Authorization": "Bearer token"},
            },
        )
    ]


def test_get_wraps_client_errors_as_update_failed() -> None:
    api = NatureRemoAPI("token", FailingSession())  # type: ignore[arg-type]

    with pytest.raises(UpdateFailed):
        asyncio.run(api.get())
