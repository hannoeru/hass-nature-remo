"""Tests for the Nature Remo API adapter."""

import asyncio
from typing import Any, Self

import pytest
from aiohttp import ClientError, ClientResponseError, RequestInfo
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.update_coordinator import UpdateFailed
from multidict import CIMultiDict, CIMultiDictProxy
from yarl import URL

from custom_components.nature_remo import NatureRemoAPI


class FakeResponse:
    """Minimal aiohttp response test double."""

    def __init__(self, payload: Any, *, status: int = 200) -> None:
        self._payload = payload
        self.status = status
        self.raise_for_status_called = False

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *_args: object) -> None:
        return None

    def raise_for_status(self) -> None:
        self.raise_for_status_called = True
        if self.status >= 400:
            raise _http_error(self.status)

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


def test_get_wraps_client_errors_as_update_failed(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_sleep(monkeypatch)
    api = NatureRemoAPI("token", FailingSession())  # type: ignore[arg-type]

    with pytest.raises(UpdateFailed):
        asyncio.run(api.get())


def test_get_retries_a_dropped_connection_then_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    sleeps = _patch_sleep(monkeypatch)
    session = SequenceSession([ClientError("reset"), [{"id": "appliance-1"}], [{"id": "device-1"}]])
    api = NatureRemoAPI("token", session)  # type: ignore[arg-type]

    data = asyncio.run(api.get())

    assert data["appliances"]["appliance-1"]["id"] == "appliance-1"
    assert len(session.calls) == 3
    assert sleeps == [0.5]


def test_get_retries_server_and_rate_limit_responses(monkeypatch: pytest.MonkeyPatch) -> None:
    sleeps = _patch_sleep(monkeypatch)
    session = SequenceSession(
        [
            FakeResponse(None, status=500),
            FakeResponse(None, status=429),
            [{"id": "appliance-1"}],
            [{"id": "device-1"}],
        ]
    )
    api = NatureRemoAPI("token", session)  # type: ignore[arg-type]

    data = asyncio.run(api.get())

    assert "appliance-1" in data["appliances"]
    assert sleeps == [0.5, 1.0]


def test_get_does_not_retry_rejected_tokens(monkeypatch: pytest.MonkeyPatch) -> None:
    sleeps = _patch_sleep(monkeypatch)
    session = SequenceSession([FakeResponse(None, status=401)])
    api = NatureRemoAPI("token", session)  # type: ignore[arg-type]

    with pytest.raises(ConfigEntryAuthFailed):
        asyncio.run(api.get())

    assert len(session.calls) == 1
    assert sleeps == []


def test_post_does_not_retry_a_transient_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    sleeps = _patch_sleep(monkeypatch)
    session = SequenceSession([ClientError("reset"), {"ok": True}])
    api = NatureRemoAPI("token", session)  # type: ignore[arg-type]

    with pytest.raises(HomeAssistantError):
        asyncio.run(api.post("/signals/1/send", {}))

    assert len(session.calls) == 1
    assert sleeps == []


class SequenceSession:
    """Session that returns payloads, responses, or raises errors in order."""

    def __init__(self, steps: list[Any]) -> None:
        self._steps = list(steps)
        self.calls: list[tuple[str, str]] = []

    def request(self, method: str, url: str, **_kwargs: Any) -> FakeResponse:
        self.calls.append((method, url))
        step = self._steps.pop(0)
        if isinstance(step, Exception):
            raise step
        if isinstance(step, FakeResponse):
            return step
        return FakeResponse(step)


def _patch_sleep(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    sleeps: list[float] = []

    async def _sleep(delay: float) -> None:
        sleeps.append(delay)

    monkeypatch.setattr("custom_components.nature_remo.asyncio.sleep", _sleep)
    return sleeps


def _http_error(status: int) -> ClientResponseError:
    info = RequestInfo(
        URL("https://api.nature.global/1/appliances"),
        "GET",
        CIMultiDictProxy(CIMultiDict()),
    )
    return ClientResponseError(info, (), status=status, message="error")
