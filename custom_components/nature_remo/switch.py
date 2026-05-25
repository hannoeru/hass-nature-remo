"""Support for Nature Remo IR switches."""

import logging
from typing import Any, Dict, Iterable

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from . import DOMAIN, NatureRemoAPI, NatureRemoBase

_LOGGER = logging.getLogger(__name__)

SIGNAL_IMAGE_ON = "ico_on"
SIGNAL_IMAGE_OFF = "ico_off"
SIGNAL_IMAGE_TOGGLE = "ico_io"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Nature Remo generic IR switches."""
    _LOGGER.debug("Setting up switch platform.")
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    api = hass.data[DOMAIN][entry.entry_id]["api"]
    appliances = coordinator.data["appliances"]

    async_add_entities(
        [
            NatureRemoSwitch(coordinator, api, appliance)
            for appliance in appliances.values()
            if appliance["type"] == "IR" and _has_switch_signal(appliance.get("signals") or [])
        ]
    )


def _has_switch_signal(signals: Iterable[Dict[str, Any]]) -> bool:
    """Return true if the signal list can act as a switch."""
    images = {signal.get("image") for signal in signals}
    return bool(images & {SIGNAL_IMAGE_ON, SIGNAL_IMAGE_OFF, SIGNAL_IMAGE_TOGGLE})


class NatureRemoSwitch(NatureRemoBase, SwitchEntity):
    """Representation of a generic Nature Remo IR appliance as a switch."""

    _attr_assumed_state = True

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        api: NatureRemoAPI,
        appliance: Dict[str, Any],
    ) -> None:
        super().__init__(coordinator, appliance)
        self._api = api
        self._signals = appliance.get("signals") or []
        self._is_on = False

    @property
    def is_on(self) -> bool:
        """Return the locally assumed switch state."""
        return self._is_on

    @property
    def available(self) -> bool:
        """Return whether this switch has usable IR signals."""
        return _has_switch_signal(self._signals)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the IR appliance."""
        await self._send_first_signal([SIGNAL_IMAGE_ON, SIGNAL_IMAGE_TOGGLE])
        self._is_on = True
        self._async_write_state_if_added()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the IR appliance."""
        await self._send_first_signal([SIGNAL_IMAGE_OFF, SIGNAL_IMAGE_TOGGLE])
        self._is_on = False
        self._async_write_state_if_added()

    async def _send_first_signal(self, images: Iterable[str]) -> None:
        """Send the first matching IR signal by image name."""
        for image in images:
            signal = next((x for x in self._signals if x.get("image") == image), None)
            if signal is not None:
                _LOGGER.debug("Sending IR signal %s for %s", signal["id"], self._appliance_id)
                await self._api.post(f"/signals/{signal['id']}/send", {})
                return

        raise HomeAssistantError(f"No matching Nature Remo IR signal found for {self.name}")

    def _async_write_state_if_added(self) -> None:
        """Write state only after Home Assistant has added the entity."""
        if self.hass is not None:
            self.async_write_ha_state()
