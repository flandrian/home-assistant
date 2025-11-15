"""Tests for the EnOcean binary sensor platform."""

from enocean.protocol.packet import RadioPacket
import pytest

from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.enocean import DOMAIN
from homeassistant.components.enocean.binary_sensor import EVENT_BUTTON_PRESSED
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from .conftest import setup_platform

from tests.common import assert_setup_component, async_capture_events

SENDER_ID = [0xDE, 0xAD, 0xBE, 0xEF]

BINARY_SENSOR_CONFIG = {
    "binary_sensor": [
        {
            "platform": DOMAIN,
            "id": SENDER_ID,
            "name": "room0",
        },
    ]
}


@pytest.mark.parametrize(
    ("packets", "expected_event_data"),
    [
        (
            [{"R1": 0, "EB": 1, "R2": 0, "SA": 0, "NU": 1, "T21": 1}],
            {"pushed": 1, "which": 1, "onoff": 1},
        ),
        (
            [{"R1": 1, "EB": 1, "R2": 0, "SA": 0, "NU": 1, "T21": 1}],
            {"pushed": 1, "which": 1, "onoff": 0},
        ),
        (
            [{"R1": 2, "EB": 1, "R2": 0, "SA": 0, "NU": 1, "T21": 1}],
            {"pushed": 1, "which": 0, "onoff": 1},
        ),
        (
            [{"R1": 3, "EB": 1, "R2": 0, "SA": 0, "NU": 1, "T21": 1}],
            {"pushed": 1, "which": 0, "onoff": 0},
        ),
        (
            [{"R1": 0, "EB": 1, "R2": 2, "SA": 1, "NU": 1, "T21": 1}],
            {"pushed": 1, "which": 10, "onoff": 1},
        ),
        (
            [{"R1": 1, "EB": 1, "R2": 3, "SA": 1, "NU": 1, "T21": 1}],
            {"pushed": 1, "which": 10, "onoff": 0},
        ),
        (
            [
                {"R1": 0, "EB": 1, "R2": 0, "SA": 0, "NU": 1, "T21": 1},
                {"R1": 0, "EB": 0, "R2": 0, "SA": 0, "NU": 0, "T21": 1},
            ],
            {"pushed": 0, "which": 1, "onoff": 1},
        ),
        (
            [
                {"R1": 1, "EB": 1, "R2": 0, "SA": 0, "NU": 1, "T21": 1},
                {"R1": 0, "EB": 0, "R2": 0, "SA": 0, "NU": 0, "T21": 1},
            ],
            {"pushed": 0, "which": 1, "onoff": 0},
        ),
    ],
)
async def test_rocker_packets(
    hass: HomeAssistant,
    packets,
    expected_event_data,
) -> None:
    """Inject rocker switch packets and assert correct reaction."""
    communicator_mock = await setup_platform(hass, BINARY_SENSOR_DOMAIN)
    with assert_setup_component(1, BINARY_SENSOR_DOMAIN):
        assert await async_setup_component(
            hass,
            BINARY_SENSOR_DOMAIN,
            BINARY_SENSOR_CONFIG,
        )

    event_list = async_capture_events(hass, EVENT_BUTTON_PRESSED)

    for packet_content in packets:
        packet = RadioPacket.create(
            rorg=0xF6,
            rorg_func=0x02,
            rorg_type=0x02,
            sender=SENDER_ID,
            **packet_content,
        )
        communicator_mock.call_args_list[0].kwargs["callback"](packet)
        await hass.async_block_till_done()
    for field in expected_event_data:
        assert event_list[-1].data[field] == expected_event_data[field], (
            f"mismatch {field}"
        )
