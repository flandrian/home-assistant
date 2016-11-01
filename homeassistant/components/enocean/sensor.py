"""
Enocean Sensor

Depending on the EEP configured for the entity a different class can be
instantiated to handle the sensor type.

Consult the EEP at http://www.enocean-alliance.org/eep/ for protocol details
"""

import voluptuous as vol
import logging

from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import TEMP_CELSIUS, STATE_UNAVAILABLE, POWER_WATT,\
    ELECTRICAL_CURRENT_MILLIAMPERES, VOLUME_FLOW_RATE_LITERS_PER_SECOND
from homeassistant.components import enocean
from homeassistant.helpers.entity import Entity
from homeassistant.const import (CONF_NAME, CONF_ID)
import homeassistant.helpers.config_validation as cv
from .device import EnOceanEntity
from . import parse_eep_config

DEPENDENCIES = ['enocean']

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_ID): cv.match_all,
        vol.Required("eep"): cv.string,
        vol.Optional(CONF_NAME, default='Undefined Enocean Sensor'): cv.string,
    }
)

def setup_platform(hass, config, add_devices, discovery_info=None):
    device_id = config.get(CONF_ID)
    device_name = config.get(CONF_NAME)
    eep = parse_eep_config(config.get('eep'))
    if eep['rorg'] == 0xA5 and eep['func'] == 0x02:
        add_devices([EnoceanSensorA502(device_name, device_id, eep['type'])])
    if eep['rorg'] == 0xA5 and eep['func'] == 0x10:
        add_devices([EnoceanSensorA510(device_name, device_id, eep['type'])])
    if eep['rorg'] == 0xA5 and eep['func'] == 0x12:
        add_devices([EnoceanSensorA512(device_name, device_id, eep['type'])])

class EnoceanSensorA502(EnOceanEntity):
    """ Representation of an Enocean Temperature Sensor """

    def __init__(self, name, device_id, device_type):
        super().__init__(device_id, name)
        self._device_type = device_type
        self._state = STATE_UNAVAILABLE
        self._unit_of_measurement = TEMP_CELSIUS

    def value_changed(self, packet):
        packet.parse_eep(0x02, self._device_type)
        self._state = packet.parsed['TMP']['value']
        self.update_ha_state()

    @property
    def should_poll(self):
        return False

    @property
    def name(self):
        """Return the name of the device."""
        return self.dev_name

    @property
    def state(self):
        """Return the state of the device."""
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return self._unit_of_measurement

class EnoceanSensorA510(EnOceanEntity):
    """ Representation of an Enocean Room Operating Panel """

    def __init__(self, name, device_id, device_type):
        super().__init__(device_id, name)
        self._device_type = device_type
        self._state = STATE_UNAVAILABLE
        self._unit_of_measurement = TEMP_CELSIUS
        self._humidity = None

    def value_changed(self, packet):
        packet.parse_eep(0x10, self._device_type)
        self._state = packet.parsed['TMP']['value']
        try:
            self._humidity = packet.parsed['HUM']['value']
        except KeyError:
            pass
        self.schedule_update_ha_state()

    @property
    def should_poll(self):
        return False

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit this state is expressed in."""
        return self._unit_of_measurement

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        if self._humidity:
            return {
                'humidity': self._humidity,
            }

class EnoceanSensorA512(EnOceanEntity):
    """ Representation of an Automated Meter Reading (Power Meter, Gas Meter
    and other more exotic "meters"),
    e.g. Permundo PSC-234/PSC-236 Switch with Power reading """

    def __init__(self, name, device_id, device_type):
        super().__init__(device_id, name)
        self._device_type = device_type
        self._state = STATE_UNAVAILABLE
        if (device_type == 0x01):
            self._unit_of_measurement = POWER_WATT
        elif (device_type == 0x02):
            self._unit_of_measurement = VOLUME_FLOW_RATE_LITERS_PER_SECOND
        elif (device_type == 0x10):
            self._unit_of_measurement = ELECTRICAL_CURRENT_MILLIAMPERES
        else:
            self._unit_of_measurement = '?'

    def value_changed(self, packet):
        packet.parse_eep(0x02, self._device_type)
        # skip packets that don't contain the current value
        if packet.parsed['DT']['value'] != 1:
            return
        value = packet.parsed['MR']['value']
        multiplier = pow(10, packet.parsed['DIV']['value'])
        self._state = value * multiplier
        self.schedule_update_ha_state()

    @property
    def should_poll(self):
        return False

    @property
    def name(self):
        """Return the name of the sensor."""
        return self.dev_name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit this state is expressed in."""
        return self._unit_of_measurement    
