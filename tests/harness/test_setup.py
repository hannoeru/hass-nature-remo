"""Load Nature Remo in Home Assistant against a mocked cloud API."""

from http import HTTPStatus

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_ACCESS_TOKEN
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.nature_remo import CONF_COOL_TEMP, CONF_HEAT_TEMP, DOMAIN
from tests.harness.payloads import APPLIANCES_URL, DEVICES_URL, sample_appliances_and_devices

# The coordinator keeps its update interval scheduled after unload.
pytestmark = pytest.mark.parametrize("expected_lingering_timers", [True])


def _entry_data() -> dict[str, object]:
    return {
        CONF_ACCESS_TOKEN: "test-token",
        CONF_COOL_TEMP: 28,
        CONF_HEAT_TEMP: 20,
    }


def _mock_cloud(aioclient_mock) -> None:
    appliances, devices = sample_appliances_and_devices()
    aioclient_mock.get(APPLIANCES_URL, json=appliances)
    aioclient_mock.get(DEVICES_URL, json=devices)


def _state(hass: HomeAssistant, entity_id: str) -> str:
    state = hass.states.get(entity_id)
    assert state is not None, entity_id
    return state.state


async def test_config_entry_creates_user_visible_entities(
    hass: HomeAssistant, aioclient_mock
) -> None:
    """A configured account shows AC, energy, IR, light, TV, and room sensors."""
    _mock_cloud(aioclient_mock)
    entry = MockConfigEntry(domain=DOMAIN, data=_entry_data(), unique_id=DOMAIN)
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert _state(hass, "climate.living_room_nature_remo_living_ac") == "cool"
    assert _state(hass, "sensor.meter_nature_remo_meter_power") == "450.0"
    assert _state(hass, "sensor.meter_nature_remo_meter_energy_consumed") == "100.0"
    assert _state(hass, "switch.living_room_nature_remo_fan") == "off"
    assert _state(hass, "light.living_room_nature_remo_ceiling") == "on"
    assert _state(hass, "media_player.living_room_nature_remo_tv") == "off"
    assert _state(hass, "sensor.hall_nature_remo_hall_temperature") == "21.5"
    assert _state(hass, "sensor.hall_nature_remo_hall_humidity") == "48"
    assert _state(hass, "sensor.hall_nature_remo_hall_illuminance") == "120"

    appliance_calls = [call for call in aioclient_mock.mock_calls if str(call[1]) == APPLIANCES_URL]
    assert appliance_calls
    assert appliance_calls[0][3]["Authorization"] == "Bearer test-token"

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.NOT_LOADED
    climate_after = hass.states.get("climate.living_room_nature_remo_living_ac")
    assert climate_after is None or climate_after.state == "unavailable"


async def test_user_flow_accepts_a_working_token(hass: HomeAssistant, aioclient_mock) -> None:
    """The settings UI creates an entry when Nature Remo accepts the token."""
    _mock_cloud(aioclient_mock)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    assert result["type"] is FlowResultType.FORM

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        _entry_data(),
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Nature Remo"
    assert result["data"][CONF_ACCESS_TOKEN] == "test-token"
    await hass.async_block_till_done()
    assert _state(hass, "climate.living_room_nature_remo_living_ac") == "cool"


async def test_user_flow_reports_a_rejected_token(hass: HomeAssistant, aioclient_mock) -> None:
    """A rejected token stays on the form instead of creating an entry."""
    aioclient_mock.get(APPLIANCES_URL, status=HTTPStatus.UNAUTHORIZED)
    aioclient_mock.get(DEVICES_URL, json=[])

    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        _entry_data(),
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}
    assert not hass.config_entries.async_entries(DOMAIN)
