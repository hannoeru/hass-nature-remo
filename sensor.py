"""Support for Nature Remo E energy sensor."""
import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.components.sensor.const import (SensorDeviceClass,
                                                   UnitOfPower,
                                                   UnitOfTemperature,
                                                   UnitOfEnergy,
                                                   SensorStateClass
                                                   )

from . import DOMAIN, NatureRemoBase, NatureRemoDeviceBase

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the Nature Remo E sensor."""
    if discovery_info is None:
        return
    _LOGGER.debug("Setting up sensor platform.")
    coordinator = hass.data[DOMAIN]["coordinator"]
    appliances = coordinator.data["appliances"]
    devices = coordinator.data["devices"]

    entities = []

    for appliance in appliances.values():
        if appliance["type"] == "EL_SMART_METER":
            entities.append(NatureRemoE(coordinator, appliance))
            entities.append(NatureRemoEnergySensor(coordinator, appliance))
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

    def __init__(self, coordinator, appliance):
        super().__init__(coordinator, appliance)
        self._name = self._name.strip() + " Power"

    @property
    def state(self):
        """Return the state of the sensor."""
        appliance = self._coordinator.data["appliances"][self._appliance_id]
        smart_meter = appliance["smart_meter"]
        echonetlite_properties = smart_meter["echonetlite_properties"]
        measured_instantaneous = next(
            value["val"] for value in echonetlite_properties if value["epc"] == 231
        )
        _LOGGER.debug("Current state: %sW", measured_instantaneous)
        return measured_instantaneous

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement of this entity, if any."""
        return UnitOfPower.WATT

    @property
    def device_class(self):
        """Return the device class."""
        return SensorDeviceClass.POWER

    async def async_added_to_hass(self):
        """Subscribe to updates."""
        self.async_on_remove(
            self._coordinator.async_add_listener(self.async_write_ha_state)
        )

    async def async_update(self):
        """Update the entity.

        Only used by the generic entity update service.
        """
        await self._coordinator.async_request_refresh()

class NatureRemoCumulativeEnergySensorBase(NatureRemoBase, SensorEntity):
    """Cumulative energy sensor base for Nature Remo E."""

    _epc: int
    _sensor_type: str

    def __init__(self, coordinator, appliance):
        super().__init__(coordinator, appliance)
        self._name = self._name.strip() + f" Energy ({self._sensor_type})"

    UNIT_TABLE = {
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
    def calculate_energy(props: dict, epc: int) -> float:
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
    def epc_exists(props: dict, epc: int) -> bool:
        return epc in props
    
    @property
    def state(self):
        appliance = self._coordinator.data["appliances"][self._appliance_id]
        smart_meter = appliance["smart_meter"]
        props = {int(p["epc"]): float(p["val"]) for p in smart_meter["echonetlite_properties"]}
        return self.calculate_energy(props, self._epc)

    @property
    def available(self):
        appliance = self._coordinator.data["appliances"][self._appliance_id]
        smart_meter = appliance["smart_meter"]
        props = {int(p["epc"]): float(p["val"]) for p in smart_meter["echonetlite_properties"]}
        return self.epc_exists(props, self._epc)

    @property
    def unit_of_measurement(self):
        return UnitOfEnergy.KILO_WATT_HOUR

    @property
    def device_class(self):
        return SensorDeviceClass.ENERGY

    @property
    def state_class(self):
        return SensorStateClass.TOTAL_INCREASING
    
    @property
    def unique_id(self):
        return f"{self._appliance_id}-cumulative-energy-{self._sensor_type.lower()}"

    async def async_added_to_hass(self):
        self.async_on_remove(self._coordinator.async_add_listener(self.async_write_ha_state))

    async def async_update(self):
        await self._coordinator.async_request_refresh()


class NatureRemoEnergySensor(NatureRemoCumulativeEnergySensorBase):
    _epc = 224
    _sensor_type = "Consumed"


class NatureRemoReturnedEnergySensor(NatureRemoCumulativeEnergySensorBase):
    _epc = 227
    _sensor_type = "Returned"


class NatureRemoTemperatureSensor(NatureRemoDeviceBase, SensorEntity):
    """Implementation of a Nature Remo sensor."""

    def __init__(self, coordinator, appliance):
        super().__init__(coordinator, appliance)
        self._name = self._name.strip() + " Temperature"

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement of this entity, if any."""
        return UnitOfTemperature.CELSIUS

    @property
    def state(self):
        """Return the state of the sensor."""
        device = self._coordinator.data["devices"][self._device["id"]]
        return device["newest_events"]["te"]["val"]

    @property
    def device_class(self):
        """Return the device class."""
        return SensorDeviceClass.TEMPERATURE


class NatureRemoHumiditySensor(NatureRemoDeviceBase, SensorEntity):
    """Implementation of a Nature Remo sensor."""

    def __init__(self, coordinator, appliance):
        super().__init__(coordinator, appliance)
        self._name = self._name.strip() + " Humidity"

    @property
    def state(self):
        """Return the state of the sensor."""
        device = self._coordinator.data["devices"][self._device["id"]]
        return device["newest_events"]["hu"]["val"]

    @property
    def device_class(self):
        """Return the device class."""
        return SensorDeviceClass.HUMIDITY


class NatureRemoIlluminanceSensor(NatureRemoDeviceBase, SensorEntity):
    """Implementation of a Nature Remo sensor."""

    def __init__(self, coordinator, appliance):
        super().__init__(coordinator, appliance)
        self._name = self._name.strip() + " Illuminance"

    @property
    def unique_id(self):
        """Return a unique ID."""
        return self._device["id"] + "-illuminance"

    @property
    def state(self):
        """Return the state of the sensor."""
        device = self._coordinator.data["devices"][self._device["id"]]
        return device["newest_events"]["il"]["val"]

    @property
    def device_class(self):
        """Return the device class."""
        return SensorDeviceClass.ILLUMINANCE 
