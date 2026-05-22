"""Support for Nature Remo E energy sensor."""

import logging
from typing import Any, Dict, Optional

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.components.sensor.const import SensorDeviceClass, SensorStateClass
from homeassistant.const import LIGHT_LUX, PERCENTAGE, UnitOfEnergy, UnitOfPower, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from propcache.api import cached_property

from . import DOMAIN, NatureRemoBase, NatureRemoDeviceBase

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: Optional[DiscoveryInfoType] = None,
) -> None:
    """Set up the Nature Remo E sensor."""
    if discovery_info is None:
        return
    _LOGGER.debug("Setting up sensor platform.")
    coordinator = hass.data[DOMAIN]["coordinator"]
    appliances = coordinator.data["appliances"]
    devices = coordinator.data["devices"]

    entities: list[SensorEntity] = []

    for appliance in appliances.values():
        if appliance["type"] == "EL_SMART_METER":
            entities.append(NatureRemoE(coordinator, appliance))
            # Check for EPC 224 (Consumed Energy)
            if any(prop.get("epc") == 224 for prop in appliance.get("echonetlite_properties", [])):
                entities.append(NatureRemoEnergySensor(coordinator, appliance))
            # Check for EPC 227 (Returned Energy)
            if any(prop.get("epc") == 227 for prop in appliance.get("echonetlite_properties", [])):
                entities.append(NatureRemoReturnedEnergySensor(coordinator, appliance))
    for device in devices.values():
        # skip devices that include in appliances
        if device["id"] in [appliance["device"]["id"] for appliance in appliances.values()]:
            continue
        for sensor in device["newest_events"].keys():
            if sensor == "te":
                entities.append(NatureRemoTemperatureSensor(coordinator, device))
            elif sensor == "hu":
                entities.append(NatureRemoHumiditySensor(coordinator, device))
            elif sensor == "il":
                entities.append(NatureRemoIlluminanceSensor(coordinator, device))

    async_add_entities(entities)


class NatureRemoE(NatureRemoBase, SensorEntity):
    """Implementation of a Nature Remo E sensor."""

    def __init__(self, coordinator: DataUpdateCoordinator, appliance: Dict[str, Any]) -> None:
        super().__init__(coordinator, appliance)
        self._name = self._name.strip() + " Power"
        self.entity_description = SensorEntityDescription(
            key="power",
            name=self._name,
            device_class=SensorDeviceClass.POWER,
            native_unit_of_measurement=UnitOfPower.WATT,
        )

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        appliance = self.coordinator.data["appliances"][self._appliance_id]
        smart_meter = appliance["smart_meter"]
        echonetlite_properties = smart_meter["echonetlite_properties"]
        measured_instantaneous = next(
            value["val"] for value in echonetlite_properties if value["epc"] == 231
        )
        _LOGGER.debug("Current state: %sW", measured_instantaneous)
        return measured_instantaneous


class NatureRemoCumulativeEnergySensorBase(NatureRemoBase, SensorEntity):
    """Cumulative energy sensor base for Nature Remo E."""

    _epc: int
    _sensor_type: str

    def __init__(self, coordinator: DataUpdateCoordinator, appliance: Dict[str, Any]) -> None:
        super().__init__(coordinator, appliance)
        self._name = self._name.strip() + f" Energy ({self._sensor_type})"
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING

    UNIT_TABLE: Dict[int, float] = {
        0: 1,
        1: 0.1,
        2: 0.01,
        3: 0.001,
        4: 0.0001,
        10: 10,
        11: 100,
        12: 1000,
    }

    @staticmethod
    def calculate_energy(props: Dict[int, float], epc: int) -> Optional[float]:
        try:
            value = props.get(epc, 0)
            coefficient = props.get(211, 1)
            unit_code = int(props.get(225, 0))
            unit = NatureRemoCumulativeEnergySensorBase.UNIT_TABLE.get(unit_code, 1)
            return value * coefficient * unit
        except Exception as e:
            _LOGGER.warning("Energy calculation error for EPC %s: %s", epc, e)
            return None

    @staticmethod
    def epc_exists(props: Dict[int, float], epc: int) -> bool:
        return epc in props

    @property
    def native_value(self) -> float | None:
        appliance = self.coordinator.data["appliances"][self._appliance_id]
        smart_meter = appliance["smart_meter"]
        props = {int(p["epc"]): float(p["val"]) for p in smart_meter["echonetlite_properties"]}
        return self.calculate_energy(props, self._epc)

    @property
    def available(self) -> bool:
        appliance = self.coordinator.data["appliances"][self._appliance_id]
        smart_meter = appliance["smart_meter"]
        props = {int(p["epc"]): float(p["val"]) for p in smart_meter["echonetlite_properties"]}
        return self.epc_exists(props, self._epc)

    @cached_property
    def unique_id(self) -> str | None:
        return f"{self._appliance_id}-cumulative-energy-{self._sensor_type.lower()}"


class NatureRemoEnergySensor(NatureRemoCumulativeEnergySensorBase):
    _epc = 224
    _sensor_type = "Consumed"

    def __init__(self, coordinator: DataUpdateCoordinator, appliance: Dict[str, Any]) -> None:
        super().__init__(coordinator, appliance)


class NatureRemoReturnedEnergySensor(NatureRemoCumulativeEnergySensorBase):
    _epc = 227
    _sensor_type = "Returned"

    def __init__(self, coordinator: DataUpdateCoordinator, appliance: Dict[str, Any]) -> None:
        super().__init__(coordinator, appliance)


class NatureRemoTemperatureSensor(NatureRemoDeviceBase, SensorEntity):
    """Implementation of a Nature Remo sensor."""

    def __init__(self, coordinator: DataUpdateCoordinator, device: Dict[str, Any]) -> None:
        super().__init__(coordinator, device)
        self._name = self._name.strip() + " Temperature"
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_device_class = SensorDeviceClass.TEMPERATURE

    @cached_property
    def unique_id(self) -> str | None:
        """Return a unique ID."""
        return self._device["id"] + "-temperature"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        device = self.coordinator.data["devices"][self._device["id"]]
        return device["newest_events"]["te"]["val"]


class NatureRemoHumiditySensor(NatureRemoDeviceBase, SensorEntity):
    """Implementation of a Nature Remo sensor."""

    def __init__(self, coordinator: DataUpdateCoordinator, device: Dict[str, Any]) -> None:
        super().__init__(coordinator, device)
        self._name = self._name.strip() + " Humidity"
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_device_class = SensorDeviceClass.HUMIDITY

    @cached_property
    def unique_id(self) -> str | None:
        """Return a unique ID."""
        return self._device["id"] + "-humidity"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        device = self.coordinator.data["devices"][self._device["id"]]
        return device["newest_events"]["hu"]["val"]


class NatureRemoIlluminanceSensor(NatureRemoDeviceBase, SensorEntity):
    """Implementation of a Nature Remo sensor."""

    def __init__(self, coordinator: DataUpdateCoordinator, device: Dict[str, Any]) -> None:
        super().__init__(coordinator, device)
        self._name = self._name.strip() + " Illuminance"
        self._attr_native_unit_of_measurement = LIGHT_LUX
        self._attr_device_class = SensorDeviceClass.ILLUMINANCE

    @cached_property
    def unique_id(self) -> str | None:
        """Return a unique ID."""
        return self._device["id"] + "-illuminance"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        device = self.coordinator.data["devices"][self._device["id"]]
        return device["newest_events"]["il"]["val"]
