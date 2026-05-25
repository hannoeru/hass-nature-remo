"""Support for Nature Remo lights."""

import logging
from typing import Any, Dict, Iterable

from homeassistant.components.light import ColorMode, LightEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from propcache.api import cached_property

from . import DOMAIN, NatureRemoAPI, NatureRemoBase

_LOGGER = logging.getLogger(__name__)

BUTTON_ON_PRIORITY = ("on", "on-favorite", "on-100", "onoff", "power")
BUTTON_OFF_PRIORITY = ("off", "onoff", "power")

ATTR_BRIGHTNESS_PERCENT = "brightness_percent"
ATTR_LAST_BUTTON = "last_button"
ATTR_BUTTONS = "buttons"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Nature Remo light appliances."""
    _LOGGER.debug("Setting up light platform.")
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    api = hass.data[DOMAIN][entry.entry_id]["api"]
    appliances = coordinator.data["appliances"]

    async_add_entities(
        [
            NatureRemoLight(coordinator, api, appliance)
            for appliance in appliances.values()
            if appliance["type"] == "LIGHT" and appliance.get("light") is not None
        ]
    )


class NatureRemoLight(NatureRemoBase, LightEntity):
    """Representation of a Nature Remo light appliance."""

    _attr_assumed_state = True
    _attr_supported_color_modes = {ColorMode.ONOFF}
    _attr_color_mode = ColorMode.ONOFF

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        api: NatureRemoAPI,
        appliance: Dict[str, Any],
    ) -> None:
        super().__init__(coordinator, appliance)
        self._api = api
        self._buttons = _button_names(appliance)
        self._state: dict[str, Any] = {}
        self._is_on = False
        self._update((appliance.get("light") or {}).get("state"))

    @property
    def is_on(self) -> bool:
        """Return true if the light is on."""
        return self._is_on

    @cached_property
    def supported_color_modes(self) -> set[ColorMode]:
        """Return supported color modes."""
        return {ColorMode.ONOFF}

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return Nature Remo-specific light state."""
        attributes: dict[str, Any] = {ATTR_BUTTONS: self._buttons}
        if brightness := self._state.get("brightness"):
            attributes[ATTR_BRIGHTNESS_PERCENT] = brightness
        if last_button := self._state.get("last_button"):
            attributes[ATTR_LAST_BUTTON] = last_button
        return attributes

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on."""
        await self._post_button(BUTTON_ON_PRIORITY)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the light off."""
        await self._post_button(BUTTON_OFF_PRIORITY)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        appliance = self.coordinator.data["appliances"][self._appliance_id]
        self._buttons = _button_names(appliance)
        self._update((appliance.get("light") or {}).get("state"))
        self.async_write_ha_state()

    async def _post_button(self, candidates: Iterable[str]) -> None:
        """Post the first available light button from the candidate list."""
        button = next((candidate for candidate in candidates if candidate in self._buttons), None)
        if button is None:
            raise HomeAssistantError(f"No matching Nature Remo light button found for {self.name}")

        _LOGGER.debug("Sending light button %s for %s", button, self._appliance_id)
        response = await self._api.post(
            f"/appliances/{self._appliance_id}/light", {"button": button}
        )
        self._update(response)
        self._async_write_state_if_added()

    def _update(self, state: Dict[str, Any] | None) -> None:
        """Update local state from Nature Remo light state."""
        if not state:
            return

        self._state = state
        if state.get("power") == "on":
            self._is_on = True
        elif state.get("power") == "off":
            self._is_on = False

    def _async_write_state_if_added(self) -> None:
        """Write state only after Home Assistant has added the entity."""
        if self.hass is not None:
            self.async_write_ha_state()


def _button_names(appliance: Dict[str, Any]) -> list[str]:
    """Return all supported Nature Remo button names for a light appliance."""
    return [button["name"] for button in (appliance.get("light") or {}).get("buttons") or []]
