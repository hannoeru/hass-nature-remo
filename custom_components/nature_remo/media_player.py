"""Support for Nature Remo TVs."""

import logging
from typing import Any, Dict

from homeassistant.components.media_player import (
    MediaPlayerDeviceClass,
    MediaPlayerEntity,
    MediaPlayerState,
)
from homeassistant.components.media_player.const import MediaPlayerEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from . import DOMAIN, NatureRemoAPI, NatureRemoBase

_LOGGER = logging.getLogger(__name__)

INPUT_TO_SOURCE = {
    "t": "terrestrial",
    "bs": "BS",
    "cs": "CS",
}
SOURCE_TO_INPUT = {source: input_id for input_id, source in INPUT_TO_SOURCE.items()}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Nature Remo TV appliances."""
    _LOGGER.debug("Setting up media_player platform.")
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    api = hass.data[DOMAIN][entry.entry_id]["api"]
    appliances = coordinator.data["appliances"]

    async_add_entities(
        [
            NatureRemoTV(coordinator, api, appliance)
            for appliance in appliances.values()
            if appliance["type"] == "TV" and appliance.get("tv") is not None
        ]
    )


class NatureRemoTV(NatureRemoBase, MediaPlayerEntity):
    """Representation of a Nature Remo TV appliance."""

    _attr_assumed_state = True
    _attr_device_class = MediaPlayerDeviceClass.TV

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        api: NatureRemoAPI,
        appliance: Dict[str, Any],
    ) -> None:
        super().__init__(coordinator, appliance)
        self._api = api
        self._buttons = _button_names(appliance)
        self._state = MediaPlayerState.OFF
        self._source: str | None = None
        self._source_list: list[str] = []
        self._supported_features = MediaPlayerEntityFeature(0)
        self._update((appliance.get("tv") or {}).get("state"), self._buttons)

    @property
    def state(self) -> MediaPlayerState:
        """Return the locally assumed media player state."""
        return self._state

    @property
    def source(self) -> str | None:
        """Return the current input source."""
        return self._source

    @property
    def source_list(self) -> list[str]:
        """Return available input sources."""
        return self._source_list

    @property
    def supported_features(self) -> MediaPlayerEntityFeature:
        """Flag supported media player features."""
        return self._supported_features

    async def async_turn_on(self) -> None:
        """Turn on the TV using the power button."""
        await self._post_button("power")
        if self._state == MediaPlayerState.OFF:
            self._state = MediaPlayerState.IDLE
        self._async_write_state_if_added()

    async def async_turn_off(self) -> None:
        """Turn off the TV using the power button."""
        await self._post_button("power")
        self._state = MediaPlayerState.OFF
        self._async_write_state_if_added()

    async def async_select_source(self, source: str) -> None:
        """Select a TV input source."""
        input_id = SOURCE_TO_INPUT.get(source, source)
        await self._post_button(f"input-{input_id}")
        self._source = source
        self._async_write_state_if_added()

    async def async_mute_volume(self, mute: bool) -> None:
        """Mute or unmute volume using the TV mute button."""
        await self._post_button("mute")
        self._attr_is_volume_muted = mute
        self._async_write_state_if_added()

    async def async_volume_up(self) -> None:
        """Turn volume up."""
        await self._post_button("vol-up")
        self._attr_is_volume_muted = False
        self._async_write_state_if_added()

    async def async_volume_down(self) -> None:
        """Turn volume down."""
        await self._post_button("vol-down")
        self._attr_is_volume_muted = False
        self._async_write_state_if_added()

    async def async_media_play(self) -> None:
        """Send play."""
        await self._post_button("play")
        self._state = MediaPlayerState.PLAYING
        self._async_write_state_if_added()

    async def async_media_pause(self) -> None:
        """Send pause."""
        await self._post_button("pause")
        self._state = MediaPlayerState.PAUSED
        self._async_write_state_if_added()

    async def async_media_stop(self) -> None:
        """Send stop."""
        await self._post_button("stop")
        self._state = MediaPlayerState.IDLE
        self._async_write_state_if_added()

    async def async_media_previous_track(self) -> None:
        """Send previous."""
        await self._post_button("prev")
        self._async_write_state_if_added()

    async def async_media_next_track(self) -> None:
        """Send next."""
        await self._post_button("next")
        self._async_write_state_if_added()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        appliance = self.coordinator.data["appliances"][self._appliance_id]
        self._buttons = _button_names(appliance)
        self._update((appliance.get("tv") or {}).get("state"), self._buttons)
        self.async_write_ha_state()

    async def _post_button(self, button: str) -> None:
        """Post a TV button command."""
        if button not in self._buttons:
            raise HomeAssistantError(
                f"Nature Remo TV button {button} is not available for {self.name}"
            )

        _LOGGER.debug("Sending TV button %s for %s", button, self._appliance_id)
        response = await self._api.post(f"/appliances/{self._appliance_id}/tv", {"button": button})
        self._update(response, self._buttons)

    def _update(self, state: Dict[str, Any] | None, buttons: list[str]) -> None:
        """Update local state from Nature Remo TV state and buttons."""
        self._source_list = [
            INPUT_TO_SOURCE.get(button.removeprefix("input-"), button.removeprefix("input-"))
            for button in buttons
            if button.startswith("input-")
        ]
        self._supported_features = _supported_features(buttons)

        if not state:
            return

        input_id = state.get("input")
        if input_id:
            self._source = INPUT_TO_SOURCE.get(input_id, input_id)

    def _async_write_state_if_added(self) -> None:
        """Write state only after Home Assistant has added the entity."""
        if self.hass is not None:
            self.async_write_ha_state()


def _button_names(appliance: Dict[str, Any]) -> list[str]:
    """Return all supported Nature Remo button names for a TV appliance."""
    return [button["name"] for button in (appliance.get("tv") or {}).get("buttons") or []]


def _supported_features(buttons: list[str]) -> MediaPlayerEntityFeature:
    """Return Home Assistant media player features supported by the TV buttons."""
    features = MediaPlayerEntityFeature(0)
    if "power" in buttons:
        features |= MediaPlayerEntityFeature.TURN_ON | MediaPlayerEntityFeature.TURN_OFF
    if any(button.startswith("input-") for button in buttons):
        features |= MediaPlayerEntityFeature.SELECT_SOURCE
    if "mute" in buttons:
        features |= MediaPlayerEntityFeature.VOLUME_MUTE
    if "vol-up" in buttons and "vol-down" in buttons:
        features |= MediaPlayerEntityFeature.VOLUME_STEP
    if "play" in buttons:
        features |= MediaPlayerEntityFeature.PLAY
    if "pause" in buttons:
        features |= MediaPlayerEntityFeature.PAUSE
    if "stop" in buttons:
        features |= MediaPlayerEntityFeature.STOP
    if "prev" in buttons:
        features |= MediaPlayerEntityFeature.PREVIOUS_TRACK
    if "next" in buttons:
        features |= MediaPlayerEntityFeature.NEXT_TRACK
    return features
