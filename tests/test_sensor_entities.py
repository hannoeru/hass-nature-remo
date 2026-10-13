"""Tests for Nature Remo sensor entities."""

from typing import Any

from homeassistant.components.sensor.const import SensorStateClass

from custom_components.nature_remo.sensor import (
    NatureRemoE,
    NatureRemoEnergySensor,
    NatureRemoHumiditySensor,
    NatureRemoIlluminanceSensor,
    NatureRemoTemperatureSensor,
)


class FakeCoordinator:
    """Minimal coordinator test double."""

    def __init__(self, data: dict[str, Any]) -> None:
        self.data = data
        self.last_update_success = True


def test_device_info_separates_model_and_serial() -> None:
    device = {
        "id": "device-1",
        "name": "Living Room",
        "firmware_version": "Remo/1.2.3",
        "serial_number": "SN-1",
        "newest_events": {"te": {"val": 21.5}},
    }
    sensor = NatureRemoTemperatureSensor(FakeCoordinator({"devices": {}}), device)  # type: ignore[arg-type]
    info = sensor.device_info
    assert info is not None
    assert info["model"] == "Remo"
    assert info["serial_number"] == "SN-1"
    assert info["sw_version"] == "Remo/1.2.3"
    assert info["identifiers"] == {("nature_remo", "device-1")}

    appliance = {"id": "appliance-1", "nickname": "Meter", "device": device}
    power = NatureRemoE(FakeCoordinator({"appliances": {}}), appliance)  # type: ignore[arg-type]
    assert power.device_info == info

    unnamed = {"id": "device-2", "name": "", "newest_events": {}}
    bare = NatureRemoTemperatureSensor(FakeCoordinator({"devices": {}}), unnamed)  # type: ignore[arg-type]
    bare_info = bare.device_info
    assert bare_info is not None
    assert bare_info["model"] == "Nature Remo"
    assert bare_info["name"] == "Unknown Device"
    assert bare_info["serial_number"] is None
    assert bare_info["sw_version"] == "Unknown Version"


def test_temperature_sensor_unavailable_when_device_disappears() -> None:
    device = {
        "id": "device-1",
        "name": "Living Room",
        "newest_events": {"te": {"val": 21.5}},
    }
    coordinator = FakeCoordinator({"devices": {"device-1": device}})
    sensor = NatureRemoTemperatureSensor(coordinator, device)  # type: ignore[arg-type]

    assert sensor.available is True
    coordinator.data = {"devices": {}}

    assert sensor.available is False
    assert sensor.native_value is None


def test_power_sensor_is_a_measurement() -> None:
    appliance = {
        "id": "appliance-1",
        "nickname": "Meter",
        "device": {"id": "device-1", "name": "Remo E"},
    }
    sensor = NatureRemoE(FakeCoordinator({"appliances": {}}), appliance)  # type: ignore[arg-type]

    assert sensor.state_class is SensorStateClass.MEASUREMENT


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


def test_cumulative_energy_unavailable_when_coordinator_update_failed() -> None:
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
                            {"epc": 211, "val": 1},
                            {"epc": 225, "val": 0},
                        ]
                    },
                }
            }
        }
    )
    coordinator.last_update_success = False
    sensor = NatureRemoEnergySensor(coordinator, appliance)  # type: ignore[arg-type]

    assert sensor.available is False
