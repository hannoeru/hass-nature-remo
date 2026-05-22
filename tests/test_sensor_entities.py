"""Tests for Nature Remo sensor entities."""

from typing import Any

from custom_components.nature_remo.sensor import (
    NatureRemoEnergySensor,
    NatureRemoHumiditySensor,
    NatureRemoIlluminanceSensor,
    NatureRemoTemperatureSensor,
)


class FakeCoordinator:
    """Minimal coordinator test double."""

    def __init__(self, data: dict[str, Any]) -> None:
        self.data = data


def test_device_sensor_unique_ids_are_sensor_specific() -> None:
    device = {
        "id": "device-1",
        "name": "Living Room",
        "newest_events": {"te": {"val": 21.5}, "hu": {"val": 55}, "il": {"val": 120}},
    }
    coordinator = FakeCoordinator({"devices": {"device-1": device}})

    assert NatureRemoTemperatureSensor(coordinator, device).unique_id == "device-1-temperature"  # type: ignore[arg-type]
    assert NatureRemoHumiditySensor(coordinator, device).unique_id == "device-1-humidity"  # type: ignore[arg-type]
    assert NatureRemoIlluminanceSensor(coordinator, device).unique_id == "device-1-illuminance"  # type: ignore[arg-type]


def test_device_sensor_native_values_follow_coordinator_data() -> None:
    device = {
        "id": "device-1",
        "name": "Living Room",
        "newest_events": {"te": {"val": 21.5}},
    }
    coordinator = FakeCoordinator({"devices": {"device-1": device}})
    sensor = NatureRemoTemperatureSensor(coordinator, device)  # type: ignore[arg-type]

    assert sensor.native_value == 21.5

    coordinator.data["devices"]["device-1"]["newest_events"]["te"]["val"] = 22.5

    assert sensor.native_value == 22.5


def test_cumulative_energy_sensor_calculates_from_coordinator_data() -> None:
    appliance = {
        "id": "appliance-1",
        "nickname": "Meter",
        "device": {"id": "device-1", "name": "Remo E"},
    }
    coordinator = FakeCoordinator(
        {
            "appliances": {
                "appliance-1": {
                    **appliance,
                    "smart_meter": {
                        "echonetlite_properties": [
                            {"epc": 224, "val": 100},
                            {"epc": 211, "val": 2},
                            {"epc": 225, "val": 1},
                        ]
                    },
                }
            }
        }
    )
    sensor = NatureRemoEnergySensor(coordinator, appliance)  # type: ignore[arg-type]

    assert sensor.available
    assert sensor.native_value == 20

    coordinator.data["appliances"]["appliance-1"]["smart_meter"]["echonetlite_properties"][0][
        "val"
    ] = 110

    assert sensor.native_value == 22
