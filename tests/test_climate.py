"""Tests for Nature Remo climate entities."""

import asyncio
import logging
from typing import Any

from homeassistant.components.climate.const import HVACMode
from homeassistant.const import ATTR_TEMPERATURE

from custom_components.nature_remo import CONF_COOL_TEMP, CONF_HEAT_TEMP
from custom_components.nature_remo.climate import NatureRemoAC


class FakeCoordinator:
    """Minimal coordinator test double."""

    def __init__(self, data: dict[str, Any] | None = None) -> None:
        self.data = data or {}
        self.last_update_success = True


class FakeApi:
    """Minimal API test double."""

    async def post(self, _path: str, _data: dict[str, Any]) -> dict[str, Any]:
        return {}


def _appliance(settings: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "id": "appliance-1",
        "nickname": "AC",
        "type": "AC",
        "device": {"id": "device-1", "name": "Living Room"},
        "settings": settings
        or {
            "mode": "cool",
            "temp": "25",
            "button": "",
            "vol": "auto",
            "dir": "auto",
        },
        "aircon": {
            "range": {
                "modes": {
                    "cool": {
                        "temp": ["18", "19", "20"],
                        "vol": ["auto"],
                        "dir": ["auto"],
                    }
                }
            }
        },
    }


def test_climate_update_uses_device_temperature_when_present() -> None:
    entity = NatureRemoAC(
        FakeCoordinator(),  # type: ignore[arg-type]
        FakeApi(),  # type: ignore[arg-type]
        _appliance(),
        {CONF_COOL_TEMP: 28, CONF_HEAT_TEMP: 20},
    )

    entity._update(
        _appliance()["settings"],
        {"newest_events": {"te": {"val": 23.5}}},
    )

    assert entity.current_temperature == 23.5


def test_climate_update_handles_missing_device_temperature() -> None:
    entity = NatureRemoAC(
        FakeCoordinator(),  # type: ignore[arg-type]
        FakeApi(),  # type: ignore[arg-type]
        _appliance(),
        {CONF_COOL_TEMP: 28, CONF_HEAT_TEMP: 20},
    )
    entity._current_temperature = 23.5

    entity._update(
        _appliance()["settings"],
        {"newest_events": {}},
    )

    assert entity.current_temperature is None
    assert entity.hvac_mode == HVACMode.COOL


def test_climate_unavailable_when_appliance_disappears() -> None:
    appliance = _appliance()
    coordinator = FakeCoordinator(
        {
            "appliances": {"appliance-1": appliance},
            "devices": {"device-1": appliance["device"]},
        }
    )
    entity = NatureRemoAC(
        coordinator,  # type: ignore[arg-type]
        FakeApi(),  # type: ignore[arg-type]
        appliance,
        {CONF_COOL_TEMP: 28, CONF_HEAT_TEMP: 20},
    )
    entity.async_write_ha_state = lambda: None  # type: ignore[method-assign]
    coordinator.data = {"appliances": {}, "devices": {}}

    entity._handle_coordinator_update()

    assert entity.available is False


def test_climate_reads_room_temperature_when_created() -> None:
    appliance = _appliance()
    appliance["device"]["newest_events"] = {"te": {"val": 24.0}}
    entity = NatureRemoAC(
        FakeCoordinator(),  # type: ignore[arg-type]
        FakeApi(),  # type: ignore[arg-type]
        appliance,
        {CONF_COOL_TEMP: 28, CONF_HEAT_TEMP: 20},
    )

    assert entity.current_temperature == 24.0


def test_set_temperature_accepts_half_degrees(caplog: Any) -> None:
    class RecordingApi:
        def __init__(self) -> None:
            self.calls: list[tuple[str, dict[str, Any]]] = []

        async def post(self, path: str, data: dict[str, Any]) -> dict[str, Any]:
            self.calls.append((path, data))
            return {
                "mode": "cool",
                "temp": "25.5",
                "button": "",
                "vol": "auto",
                "dir": "auto",
            }

    api = RecordingApi()
    entity = NatureRemoAC(
        FakeCoordinator(),  # type: ignore[arg-type]
        api,  # type: ignore[arg-type]
        _appliance(),
        {CONF_COOL_TEMP: 28, CONF_HEAT_TEMP: 20},
    )
    entity.async_write_ha_state = lambda: None  # type: ignore[method-assign]

    with caplog.at_level(logging.DEBUG, logger="custom_components.nature_remo.climate"):
        asyncio.run(entity.async_set_temperature(**{ATTR_TEMPERATURE: 25.5}))

    assert api.calls == [
        ("/appliances/appliance-1/aircon_settings", {"temperature": "25.5"}),
    ]
    assert "Set temperature: 25.5" in caplog.text
