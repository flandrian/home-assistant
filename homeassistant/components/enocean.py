"""
EnOcean Component.

For more details about this component, please refer to the documentation at
https://home-assistant.io/components/EnOcean/
"""
import logging

import voluptuous as vol

from homeassistant.const import CONF_DEVICE
import homeassistant.helpers.config_validation as cv

REQUIREMENTS = ['enocean==0.40']

_LOGGER = logging.getLogger(__name__)

DOMAIN = 'enocean'

ENOCEAN_DONGLE = None

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_DEVICE): cv.string,
    }),
}, extra=vol.ALLOW_EXTRA)


def setup(hass, config):
    """Set up the EnOcean component."""
    global ENOCEAN_DONGLE

    serial_dev = config[DOMAIN].get(CONF_DEVICE)

    ENOCEAN_DONGLE = EnOceanDongle(hass, serial_dev)

    return True

def parse_eep_config(eep_string):
    eep_number_strings = eep_string.split('-')
    return {
        'rorg':int(eep_number_strings[0], 16),
        'func':int(eep_number_strings[1], 16),
        'type':int(eep_number_strings[2], 16)}


class EnOceanDongle:
    """Representation of an EnOcean dongle."""

    def __init__(self, hass, ser):
        """Initialize the EnOcean dongle."""
        from enocean.communicators.serialcommunicator import SerialCommunicator
        self.__communicator = SerialCommunicator(
            port=ser, callback=self.callback)
        self.__communicator.start()
        self._devices_by_id = {}

    def register_device(self, dev):
        """Register another device."""
        decice_id_hex = self._combine_hex(dev._device_id)
        if decice_id_hex not in self._devices_by_id:
            self._devices_by_id[decice_id_hex] = list()
        self._devices_by_id[decice_id_hex].append(dev)

    def send_command(self, command):
        """Send a command from the EnOcean dongle."""
        self.__communicator.send(command)

    def get_base_id(self):
        """Return a copy of the base ID"""
        return self.__communicator.base_id.copy()

    # pylint: disable=no-self-use
    def _combine_hex(self, data):
        """Combine list of integer values to one big integer."""
        output = 0x00
        for i, j in enumerate(reversed(data)):
            output |= (j << i * 8)
        return output

    def callback(self, temp):
        """Handle EnOcean device's callback.

        This is the callback function called by
        python-enocean whenever there is an incoming
        packet.
        """
        #_LOGGER.info('packet received ' + str(temp))
        from enocean.protocol.packet import RadioPacket
        if isinstance(temp, RadioPacket):
            sender_int  = self._combine_hex(temp.sender)
            if sender_int in self._devices_by_id:
                for device in self._devices_by_id[sender_int]:
                    device.handle_packet(temp)


class EnOceanDevice():
    """Parent class for all devices associated with the EnOcean component."""

    def __init__(self, device_id):
        """Initialize the device."""
        self._device_id = device_id
        ENOCEAN_DONGLE.register_device(self)

    # pylint: disable=no-self-use
    def send_command(self, data, optional, packet_type):
        """Send a command via the EnOcean dongle."""
        from enocean.protocol.packet import Packet
        packet = Packet(packet_type, data=data, optional=optional)
        ENOCEAN_DONGLE.send_command(packet)

    def create_and_send_packet(self, **kwargs):
        from enocean.protocol.packet import RadioPacket
        packet = RadioPacket.create(**kwargs)
        ENOCEAN_DONGLE.send_command(packet)

    def get_base_id(self, offset=0):
        """Return a copy of the base ID, with offset applied"""
        id = ENOCEAN_DONGLE.get_base_id()
        id[3] += offset
        return id