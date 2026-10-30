"""Diagnostics for the Invoxia GPS & Biotracker integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant

from . import InvoxiaConfigEntry

TO_REDACT = {
    CONF_PASSWORD,
    CONF_USERNAME,
    "email",
    "firmware_path",
    "image",
    "lat",
    "last_loc_latitude",
    "last_loc_longitude",
    "lng",
    "serial",
    "title",
    "unique_id",
    "uuid",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: InvoxiaConfigEntry
) -> dict[str, Any]:
    """Return redacted raw API answers to help support new device types."""
    coordinator = entry.runtime_data
    return {
        "entry": async_redact_data(entry.as_dict(), TO_REDACT),
        "devices": async_redact_data(coordinator.raw_devices, TO_REDACT),
        "trackers": {
            tracker_id: {
                "type": tracker.device_type,
                "status": async_redact_data(tracker.status, TO_REDACT),
                "latest_locations": async_redact_data(
                    tracker.locations_raw[:3], TO_REDACT
                ),
                "selected_location_source": tracker.location.source
                if tracker.location
                else None,
            }
            for tracker_id, tracker in (coordinator.data or {}).items()
        },
    }
