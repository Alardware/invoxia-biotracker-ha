"""Fixtures for the Invoxia GPS & Biotracker tests."""

from __future__ import annotations

from typing import Any

from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.invoxia_biotracker.const import DEFAULT_API_URL, DOMAIN

API = DEFAULT_API_URL
TRACKER_ID = 4242

# Shape modelled on the gps-tracker fixtures, with a device type, an icon and a
# location method that the gps-tracker library does not know.
BIOTRACKER: dict[str, Any] = {
    "id": TRACKER_ID,
    "type": "tracker_05",
    "name": "Rex",
    "created": "2025-06-01T10:00:00.000000Z",
    "version": "2.3.1",
    "serial": "a1b2c3d4e5f6",
    "model": "Biotracker",
    "tracker_config": {"icon": 99, "usage": "dog", "board_name": "MTZ01"},
    "tracker_status": {
        "battery": 76,
        "last_event": "2026-10-30T14:59:00Z",
        "last_location": "2026-10-30T14:50:00Z",
        "last_loc_latitude": 45.1,
        "last_loc_longitude": 5.1,
        "state": "active",
        "sub_state": "",
    },
}
PHONE: dict[str, Any] = {
    "id": 1,
    "type": "android",
    "name": "Phone",
    "created": "2025-06-01T10:00:00Z",
    "version": "14",
    "serial": "00000000-0000-0000-0000-000000000000",
}
LOCATIONS: list[dict[str, Any]] = [
    {
        "datetime": "2026-10-30T14:55:00.000000Z",
        "lat": "45.2",
        "lng": "5.2",
        "method": 21,
        "precision": 30,
        "pkt_drop": 0,
        "uuid": "11111111-1111-1111-1111-111111111111",
    },
    {
        "datetime": "2026-10-30T14:40:00.000000Z",
        "lat": "45.0",
        "lng": "5.0",
        "method": 2,
        "precision": 10,
        "pkt_drop": 0,
        "uuid": "22222222-2222-2222-2222-222222222222",
    },
]

USER_INPUT = {CONF_USERNAME: "dog@example.com", CONF_PASSWORD: "secret"}


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable loading custom integrations in all tests."""
    return


def mock_api(
    aioclient_mock: AiohttpClientMocker,
    devices: list[dict[str, Any]] | None = None,
    locations: list[dict[str, Any]] | None = None,
) -> None:
    """Register fake Invoxia API answers."""
    aioclient_mock.get(
        f"{API}/devices/", json=[PHONE, BIOTRACKER] if devices is None else devices
    )
    aioclient_mock.get(
        f"{API}/devices/{TRACKER_ID}/tracker_data/",
        json=LOCATIONS if locations is None else locations,
    )


@pytest.fixture
def config_entry() -> MockConfigEntry:
    """Return a config entry for the fake account."""
    return MockConfigEntry(
        domain=DOMAIN, data=USER_INPUT, unique_id=USER_INPUT[CONF_USERNAME]
    )
