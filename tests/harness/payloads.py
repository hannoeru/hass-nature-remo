"""Nature Remo API payloads used by the Home Assistant harness."""

from typing import Any

APPLIANCES_URL = "https://api.nature.global/1/appliances"
DEVICES_URL = "https://api.nature.global/1/devices"


def remo_device(
    device_id: str,
    name: str,
    *,
    temperature: float | None = 21.5,
    humidity: float | None = 48,
    illuminance: float | None = 120,
) -> dict[str, Any]:
    """Return a Nature Remo device payload."""
    events: dict[str, Any] = {}
    if temperature is not None:
        events["te"] = {"val": temperature, "created_at": "2026-10-01T00:00:00Z"}
    if humidity is not None:
        events["hu"] = {"val": humidity, "created_at": "2026-10-01T00:00:00Z"}
    if illuminance is not None:
        events["il"] = {"val": illuminance, "created_at": "2026-10-01T00:00:00Z"}
    return {
        "id": device_id,
        "name": name,
        "firmware_version": "Remo/1.2.3",
        "serial_number": f"SN-{device_id}",
        "newest_events": events,
    }


def sample_appliances_and_devices() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return one appliance of each supported type plus a sensor-only device."""
    living = remo_device(
        "device-living", "Living Room", temperature=24.0, humidity=40, illuminance=80
    )
    hall = remo_device("device-hall", "Hall")
    meter = remo_device("device-meter", "Meter", temperature=None, humidity=None, illuminance=None)
    appliances = [
        {
            "id": "appliance-ac",
            "nickname": "Living AC",
            "type": "AC",
            "device": living,
            "settings": {
                "mode": "cool",
                "temp": "26",
                "button": "",
                "vol": "auto",
                "dir": "auto",
            },
            "aircon": {
                "range": {
                    "modes": {
                        "cool": {
                            "temp": ["18", "26", "28"],
                            "vol": ["auto"],
                            "dir": ["auto"],
                        }
                    }
                }
            },
        },
        {
            "id": "appliance-meter",
            "nickname": "Meter",
            "type": "EL_SMART_METER",
            "device": meter,
            "smart_meter": {
                "echonetlite_properties": [
                    {"epc": 231, "val": 450},
                    {"epc": 224, "val": 100},
                    {"epc": 211, "val": 1},
                    {"epc": 225, "val": 0},
                ]
            },
        },
        {
            "id": "appliance-fan",
            "nickname": "Fan",
            "type": "IR",
            "device": living,
            "signals": [
                {"id": "signal-on", "name": "On", "image": "ico_on"},
                {"id": "signal-off", "name": "Off", "image": "ico_off"},
            ],
        },
        {
            "id": "appliance-light",
            "nickname": "Ceiling",
            "type": "LIGHT",
            "device": living,
            "light": {
                "buttons": [
                    {"name": "on", "image": "ico_on", "label": "Light_on"},
                    {"name": "off", "image": "ico_off", "label": "Light_off"},
                ],
                "state": {"power": "on", "brightness": "100", "last_button": "on"},
            },
        },
        {
            "id": "appliance-tv",
            "nickname": "TV",
            "type": "TV",
            "device": living,
            "tv": {
                "buttons": [
                    {"name": "power", "image": "ico_io", "label": "TV_power"},
                ],
                "state": {"input": "t"},
            },
        },
    ]
    return appliances, [living, hall, meter]
