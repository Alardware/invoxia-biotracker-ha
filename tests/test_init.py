"""Setup, entities and diagnostics tests."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.components.diagnostics import (
    get_diagnostics_for_config_entry,
)
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.invoxia_biotracker.const import DOMAIN

from .conftest import API, BIOTRACKER, TRACKER_ID, mock_api


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def test_entities_for_unknown_tracker_type(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    config_entry: MockConfigEntry,
) -> None:
    """The tracker and its sensors are created with the newest position."""
    mock_api(aioclient_mock)
    await _setup(hass, config_entry)
    assert config_entry.state is ConfigEntryState.LOADED

    tracker = hass.states.get("device_tracker.rex")
    assert tracker is not None
    assert tracker.attributes["latitude"] == 45.2
    assert tracker.attributes["longitude"] == 5.2
    assert tracker.attributes["gps_accuracy"] == 30
    assert tracker.attributes["battery_level"] == 76
    assert tracker.attributes["location_method"] == "method_21"
    assert tracker.attributes["invoxia_device_type"] == "tracker_05"
    assert tracker.attributes["icon"] == "mdi:dog"

    assert hass.states.get("sensor.rex_battery").state == "76"
    assert (
        hass.states.get("sensor.rex_last_position").state == "2026-10-30T14:55:00+00:00"
    )
    assert hass.states.get("sensor.rex_last_seen").state == "2026-10-30T14:59:00+00:00"
    assert hass.states.get("sensor.rex_tracker_state").state == "active"
    # The phone of the account is not a tracker.
    assert len(hass.states.async_entity_ids("device_tracker")) == 1

    device = dr.async_get(hass).async_get_device(
        identifiers={(DOMAIN, str(TRACKER_ID))}
    )
    assert device is not None
    assert device.manufacturer == "Invoxia"
    assert device.model == "Biotracker"


async def test_status_position_used_without_tracker_data(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    config_entry: MockConfigEntry,
) -> None:
    """The position of tracker_status is used when tracker_data is empty."""
    mock_api(aioclient_mock, locations=[])
    await _setup(hass, config_entry)

    tracker = hass.states.get("device_tracker.rex")
    assert tracker.attributes["latitude"] == 45.1
    assert tracker.attributes["longitude"] == 5.1
    assert tracker.attributes["location_source"] == "tracker_status"


async def test_tracker_data_failure_is_not_fatal(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    config_entry: MockConfigEntry,
) -> None:
    """A failing tracker_data endpoint (e.g. 403) does not break setup."""
    aioclient_mock.get(f"{API}/devices/", json=[BIOTRACKER])
    aioclient_mock.get(f"{API}/devices/{TRACKER_ID}/tracker_data/", status=403)
    await _setup(hass, config_entry)

    assert config_entry.state is ConfigEntryState.LOADED
    tracker = hass.states.get("device_tracker.rex")
    assert tracker.attributes["latitude"] == 45.1


async def test_invalid_auth_starts_reauth(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    config_entry: MockConfigEntry,
) -> None:
    """A rejected password triggers the re-authentication flow."""
    aioclient_mock.get(f"{API}/devices/", status=401)
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert config_entry.state is ConfigEntryState.SETUP_ERROR
    flows = hass.config_entries.flow.async_progress()
    assert [flow["context"]["source"] for flow in flows] == ["reauth"]


async def test_diagnostics_are_redacted(
    hass: HomeAssistant,
    hass_client,
    aioclient_mock: AiohttpClientMocker,
    config_entry: MockConfigEntry,
) -> None:
    """Credentials, serial numbers and coordinates are hidden."""
    mock_api(aioclient_mock)
    await _setup(hass, config_entry)

    diag = await get_diagnostics_for_config_entry(hass, hass_client, config_entry)
    text = str(diag)
    for secret in ("secret", "dog@example.com", "a1b2c3d4e5f6", "45.2", "45.1"):
        assert secret not in text
    assert diag["trackers"][str(TRACKER_ID)]["type"] == "tracker_05"
