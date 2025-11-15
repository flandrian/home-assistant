"""Fixtures for EnOcean integration tests.

This module provides helpers to set up a mocked Enocean communicator,
inject radio packets, and assert packet and entity state content in tests.
"""

from typing import Final
from unittest.mock import MagicMock, patch

from enocean.protocol.constants import PARSE_RESULT
from enocean.protocol.packet import Packet, RadioPacket
import pytest

from homeassistant.components.enocean.const import DOMAIN
from homeassistant.const import CONF_DEVICE
from homeassistant.core import HomeAssistant

from tests.common import MockConfigEntry

ENTRY_CONFIG: Final[dict[str, str]] = {
    CONF_DEVICE: "/dev/ttyUSB0",
}


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Return the default mocked config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        unique_id="device_chip_id",
        data=ENTRY_CONFIG,
    )


async def setup_platform(hass: HomeAssistant, platform: str) -> MockConfigEntry:
    """Set up the Enocean platform with a mocked communicator and return it."""
    mock_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "device": "/dev/null",
        },
    )
    mock_entry.add_to_hass(hass)

    with patch(
        "homeassistant.components.enocean.dongle.SerialCommunicator"
    ) as communicator_mock:
        await hass.config_entries.async_setup(mock_entry.entry_id)
    await hass.async_block_till_done()
    return communicator_mock


async def inject_packets(
    hass: HomeAssistant, packets: list, communicator_mock: MagicMock
) -> None:
    """Mock the reception of enocean packets by feeding them into the communicator mock."""
    for packet_content in packets:
        packet = RadioPacket.create(
            **packet_content,
        )
        communicator_mock.call_args_list[0].kwargs["callback"](packet)
    await hass.async_block_till_done()


def assert_state(hass: HomeAssistant, state_name: str, expected_state: tuple):
    """Asserte that the named entity has the state provided."""
    state = hass.states.get(state_name)
    assert state
    assert state.state == expected_state[0]
    expected_attributes = expected_state[1]
    for key in expected_attributes:
        assert state.attributes[key] == expected_attributes[key], f"mismatch {key}"


def get_sent_packet(communicator_mock: MagicMock):
    """Read the sent packets from the communicator mock and translate them so they appear as received packets."""
    sent_packet = communicator_mock.return_value.send.call_args[0][0]
    if len(sent_packet.optional) == 0:
        sent_packet.optional = [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
    raw_packet = sent_packet.build()
    result, _, transported_packet = Packet.parse_msg(raw_packet)
    assert result == PARSE_RESULT.OK

    return transported_packet


def assert_packet_content(
    expected_packet: dict, transported_packet: dict, command: int | None = None
):
    """Assert that a transported Enocean packet matches the expected content.

    Parameters
    ----------
    expected_packet : dict
        Mapping of expected EEP fields; keys may include 'rorg', 'rorg_func',
        'rorg_type', or other field names mapped to expected raw values.
    transported_packet : dict
        The parsed transported packet object returned by Packet.parse_msg.
    command : int | None
        Optional command value to pass to parse_eep.
    """
    transported_packet.parse_eep(
        expected_packet["rorg_func"],
        expected_packet["rorg_type"],
        command=command,
    )
    for field, expected_content in expected_packet.items():
        if field == "rorg":
            assert transported_packet.rorg == expected_content
        elif field == "rorg_func":
            assert transported_packet.rorg_func == expected_content
        elif field == "rorg_type":
            assert transported_packet.rorg_type == expected_content
        else:
            assert transported_packet.parsed[field]["raw_value"] == expected_content, (
                f"mismatch {field}"
            )
