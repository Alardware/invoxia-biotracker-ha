"""Sensor platform for the Invoxia GPS & Biotracker integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfLength
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import InvoxiaConfigEntry
from .coordinator import InvoxiaCoordinator, InvoxiaTracker
from .entity import InvoxiaEntity, async_add_new_trackers

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class InvoxiaSensorDescription(SensorEntityDescription):
    """Describe an Invoxia sensor."""

    value_fn: Callable[[InvoxiaTracker], int | float | str | datetime | None]


SENSORS: tuple[InvoxiaSensorDescription, ...] = (
    InvoxiaSensorDescription(
        key="battery",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda tracker: tracker.battery,
    ),
    InvoxiaSensorDescription(
        key="last_location",
        translation_key="last_location",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda tracker: tracker.location.time if tracker.location else None,
    ),
    InvoxiaSensorDescription(
        key="last_seen",
        translation_key="last_seen",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda tracker: tracker.last_seen,
    ),
    InvoxiaSensorDescription(
        key="location_accuracy",
        translation_key="location_accuracy",
        device_class=SensorDeviceClass.DISTANCE,
        native_unit_of_measurement=UnitOfLength.METERS,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda tracker: (
            tracker.location.accuracy if tracker.location else None
        ),
    ),
    InvoxiaSensorDescription(
        key="location_method",
        translation_key="location_method",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda tracker: (
            tracker.location.method_name if tracker.location else None
        ),
    ),
    InvoxiaSensorDescription(
        key="tracker_state",
        translation_key="tracker_state",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda tracker: tracker.state,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: InvoxiaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up sensors for every Invoxia tracker."""
    coordinator = entry.runtime_data
    async_add_new_trackers(
        coordinator,
        entry.async_on_unload,
        lambda ids: async_add_entities(
            InvoxiaSensor(coordinator, tracker_id, description)
            for tracker_id in ids
            for description in SENSORS
        ),
    )


class InvoxiaSensor(InvoxiaEntity, SensorEntity):
    """Sensor exposing one value of an Invoxia tracker."""

    entity_description: InvoxiaSensorDescription

    def __init__(
        self,
        coordinator: InvoxiaCoordinator,
        tracker_id: int,
        description: InvoxiaSensorDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, tracker_id)
        self.entity_description = description
        self._attr_unique_id = f"{tracker_id}_{description.key}"

    @property
    def native_value(self) -> int | float | str | datetime | None:
        """Return the sensor value."""
        return self.entity_description.value_fn(self.tracker)
