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

class NatureRemoEnergySensor(NatureRemoBase, SensorEntity):
    """Cumulative energy sensor (normal direction) for Nature Remo E."""

    def __init__(self, coordinator, appliance):
        super().__init__(coordinator, appliance)
        self._name = self._name.strip() + " Energy (Consumed)"

    @property
    def state(self):
        appliance = self._coordinator.data["appliances"][self._appliance_id]
        smart_meter = appliance["smart_meter"]
        props = {int(p["epc"]): float(p["val"]) for p in smart_meter["echonetlite_properties"]}

        unit_table = {
                    0: 1,       # 1 kWh
                    1: 0.1,
                    2: 0.01,
                    3: 0.001,
                    4: 0.0001,
                    10: 10,
                    11: 100,
                    12: 1000,
                }

        value = props.get(224, 0)
        coefficient = props.get(211, 1)
        unit_code = int(props.get(225, 0))
        unit = unit_table.get(unit_code, 1)

        try:
            energy = value * coefficient * unit
            return energy
        except Exception as e:
            _LOGGER.warning("Failed to calculate energy: %s", e)
            return None

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
        return f"{self._appliance_id}-cumulative-energy"

    async def async_added_to_hass(self):
        self.async_on_remove(self._coordinator.async_add_listener(self.async_write_ha_state))

    async def async_update(self):
        await self._coordinator.async_request_refresh()


class NatureRemoReturnedEnergySensor(NatureRemoBase, SensorEntity):
    """Cumulative returned energy sensor (reverse direction) for Nature Remo E."""

    def __init__(self, coordinator, appliance):
        super().__init__(coordinator, appliance)
        self._name = self._name.strip() + " Energy (Returned)"

    @property
    def state(self):
        appliance = self._coordinator.data["appliances"][self._appliance_id]
        smart_meter = appliance["smart_meter"]
        props = {int(p["epc"]): float(p["val"]) for p in smart_meter["echonetlite_properties"]}

        unit_table = {
            0: 1,       # 1 kWh
            1: 0.1,
            2: 0.01,
            3: 0.001,
            4: 0.0001,
            10: 10,
            11: 100,
            12: 1000,
        }

        try:
            if 211 in props and 225 in props and 227 in props:
                energy = props[227] * props[211] * unit_table[int(props[225])]
            elif 225 in props and 227 in props:
                energy = props[227] * unit_table[int(props[225])]
            else:
                energy = props.get(227)
            return energy
        except Exception as e:
            _LOGGER.warning("Failed to calculate returned energy: %s", e)
            return None

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
        return f"{self._appliance_id}-cumulative-returned-energy"

    @property
    def extra_state_attributes(self):
        return {
            "calc_mode": self.calc_mode
        }

    async def async_added_to_hass(self):
        self.async_on_remove(self._coordinator.async_add_listener(self.async_write_ha_state))

    async def async_update(self):
        await self._coordinator.async_request_refresh()


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
