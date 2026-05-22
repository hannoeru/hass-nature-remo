"""Support for Nature Remo AC."""

import logging
from typing import Any, Dict, List, Optional

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import ClimateEntityFeature, HVACMode
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from propcache.api import cached_property

from . import CONF_COOL_TEMP, CONF_HEAT_TEMP, DOMAIN, NatureRemoAPI, NatureRemoBase

_LOGGER = logging.getLogger(__name__)

SUPPORT_FLAGS = (
    ClimateEntityFeature.TARGET_TEMPERATURE
    | ClimateEntityFeature.FAN_MODE
    | ClimateEntityFeature.SWING_MODE
    | ClimateEntityFeature.TURN_ON
    | ClimateEntityFeature.TURN_OFF
)

MODE_HA_TO_REMO = {
    HVACMode.AUTO: "auto",
    HVACMode.FAN_ONLY: "blow",
    HVACMode.COOL: "cool",
    HVACMode.DRY: "dry",
    HVACMode.HEAT: "warm",
    HVACMode.OFF: "power-off",
}

MODE_REMO_TO_HA: dict[str, HVACMode] = {
    "auto": HVACMode.AUTO,
    "blow": HVACMode.FAN_ONLY,
    "cool": HVACMode.COOL,
    "dry": HVACMode.DRY,
    "warm": HVACMode.HEAT,
    "power-off": HVACMode.OFF,
}


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: Optional[DiscoveryInfoType] = None,
) -> None:
    """Set up the Nature Remo AC."""
    if discovery_info is None:
        return
    _LOGGER.debug("Setting up climate platform.")
    coordinator = hass.data[DOMAIN]["coordinator"]
    api = hass.data[DOMAIN]["api"]
    config = hass.data[DOMAIN]["config"]
    appliances = coordinator.data["appliances"]
    async_add_entities(
        [
            NatureRemoAC(coordinator, api, appliance, config)
            for appliance in appliances.values()
            if appliance["type"] == "AC"
        ]
    )


class NatureRemoAC(NatureRemoBase, ClimateEntity):
    """Implementation of a Nature Remo E sensor."""

    _enable_turn_on_off_backwards_compatibility = False

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        api: NatureRemoAPI,
        appliance: Dict[str, Any],
        config: Dict[str, Any],
    ) -> None:
        super().__init__(coordinator, appliance)
        self._api: NatureRemoAPI = api
        self._default_temp: dict[HVACMode, float] = {
            HVACMode.COOL: config[CONF_COOL_TEMP],
            HVACMode.HEAT: config[CONF_HEAT_TEMP],
        }
        self._modes = appliance["aircon"]["range"]["modes"]
        self._hvac_mode: HVACMode | None = None
        self._current_temperature: float | None = None
        self._target_temperature: float | None = None
        self._remo_mode: str | None = None
        self._fan_mode: str | None = None
        self._swing_mode: str | None = None
        self._last_target_temperature: dict[str, float | None] = {v: None for v in MODE_REMO_TO_HA}
        self._update(appliance["settings"])

    @cached_property
    def supported_features(self) -> ClimateEntityFeature:
        """Return the list of supported features."""
        return SUPPORT_FLAGS

    @cached_property
    def current_temperature(self) -> Optional[float]:
        """Return the current temperature."""
        return self._current_temperature

    @cached_property
    def temperature_unit(self) -> str:
        """Return the unit of measurement which this thermostat uses."""
        return UnitOfTemperature.CELSIUS

    @cached_property
    def min_temp(self) -> float:
        """Return the minimum temperature."""
        temp_range = self._current_mode_temp_range()
        if len(temp_range) == 0:
            return 0
        return min(temp_range)

    @cached_property
    def max_temp(self) -> float:
        """Return the maximum temperature."""
        temp_range = self._current_mode_temp_range()
        if len(temp_range) == 0:
            return 0
        return max(temp_range)

    @cached_property
    def target_temperature(self) -> Optional[float]:
        """Return the temperature we try to reach."""
        _LOGGER.debug("Current target temperature: %s", self._target_temperature)
        return self._target_temperature

    @cached_property
    def target_temperature_step(self) -> float:
        """Return the supported step of target temperature."""
        temp_range = self._current_mode_temp_range()
        if len(temp_range) >= 2:
            # determine step from the gap of first and second temperature
            step = round(temp_range[1] - temp_range[0], 1)
            if step in [1.0, 0.5]:  # valid steps
                return step
        return 1

    @cached_property
    def hvac_mode(self) -> Optional[HVACMode]:
        """Return hvac operation ie. heat, cool mode."""
        return self._hvac_mode

    @cached_property
    def hvac_modes(self) -> List[HVACMode]:
        """Return the list of available operation modes."""
        remo_modes = list(self._modes.keys())
        ha_modes = list(map(lambda mode: MODE_REMO_TO_HA[mode], remo_modes))
        ha_modes.append(HVACMode.OFF)
        return ha_modes

    @cached_property
    def fan_mode(self) -> Optional[str]:
        """Return the fan setting."""
        return self._fan_mode

    @cached_property
    def fan_modes(self) -> List[str]:
        """List of available fan modes."""
        return self._modes[self._remo_mode]["vol"]

    @cached_property
    def swing_mode(self) -> Optional[str]:
        """Return the swing setting."""
        return self._swing_mode

    @cached_property
    def swing_modes(self) -> List[str]:
        """List of available swing modes."""
        return self._modes[self._remo_mode]["dir"]

    @property
    def device_state_attributes(self) -> Dict[str, Any]:
        """Return device specific state attributes."""
        return {
            "previous_target_temperature": self._last_target_temperature,
        }

    async def async_turn_off(self) -> None:
        """Turn the entity off."""
        await self.async_set_hvac_mode(HVACMode.OFF)

    async def async_turn_on(self) -> None:
        """Turn the entity on."""
        if self._remo_mode is None:
            # if the mode is unknown, set to the default mode
            await self.async_set_hvac_mode(HVACMode.COOL)
        else:
            await self.async_set_hvac_mode(MODE_REMO_TO_HA[self._remo_mode])

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        target_temp = kwargs.get(ATTR_TEMPERATURE)
        if target_temp is None:
            return
        if target_temp.is_integer():
            # has to cast to whole number otherwise API will return an error
            target_temp = int(target_temp)
        _LOGGER.debug("Set temperature: %d", target_temp)
        await self._post({"temperature": f"{target_temp}"})

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new target hvac mode."""
        _LOGGER.debug("Set hvac mode: %s", hvac_mode)
        mode = MODE_HA_TO_REMO[hvac_mode]
        if mode == MODE_HA_TO_REMO[HVACMode.OFF]:
            await self._post({"button": mode})
        else:
            data: dict[str, Any] = {"operation_mode": mode}
            last_temp = self._last_target_temperature.get(mode)
            if last_temp is not None:
                data["temperature"] = last_temp
            elif self._default_temp.get(hvac_mode):
                data["temperature"] = self._default_temp[hvac_mode]
            await self._post(data)

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set new target fan mode."""
        _LOGGER.debug("Set fan mode: %s", fan_mode)
        await self._post({"air_volume": fan_mode})

    async def async_set_swing_mode(self, swing_mode: str) -> None:
        """Set new target swing operation."""
        _LOGGER.debug("Set swing mode: %s", swing_mode)
        await self._post({"air_direction": swing_mode})

    async def async_added_to_hass(self) -> None:
        """Subscribe to updates."""
        self.async_on_remove(self._coordinator.async_add_listener(self._update_callback))

    async def async_update(self) -> None:
        """Update the entity.

        Only used by the generic entity update service.
        """
        await self._coordinator.async_request_refresh()

    def _update(self, ac_settings: Dict[str, Any], device: Optional[Dict[str, Any]] = None) -> None:
        # hold this to determin the ac mode while it's turned-off
        self._remo_mode = ac_settings["mode"]
        try:
            self._target_temperature = float(ac_settings["temp"])
            self._last_target_temperature[self._remo_mode] = ac_settings["temp"]  # type: ignore[assignment]
        except KeyError, ValueError:
            self._target_temperature = None

        if ac_settings["button"] == MODE_HA_TO_REMO[HVACMode.OFF]:
            self._hvac_mode = HVACMode.OFF
        else:
            self._hvac_mode = MODE_REMO_TO_HA[self._remo_mode]  # type: ignore[index]

        self._fan_mode = ac_settings["vol"] or None
        self._swing_mode = ac_settings["dir"] or None

        if device is not None:
            self._current_temperature = float(device["newest_events"]["te"]["val"])

    @callback
    def _update_callback(self) -> None:
        self._update(
            self._coordinator.data["appliances"][self._appliance_id]["settings"],
            self._coordinator.data["devices"][self._device["id"]],
        )
        self.async_write_ha_state()

    async def _post(self, data: Dict[str, Any]) -> None:
        response = await self._api.post(f"/appliances/{self._appliance_id}/aircon_settings", data)
        self._update(response)
        self.async_write_ha_state()

    def _current_mode_temp_range(self) -> List[float]:
        temp_range = self._modes[self._remo_mode]["temp"]
        return list(map(float, filter(None, temp_range)))  # type: ignore[arg-type]
