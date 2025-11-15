"""Tests for the EnOcean switch platform."""

import copy

from enocean.utils import combine_hex
import pytest

from homeassistant.components.enocean import DOMAIN
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.const import ATTR_ENTITY_ID, SERVICE_TURN_OFF, SERVICE_TURN_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component

from .conftest import (
    assert_packet_content,
    assert_state,
    get_sent_packet,
    inject_packets,
    setup_platform,
)

from tests.common import MockConfigEntry, assert_setup_component

DEVICE_ID = [0xDE, 0xAD, 0xBE, 0xEF]
SWITCH_CONFIG = {
    "switch": [
        {
            "platform": DOMAIN,
            "id": DEVICE_ID,
            "channel": 1,
            "name": "room0",
        },
    ]
}


async def test_unique_id_migration(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test EnOcean switch ID migration."""

    entity_name = SWITCH_CONFIG["switch"][0]["name"]
    switch_entity_id = f"{SWITCH_DOMAIN}.{entity_name}"
    dev_id = SWITCH_CONFIG["switch"][0]["id"]
    channel = SWITCH_CONFIG["switch"][0]["channel"]

    old_unique_id = f"{combine_hex(dev_id)}"

    entry = MockConfigEntry(domain=DOMAIN, data={"device": "/dev/null"})

    entry.add_to_hass(hass)

    # Add a switch with an old unique_id to the entity registry
    entity_entry = entity_registry.async_get_or_create(
        SWITCH_DOMAIN,
        DOMAIN,
        old_unique_id,
        suggested_object_id=entity_name,
        config_entry=entry,
        original_name=entity_name,
    )

    assert entity_entry.entity_id == switch_entity_id
    assert entity_entry.unique_id == old_unique_id

    # Now add the sensor to check, whether the old unique_id is migrated

    with assert_setup_component(1, SWITCH_DOMAIN):
        assert await async_setup_component(
            hass,
            SWITCH_DOMAIN,
            SWITCH_CONFIG,
        )

    await hass.async_block_till_done()

    # Check that new entry has a new unique_id
    entity_entry = entity_registry.async_get(switch_entity_id)
    new_unique_id = f"{combine_hex(dev_id)}-{channel}"

    assert entity_entry.unique_id == new_unique_id
    assert (
        entity_registry.async_get_entity_id(SWITCH_DOMAIN, DOMAIN, old_unique_id)
        is None
    )


@pytest.mark.parametrize(
    ("packets", "extra_config", "expected_state"),
    [
        (
            [
                {
                    "sender": DEVICE_ID,
                    "rorg": 0xD2,
                    "rorg_func": 0x01,
                    "rorg_type": 0x01,
                    "command": 4,
                    "CMD": 4,
                    "IO": 0,
                    "OV": 0,
                }
            ],
            {
                "channel": 0,
            },
            ("off", {}),
        ),
        (
            [
                {
                    "sender": DEVICE_ID,
                    "rorg": 0xD2,
                    "rorg_func": 0x01,
                    "rorg_type": 0x01,
                    "command": 4,
                    "CMD": 4,
                    "IO": 0,
                    "OV": 1,
                }
            ],
            {
                "channel": 0,
            },
            ("on", {}),
        ),
        (
            [
                {
                    "sender": DEVICE_ID,
                    "rorg": 0xD2,
                    "rorg_func": 0x01,
                    "rorg_type": 0x01,
                    "command": 4,
                    "CMD": 4,
                    "IO": 1,
                    "OV": 1,
                }
            ],
            {
                "channel": 1,
            },
            ("on", {}),
        ),
    ],
)
async def test_switch_packets(
    hass: HomeAssistant,
    packets,
    extra_config,
    expected_state,
) -> None:
    """Inject temperature sensor packets and assert correct reaction."""
    sensor_config = copy.deepcopy(SWITCH_CONFIG)
    sensor_config["switch"][0].update(extra_config)
    communicator_mock = await setup_platform(hass, SWITCH_DOMAIN)
    with assert_setup_component(1, SWITCH_DOMAIN):
        assert await async_setup_component(
            hass,
            SWITCH_DOMAIN,
            sensor_config,
        )

    await inject_packets(hass, packets, communicator_mock)

    assert_state(hass, "switch.room0", expected_state)


@pytest.mark.parametrize(
    ("expected_packet", "extra_config", "expected_state"),
    [
        (
            {
                "rorg": 0xD2,
                "rorg_func": 0x01,
                "rorg_type": 0x01,
                "CMD": 1,
                "DV": 0,
                "IO": 0,
                "OV": 0x64,
            },
            SERVICE_TURN_ON,
            {
                "channel": 0,
            },
            "on",
        ),
        (
            {
                "rorg": 0xD2,
                "rorg_func": 0x01,
                "rorg_type": 0x01,
                "CMD": 1,
                "DV": 0,
                "IO": 0,
                "OV": 0x0,
            },
            SERVICE_TURN_OFF,
            {
                "channel": 0,
            },
            "off",
        ),
    ],
)
async def test_switch_send_packets(
    hass: HomeAssistant,
    expected_packet,
    service,
    extra_config,
    expected_state,
) -> None:
    """Inject temperature sensor packets and assert correct reaction."""
    switch_config = copy.deepcopy(SWITCH_CONFIG)
    switch_config["switch"][0].update(extra_config)
    communicator_mock = await setup_platform(hass, SWITCH_DOMAIN)
    with assert_setup_component(1, SWITCH_DOMAIN):
        assert await async_setup_component(
            hass,
            SWITCH_DOMAIN,
            switch_config,
        )

    await hass.services.async_call(
        SWITCH_DOMAIN,
        service,
        {ATTR_ENTITY_ID: "switch.room0"},
    )

    await hass.async_block_till_done()
    state = hass.states.get("switch.room0")
    assert state
    assert state.state == expected_state

    sent_packet = get_sent_packet(communicator_mock)

    assert_packet_content(expected_packet, sent_packet, command=1)
    assert sent_packet.destination == DEVICE_ID
