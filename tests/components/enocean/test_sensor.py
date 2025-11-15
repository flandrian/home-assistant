"""Tests for the EnOcean sensor platform."""

import copy

import pytest

from homeassistant.components.enocean import DOMAIN
from homeassistant.components.enocean.sensor import (
    CONF_MAX_TEMP,
    CONF_MIN_TEMP,
    CONF_RANGE_FROM,
    CONF_RANGE_TO,
)
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from .conftest import assert_state, inject_packets, setup_platform

from tests.common import assert_setup_component

SENDER_ID = [0xDE, 0xAD, 0xBE, 0xEF]
POWER_SENSOR_CONFIG = {
    "sensor": [
        {
            "platform": DOMAIN,
            "id": SENDER_ID,
            "name": "room0",
            "device_class": "powersensor",
        },
    ]
}


@pytest.mark.parametrize(
    ("packets", "expected_state"),
    [
        (
            [
                {
                    "sender": SENDER_ID,
                    "rorg": 0xA5,
                    "rorg_func": 0x12,
                    "rorg_type": 0x01,
                    "MR": 42,
                    "DT": 1,
                    "DIV": 1,
                }
            ],
            ("4.2", {}),
        ),
    ],
)
async def test_powersensor_packets(
    hass: HomeAssistant,
    packets,
    expected_state,
) -> None:
    """Inject power sensor packets and assert correct reaction."""
    communicator_mock = await setup_platform(hass, SENSOR_DOMAIN)
    with assert_setup_component(1, SENSOR_DOMAIN):
        assert await async_setup_component(
            hass,
            SENSOR_DOMAIN,
            POWER_SENSOR_CONFIG,
        )

    await inject_packets(hass, packets, communicator_mock)

    assert_state(hass, "sensor.power_room0", expected_state)


TEMPERATURE_SENSOR_CONFIG = {
    "sensor": [
        {
            "platform": DOMAIN,
            "id": SENDER_ID,
            "name": "room0",
            "device_class": "temperature",
        },
    ]
}


@pytest.mark.parametrize(
    ("packets", "scale_config", "expected_state"),
    [
        (
            [
                {
                    "rorg": 0xA5,
                    "sender": SENDER_ID,
                    "rorg_func": 0x02,
                    "rorg_type": 0x01,
                    "TMP": -4.2,
                }
            ],
            {
                CONF_MIN_TEMP: -40,
                CONF_MAX_TEMP: 0,
                CONF_RANGE_FROM: 255,
                CONF_RANGE_TO: 0,
            },
            ("-4.1", {}),
        ),
        # (
        #     [
        #         {
        #             "rorg": 0xA5,
        #             "sender": SENDER_ID,
        #             "rorg_func": 0x10,
        #             "rorg_type": 0x01,
        #             "TMP": 22.5,
        #         }
        #     ],
        #     {
        #         CONF_MIN_TEMP: 0,
        #         CONF_MAX_TEMP: 40,
        #         CONF_RANGE_FROM: 255,
        #         CONF_RANGE_TO: 0,
        #     },
        #     ("22.6", {}),
        # ),
        (
            [
                {
                    "rorg": 0xA5,
                    "sender": SENDER_ID,
                    "rorg_func": 0x04,
                    "rorg_type": 0x01,
                    "TMP": 15,
                }
            ],
            {
                CONF_MIN_TEMP: 0,
                CONF_MAX_TEMP: 40,
                CONF_RANGE_FROM: 0,
                CONF_RANGE_TO: 250,
            },
            ("14.9", {}),
        ),
        # (
        #     [
        #         {
        #             "rorg": 0xA5,
        #             "sender": SENDER_ID,
        #             "rorg_func": 0x04,
        #             "rorg_type": 0x02,
        #             "TMP": 15,
        #         }
        #     ],
        #     {
        #         CONF_MIN_TEMP: -20,
        #         CONF_MAX_TEMP: 60,
        #         CONF_RANGE_FROM: 0,
        #         CONF_RANGE_TO: 250,
        #     },
        #     ("14.9", {}),
        # ),
        # (
        #     [
        #         {
        #             "rorg": 0xA5,
        #             "sender": SENDER_ID,
        #             "rorg_func": 0x10,
        #             "rorg_type": 0x10,
        #             "TMP": 32,
        #         }
        #     ],
        #     {
        #         CONF_MIN_TEMP: 0,
        #         CONF_MAX_TEMP: 40,
        #         CONF_RANGE_FROM: 0,
        #         CONF_RANGE_TO: 250,
        #     },
        #     ("32.0", {}),
        # ),
        # (
        #     [
        #         {
        #             "rorg": 0xA5,
        #             "sender": SENDER_ID,
        #             "rorg_func": 0x10,
        #             "rorg_type": 0x12,
        #             "TMP": 12,
        #         }
        #     ],
        #     {
        #         CONF_MIN_TEMP: 0,
        #         CONF_MAX_TEMP: 40,
        #         CONF_RANGE_FROM: 0,
        #         CONF_RANGE_TO: 250,
        #     },
        #     ("12.0", {}),
        # ),
    ],
)
async def test_temperaturesensor_packets(
    hass: HomeAssistant,
    packets,
    scale_config,
    expected_state,
) -> None:
    """Inject temperature sensor packets and assert correct reaction."""
    communicator_mock = await setup_platform(hass, SENSOR_DOMAIN)

    sensor_config = copy.deepcopy(TEMPERATURE_SENSOR_CONFIG)
    sensor_config["sensor"][0].update(scale_config)
    with assert_setup_component(1, SENSOR_DOMAIN):
        assert await async_setup_component(
            hass,
            SENSOR_DOMAIN,
            sensor_config,
        )

    await inject_packets(hass, packets, communicator_mock)

    assert_state(hass, "sensor.temperature_room0", expected_state)


HUMIDITY_SENSOR_CONFIG = {
    "sensor": [
        {
            "platform": DOMAIN,
            "id": SENDER_ID,
            "name": "room0",
            "device_class": "humidity",
        },
    ]
}


@pytest.mark.parametrize(
    ("packets", "scale_config", "expected_state"),
    [
        (
            [
                {
                    "rorg": 0xA5,
                    "sender": SENDER_ID,
                    "rorg_func": 0x04,
                    "rorg_type": 0x01,
                    "HUM": 42,
                }
            ],
            {},
            ("42.0", {}),
        ),
        # (
        #     [
        #         {
        #             "rorg": 0xA5,
        #             "sender": SENDER_ID,
        #             "rorg_func": 0x04,
        #             "rorg_type": 0x02,
        #             "HUM": 56,
        #         }
        #     ],
        #     {},
        #     ("56.0", {}),
        # ),
        (
            [
                {
                    "rorg": 0xA5,
                    "sender": SENDER_ID,
                    "rorg_func": 0x10,
                    "rorg_type": 0x12,
                    "HUM": 15,
                }
            ],
            {},
            ("14.8", {}),
        ),
    ],
)
async def test_humiditysensor_packets(
    hass: HomeAssistant,
    packets,
    scale_config,
    expected_state,
) -> None:
    """Inject temperature sensor packets and assert correct reaction."""
    sensor_config = copy.deepcopy(HUMIDITY_SENSOR_CONFIG)
    sensor_config["sensor"][0].update(scale_config)
    communicator_mock = await setup_platform(hass, SENSOR_DOMAIN)
    with assert_setup_component(1, SENSOR_DOMAIN):
        assert await async_setup_component(
            hass,
            SENSOR_DOMAIN,
            sensor_config,
        )

    await inject_packets(hass, packets, communicator_mock)

    assert_state(hass, "sensor.humidity_room0", expected_state)
