"""Support for EnOcean binary sensors."""

from __future__ import annotations

from enocean.utils import combine_hex
import voluptuous as vol

from homeassistant.components.binary_sensor import (
    DEVICE_CLASSES_SCHEMA,
    PLATFORM_SCHEMA as BINARY_SENSOR_PLATFORM_SCHEMA,
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import CONF_DEVICE_CLASS, CONF_ID, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .entity import EnOceanEntity

DEFAULT_NAME = "EnOcean binary sensor"
DEPENDENCIES = ["enocean"]
EVENT_BUTTON_PRESSED = "button_pressed"

PLATFORM_SCHEMA = BINARY_SENSOR_PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_ID): vol.All(cv.ensure_list, [vol.Coerce(int)]),
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_DEVICE_CLASS): DEVICE_CLASSES_SCHEMA,
    }
)


def setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the Binary Sensor platform for EnOcean."""
    dev_id: list[int] = config[CONF_ID]
    dev_name: str = config[CONF_NAME]
    device_class: BinarySensorDeviceClass | None = config.get(CONF_DEVICE_CLASS)

    add_entities([EnOceanBinarySensor(dev_id, dev_name, device_class)])


class EnOceanBinarySensor(EnOceanEntity, BinarySensorEntity):
    """Representation of EnOcean binary sensors such as wall switches.

    Supported EEPs (EnOcean Equipment Profiles):
    - F6-02-01 (Light and Blind Control - Application Style 2)
    - F6-02-02 (Light and Blind Control - Application Style 1)
    """

    def __init__(
        self,
        dev_id: list[int],
        dev_name: str,
        device_class: BinarySensorDeviceClass | None,
    ) -> None:
        """Initialize the EnOcean binary sensor."""
        super().__init__(dev_id)
        self._attr_device_class = device_class
        self.which = -1
        self.onoff = -1
        self._attr_unique_id = f"{combine_hex(dev_id)}-{device_class}"
        self._attr_name = dev_name

    def value_changed(self, packet):
        """Fire an event with the data that have changed.

        This method is called when there is an incoming packet associated
        with this platform.
        """

        packet.parse_eep(rorg_func=0x02, rorg_type=0x02)
        if not packet.parsed["T21"]["value"]:
            pushed = None
        if packet.parsed["NU"]["value"]:
            pushed = 1
        else:
            pushed = 0

        if packet.parsed["EB"]["value"] == "pressed":
            if packet.parsed["R1"]["value"] == "Button AI":
                self.which = 1
                self.onoff = 1
            elif packet.parsed["R1"]["value"] == "Button AO":
                self.which = 1
                self.onoff = 0
            elif packet.parsed["R1"]["value"] == "Button BI":
                self.which = 0
                self.onoff = 1
            elif packet.parsed["R1"]["value"] == "Button BO":
                self.which = 0
                self.onoff = 0

            if packet.parsed["SA"]["value"] == "2nd action valid":
                if (packet.parsed["R1"]["value"] == "Button AO") and (
                    packet.parsed["R2"]["value"] == "Button BO"
                ):
                    self.which = 10
                    self.onoff = 0
                elif (packet.parsed["R1"]["value"] == "Button AI") and (
                    packet.parsed["R2"]["value"] == "Button BI"
                ):
                    self.which = 10
                    self.onoff = 1

        self.schedule_update_ha_state()

        self.hass.bus.fire(
            EVENT_BUTTON_PRESSED,
            {
                "id": self.dev_id,
                "pushed": pushed,
                "which": self.which,
                "onoff": self.onoff,
            },
        )
