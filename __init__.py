"""The Nature Remo integration."""

import logging
from datetime import timedelta
from typing import Any, Dict

import voluptuous as vol
from aiohttp import ClientError, ClientSession
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ACCESS_TOKEN, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)
from propcache.api import cached_property

_LOGGER = logging.getLogger(__name__)
_RESOURCE = "https://api.nature.global/1"

DOMAIN = "nature_remo"
PLATFORMS = [Platform.CLIMATE, Platform.SENSOR]

CONF_COOL_TEMP = "cool_temperature"
CONF_HEAT_TEMP = "heat_temperature"
DEFAULT_COOL_TEMP = 28
DEFAULT_HEAT_TEMP = 20
DEFAULT_UPDATE_INTERVAL = timedelta(seconds=60)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_ACCESS_TOKEN): cv.string,
                vol.Optional(CONF_COOL_TEMP, default=DEFAULT_COOL_TEMP): vol.Coerce(int),
                vol.Optional(CONF_HEAT_TEMP, default=DEFAULT_HEAT_TEMP): vol.Coerce(int),
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up Nature Remo component from YAML."""
    hass.data.setdefault(DOMAIN, {})

    if DOMAIN in config:
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": config_entries.SOURCE_IMPORT},
                data=dict(config[DOMAIN]),
            )
        )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Nature Remo from a config entry."""
    _LOGGER.debug("Setting up Nature Remo config entry.")
    access_token = entry.data[CONF_ACCESS_TOKEN]
    session = async_get_clientsession(hass)
    api = NatureRemoAPI(access_token, session)
    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="Nature Remo update",
        update_method=api.get,
        update_interval=DEFAULT_UPDATE_INTERVAL,
    )
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "api": api,
        "coordinator": coordinator,
        "config": entry.data,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a Nature Remo config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


class NatureRemoAPI:
    """Nature Remo API client"""

    def __init__(self, access_token: str, session: ClientSession) -> None:
        """Init API client"""
        self._access_token = access_token
        self._session = session

    async def get(self) -> Dict[str, Dict[str, Any]]:
        """Get appliance and device list."""
        _LOGGER.debug("Trying to fetch appliance and device list from API.")
        try:
            appliances_response = await self._request_json("GET", "/appliances")
            devices_response = await self._request_json("GET", "/devices")
        except HomeAssistantError as err:
            raise UpdateFailed(f"Error communicating with Nature Remo API: {err}") from err

        appliances = {x["id"]: x for x in appliances_response}
        devices = {x["id"]: x for x in devices_response}
        return {"appliances": appliances, "devices": devices}

    async def post(self, path: str, data: Dict[str, Any]) -> Any:
        """Post any request."""
        _LOGGER.debug("Trying to request post:%s, data:%s", path, data)
        return await self._request_json("POST", path, data=data)

    async def _request_json(self, method: str, path: str, **kwargs: Any) -> Any:
        """Request JSON from the Nature Remo API."""
        headers = {"Authorization": f"Bearer {self._access_token}"}
        try:
            async with self._session.request(
                method,
                f"{_RESOURCE}{path}",
                headers=headers,
                **kwargs,
            ) as response:
                response.raise_for_status()
                return await response.json()
        except ClientError as err:
            raise HomeAssistantError(f"{method} {path} failed: {err}") from err


class NatureRemoBase(CoordinatorEntity):
    """Nature Remo entity base class."""

    def __init__(self, coordinator: DataUpdateCoordinator, appliance: Dict[str, Any]) -> None:
        super().__init__(coordinator)
        self._name = f"Nature Remo {appliance['nickname']}"
        self._appliance_id = appliance["id"]
        self._device = appliance["device"]

    @cached_property
    def name(self) -> str | None:
        """Return the name of the sensor."""
        return self._name

    @cached_property
    def unique_id(self) -> str | None:
        """Return a unique ID."""
        return self._appliance_id

    @cached_property
    def should_poll(self) -> bool:
        """Return the polling requirement of the entity."""
        return False

    @cached_property
    def device_info(self) -> DeviceInfo | None:
        """Return the device info for the sensor."""
        return {
            "identifiers": {(DOMAIN, self._device["id"])},
            "name": self._device["name"] or "Unknown Device",
            "manufacturer": "Nature Remo",
            "model": self._device.get("serial_number") or "Unknown Model",
            "sw_version": self._device.get("firmware_version") or "Unknown Version",
        }


class NatureRemoDeviceBase(CoordinatorEntity):
    """Nature Remo Device entity base class."""

    def __init__(self, coordinator: DataUpdateCoordinator, device: Dict[str, Any]) -> None:
        super().__init__(coordinator)
        self._name = f"Nature Remo {device['name']}"
        self._device = device

    @cached_property
    def name(self) -> str | None:
        """Return the name of the sensor."""
        return self._name

    @cached_property
    def unique_id(self) -> str | None:
        """Return a unique ID."""
        return self._device["id"]

    @cached_property
    def should_poll(self) -> bool:
        """Return the polling requirement of the entity."""
        return False

    @cached_property
    def device_info(self) -> DeviceInfo | None:
        """Return the device info for the sensor."""
        return {
            "identifiers": {(DOMAIN, self._device["id"])},
            "name": self._device["name"] or "Unknown Device",
            "manufacturer": "Nature Remo",
            "model": self._device.get("serial_number") or "Unknown Model",
            "sw_version": self._device.get("firmware_version") or "Unknown Version",
        }
