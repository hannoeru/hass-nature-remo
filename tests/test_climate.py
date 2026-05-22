"""Tests for Nature Remo climate entities."""

from typing import Any

from homeassistant.components.climate.const import HVACMode

from custom_components.nature_remo import CONF_COOL_TEMP, CONF_HEAT_TEMP
from custom_components.nature_remo.climate import NatureRemoAC


class FakeCoordinator:
    """Minimal coordinator test double."""

    def __init__(self, data: dict[str, Any] | None = None) -> None:
        self.data = data or {}


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

    entity._update(  # noqa: SLF001
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
    entity._current_temperature = 23.5  # noqa: SLF001

    entity._update(  # noqa: SLF001
        _appliance()["settings"],
        {"newest_events": {}},
    )

    assert entity.current_temperature is None
    assert entity.hvac_mode == HVACMode.COOL
