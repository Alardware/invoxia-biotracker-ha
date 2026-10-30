"""Device tracker platform for the Invoxia GPS & Biotracker integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.device_tracker import TrackerEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import InvoxiaConfigEntry
from .coordinator import InvoxiaCoordinator
from .entity import InvoxiaEntity, async_add_new_trackers

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: InvoxiaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up device trackers for every Invoxia tracker."""
    coordinator = entry.runtime_data
    async_add_new_trackers(
        coordinator,
        entry.async_on_unload,
        lambda ids: async_add_entities(
            InvoxiaDeviceTracker(coordinator, tracker_id) for tracker_id in ids
        ),
    )


class InvoxiaDeviceTracker(InvoxiaEntity, TrackerEntity):
    """Position of an Invoxia tracker."""

    _attr_entity_category = None
    _attr_name = None

    def __init__(self, coordinator: InvoxiaCoordinator, tracker_id: int) -> None:
        """Initialize the tracker entity."""
        super().__init__(coordinator, tracker_id)
        self._attr_unique_id = str(tracker_id)
        self._update_from_tracker()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Refresh attributes from the latest coordinator data."""
        if self._tracker_id in self.coordinator.data:
            self._update_from_tracker()
        super()._handle_coordinator_update()

    def _update_from_tracker(self) -> None:
        tracker = self.tracker
        location = tracker.location
        self._attr_icon = tracker.icon
        self._attr_latitude = location.latitude if location else None
        self._attr_longitude = location.longitude if location else None
        self._attr_location_accuracy = float(location.accuracy or 0) if location else 0
        self._battery = tracker.battery
        self._attributes: dict[str, Any] = {
            "last_location": location.time.isoformat()
            if location and location.time
            else None,
            "location_method": location.method_name if location else None,
            "location_source": location.source if location else None,
            "invoxia_device_type": tracker.device_type,
        }

    @property
    def battery_level(self) -> int | None:
        """Return the battery level."""
        return self._battery

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return details about the last position."""
        return self._attributes
