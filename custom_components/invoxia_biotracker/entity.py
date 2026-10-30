"""Base entity for the Invoxia GPS & Biotracker integration."""

from __future__ import annotations

from collections.abc import Callable

from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, DOMAIN
from .coordinator import InvoxiaCoordinator, InvoxiaTracker


class InvoxiaEntity(CoordinatorEntity[InvoxiaCoordinator]):
    """Entity attached to one Invoxia tracker."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True

    def __init__(self, coordinator: InvoxiaCoordinator, tracker_id: int) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._tracker_id = tracker_id
        tracker = coordinator.data[tracker_id]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(tracker_id))},
            manufacturer="Invoxia",
            name=tracker.name,
            model=tracker.model,
            serial_number=tracker.serial,
            sw_version=tracker.sw_version,
        )

    @property
    def tracker(self) -> InvoxiaTracker:
        """Return the latest data of the tracker."""
        return self.coordinator.data[self._tracker_id]

    @property
    def available(self) -> bool:
        """Return True if the tracker is still part of the account."""
        return super().available and self._tracker_id in self.coordinator.data


def async_add_new_trackers(
    coordinator: InvoxiaCoordinator,
    async_on_unload: Callable[[Callable[[], None]], None],
    add_entities: Callable[[list[int]], None],
) -> None:
    """Call add_entities now and whenever a tracker is added to the account."""
    known: set[int] = set()

    @callback
    def _check() -> None:
        new = [tracker_id for tracker_id in coordinator.data if tracker_id not in known]
        if new:
            known.update(new)
            add_entities(new)

    _check()
    async_on_unload(coordinator.async_add_listener(_check))
