"""Tests for the EnOcean switch platform."""

import copy

import pytest

from homeassistant.components.enocean import DOMAIN
from homeassistant.components.light import ATTR_BRIGHTNESS, DOMAIN as LIGHT_DOMAIN
from homeassistant.const import ATTR_ENTITY_ID, SERVICE_TURN_OFF, SERVICE_TURN_ON
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from .conftest import (
    assert_packet_content,
    assert_state,
    get_sent_packet,
    inject_packets,
    setup_platform,
)

from tests.common import assert_setup_component

DEVICE_ID = [0xAA, 0xBB, 0xCC, 0xDD]
SENDER_ID = [0xDE, 0xAD, 0xBE, 0xEF]
LIGHT_CONFIG = {
    "light": [
        {
            "platform": DOMAIN,
            "id": DEVICE_ID,
            "sender_id": SENDER_ID,
            "name": "room0",
        },
    ]
}


@pytest.mark.parametrize(
    ("packets", "expected_state"),
    [
        (
            [
                {
                    "rorg": 0xA5,
                    "rorg_func": 0x38,
                    "rorg_type": 0x08,
                    "command": 2,
                    "sender": DEVICE_ID,
                    "COM": 2,
                    "EDIM": 0,
                }
            ],
            ("off", {"brightness": None}),
        ),
        (
            [
                {
                    "rorg": 0xA5,
                    "rorg_func": 0x38,
                    "rorg_type": 0x08,
                    "command": 2,
                    "sender": DEVICE_ID,
                    "COM": 2,
                    "EDIM": 50,
                }
            ],
            ("on", {"brightness": 128}),
        ),
    ],
)
async def test_light_packets(
    hass: HomeAssistant,
    packets,
    expected_state,
) -> None:
    """Inject central command dimming packets and assert correct reaction."""
    communicator_mock = await setup_platform(hass, LIGHT_DOMAIN)
    with assert_setup_component(1, LIGHT_DOMAIN):
        assert await async_setup_component(
            hass,
            LIGHT_DOMAIN,
            LIGHT_CONFIG,
        )

    await inject_packets(hass, packets, communicator_mock)
    assert_state(hass, "light.room0", expected_state)


@pytest.mark.parametrize(
    ("call_service_args", "expected_packet", "expected_state"),
    [
        (
            [
                LIGHT_DOMAIN,
                SERVICE_TURN_ON,
                {ATTR_ENTITY_ID: "light.room0", ATTR_BRIGHTNESS: 50},
            ],
            {
                "rorg": 0xA5,
                "rorg_func": 0x38,
                "rorg_type": 0x08,
                "COM": 2,
                "EDIM": 19,
                "RMP": 1,
                "SW": 1,
            },
            ("on", {ATTR_BRIGHTNESS: 50}),
        ),
        (
            [
                LIGHT_DOMAIN,
                SERVICE_TURN_OFF,
                {ATTR_ENTITY_ID: "light.room0"},
            ],
            {
                "rorg": 0xA5,
                "rorg_func": 0x38,
                "rorg_type": 0x08,
                "COM": 2,
                "EDIM": 0,
                "RMP": 1,
                "SW": 1,
            },
            ("off", {}),
        ),
    ],
)
async def test_light_send_packets(
    hass: HomeAssistant,
    call_service_args,
    expected_packet,
    expected_state,
) -> None:
    """Inject temperature sensor packets and assert correct reaction."""
    light_config = copy.deepcopy(LIGHT_CONFIG)
    communicator_mock = await setup_platform(hass, LIGHT_DOMAIN)
    with assert_setup_component(1, LIGHT_DOMAIN):
        assert await async_setup_component(
            hass,
            LIGHT_DOMAIN,
            light_config,
        )
    await hass.async_block_till_done()

    await hass.services.async_call(*call_service_args)
    await hass.async_block_till_done()

    assert_state(hass, "light.room0", expected_state)

    transported_packet = get_sent_packet(communicator_mock)
    assert_packet_content(expected_packet, transported_packet, command=2)
