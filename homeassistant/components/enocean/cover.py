"""
Support for enocean cover

"""
import logging

from homeassistant.const import CONF_NAME, CONF_ID
from homeassistant.components.cover import (
    CoverDevice, SUPPORT_OPEN, SUPPORT_CLOSE, ATTR_POSITION,
    ATTR_TILT_POSITION)
from .device import EnOceanEntity

DEPENDENCIES = ['enocean']

_LOGGER = logging.getLogger(__name__)


def setup_platform(hass, config, add_entities, discovery_info=None):
    dev_id = config.get(CONF_ID)
    name = config.get(CONF_NAME)
    sender_id = config.get('sender_id')
    channel = config.get('channel')
    
    add_entities([EnOceanCover(dev_id, name, sender_id, channel)])


class EnOceanCover(EnOceanEntity, CoverDevice):

    _POS_NO_CHANGE = 127
    _ANG_NO_CHANGE = 127

    def __init__(self, dev_id, name, sender_id, channel):
        super().__init__(dev_id, name)
        self._sender_id = sender_id
        self._channel = int(channel)
        self._position = 0
        self._tilt = 0
        
    def value_changed(self, radio_packet):
        radio_packet.parse_eep(0x05, 0x01, command=4)
        channel = radio_packet.parsed['CHN']['raw_value']
        if channel == self._channel:
            self._position = radio_packet.parsed['POS']['raw_value']
            self._tilt = radio_packet.parsed['ANG']['raw_value']
            _LOGGER.info('new state, position=' + str(self._position) + " angle=" + str(self._tilt))
            self.schedule_update_ha_state()

    def _send_move_packet(self, position, angle):
        self.assemble_and_send_radiopacket(rorg=0xD2, rorg_func=0x05, rorg_type=0x01, command=1,
                                  sender=self._sender_id,
                                  CMD=1,
                                  POS=position,
                                  ANG=angle,
                                  REPO=0,
                                  LOCK=0,
                                  CHN=self._channel)

    @property
    def name(self):
        """Return the name of the cover."""
        return self.dev_name
        
    @property
    def current_cover_position(self):
        """Return the current position of the cover."""
        return self._position

    @property
    def current_cover_tilt_position(self):
        """Return the current position of the cover."""
        return self._tilt
            
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
        self._send_move_packet(100, 100)
    
    def close_cover(self):
        self._send_move_packet(0, 0)
    
    def set_cover_position(self, **kwargs):
        position = round(kwargs.get(ATTR_POSITION), -1)
        if position < self._position:
            tilt = 0
        else:
            tilt = 100
        self._send_move_packet(position=position, angle=tilt)
    
    def stop_cover_tilt(self, **kwargs):
        self.stop_cover()

    def open_cover_tilt(self):
        self._send_move_packet(self._POS_NO_CHANGE, 100)

    def close_cover_tilt(self):
        self._send_move_packet(self._POS_NO_CHANGE, 0)

    def set_cover_tilt_position(self, **kwargs):
        tilt = round(kwargs.get(ATTR_TILT_POSITION), -1)
        self._send_move_packet(position=self._POS_NO_CHANGE, angle=tilt)

    def update(self):
        pass