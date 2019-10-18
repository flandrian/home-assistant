"""
Support for enocean cover

"""
import logging

from homeassistant.const import CONF_NAME, CONF_ID
from homeassistant.components.cover import (
    CoverDevice, SUPPORT_OPEN, SUPPORT_CLOSE, ATTR_POSITION,
    ATTR_TILT_POSITION)
from homeassistant.components.enocean import EnOceanDevice

DEPENDENCIES = ['enocean']

_LOGGER = logging.getLogger(__name__)


def setup_platform(hass, config, add_entities, discovery_info=None):
    dev_id = config.get(CONF_ID)
    name = config.get(CONF_NAME)
    sender_id = config.get('sender_id')
    channel = config.get('channel')
    
    add_entities([EnOceanCover(dev_id, name, sender_id, channel)])


class EnOceanCover(EnOceanDevice, CoverDevice):

    def __init__(self, dev_id, name, sender_id, channel):
        EnOceanDevice.__init__(self, dev_id)
        self._name = name
        self._sender_id = sender_id
        self._channel = int(channel)
        self._position = 0
        
    def value_changed(self, radio_packet):
        radio_packet.parse_eep(0x05, 0x01, command=4)
        channel = radio_packet.parsed['CHN']['raw_value']
        if channel == self._channel:
            self._position = radio_packet.parsed['POS']['raw_value']
            _LOGGER.info('new position: ' + str(self._position))
            self.schedule_update_ha_state()

    def _send_move_packet(self, position):
        self.assemble_and_send_radiopacket(rorg=0xD2, rorg_func=0x05, rorg_type=0x01, command=1,
                                  sender=self._sender_id,
                                  CMD=1,
                                  POS=position,
                                  ANG=position,
                                  REPO=0,
                                  LOCK=0,
                                  CHN=self._channel)

    @property
    def name(self):
        """Return the name of the cover."""
        return self._name
        
    @property
    def current_cover_position(self):
        """Return the current position of the cover."""
        return self._position
    
    @property
    def is_closed(self):
        return self._position == 0

    def stop_cover(self):
        self.assemble_and_send_radiopacket(rorg=0xD2, rorg_func=0x05, rorg_type=0x01, command=2,
                                  sender=self._sender_id,
                                  CMD=2,
                                  CHN=self._channel)
        _LOGGER.info("stopping " + str(self._channel))
    
    def open_cover(self):
        self._send_move_packet(100)
    
    def close_cover(self):
        self._send_move_packet(0)
    
    def set_cover_position(self, **kwargs):
        position = round(kwargs.get(ATTR_POSITION), -1)
        self._send_move_packet(position)
    
    def update(self):
        pass