"""Data update coordinator for the Invoxia GPS & Biotracker integration."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import InvoxiaAuthError, InvoxiaClient, InvoxiaError, is_tracker
from .const import (
    DEFAULT_ICON,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    LOCATION_METHODS,
    LOGGER,
    MAX_BACKOFF,
    STALE_TOLERANCE,
    TRACKER_ICONS,
    USAGE_ICONS,
)

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry


def _to_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value: Any) -> int | None:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _to_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    parsed = dt_util.parse_datetime(value)
    if parsed is not None and parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed


def _valid_position(lat: float | None, lng: float | None) -> bool:
    """Return True for real coordinates (0, 0 means "no fix")."""
    if lat is None or lng is None or (lat == 0 and lng == 0):
        return False
    return -90 <= lat <= 90 and -180 <= lng <= 180


@dataclass(slots=True)
class InvoxiaLocation:
    """A position reported by a tracker."""

    latitude: float
    longitude: float
    accuracy: int | None = None
    time: datetime | None = None
    method: int | None = None
    source: str = "tracker_data"

    @property
    def method_name(self) -> str | None:
        """Return a readable name for the acquisition method."""
        if self.method is None:
            return None
        return LOCATION_METHODS.get(self.method, f"method_{self.method}")


def _newest_location(
    locations: list[dict[str, Any]], status: dict[str, Any]
) -> InvoxiaLocation | None:
    """Pick the most recent position from tracker_data and tracker_status."""
    best: InvoxiaLocation | None = None
    for item in locations:
        lat, lng = _to_float(item.get("lat")), _to_float(item.get("lng"))
        if not _valid_position(lat, lng):
            continue
        candidate = InvoxiaLocation(
            latitude=lat,
            longitude=lng,
            accuracy=_to_int(item.get("precision")),
            time=_to_datetime(item.get("datetime")),
            method=_to_int(item.get("method")),
        )
        if best is None or (
            candidate.time is not None
            and (best.time is None or candidate.time > best.time)
        ):
            best = candidate

    lat = _to_float(status.get("last_loc_latitude"))
    lng = _to_float(status.get("last_loc_longitude"))
    if _valid_position(lat, lng):
        status_time = _to_datetime(status.get("last_location"))
        if best is None or (
            status_time is not None
            and best.time is not None
            and status_time > best.time
        ):
            best = InvoxiaLocation(
                latitude=lat, longitude=lng, time=status_time, source="tracker_status"
            )
    return best


@dataclass(slots=True)
class InvoxiaTracker:
    """Latest known data of one tracker."""

    device: dict[str, Any]
    status: dict[str, Any] = field(default_factory=dict)
    location: InvoxiaLocation | None = None
    locations_raw: list[dict[str, Any]] = field(default_factory=list)

    @property
    def id(self) -> int:
        """Return the tracker id."""
        return int(self.device["id"])

    @property
    def config(self) -> dict[str, Any]:
        """Return the tracker configuration block."""
        config = self.device.get("tracker_config")
        return config if isinstance(config, dict) else {}

    @property
    def name(self) -> str:
        """Return the name given in the Invoxia app."""
        return str(self.device.get("name") or f"Invoxia {self.id}")

    @property
    def device_type(self) -> str:
        """Return the raw device type reported by the API."""
        return str(self.device.get("type", "unknown"))

    @property
    def model(self) -> str:
        """Return the best available model description."""
        return str(
            self.device.get("model")
            or self.config.get("board_name")
            or self.device_type
        )

    @property
    def serial(self) -> str | None:
        """Return the serial number."""
        serial = self.device.get("serial")
        return str(serial) if serial else None

    @property
    def sw_version(self) -> str | None:
        """Return the firmware version."""
        version = self.device.get("version")
        return str(version) if version else None

    @property
    def icon(self) -> str:
        """Return an icon matching the one chosen in the Invoxia app."""
        icon_id = _to_int(self.config.get("icon"))
        if icon_id in TRACKER_ICONS:
            return TRACKER_ICONS[icon_id]
        return USAGE_ICONS.get(str(self.config.get("usage", "")), DEFAULT_ICON)

    @property
    def battery(self) -> int | None:
        """Return the battery level in percent."""
        return _to_int(self.status.get("battery"))

    @property
    def last_seen(self) -> datetime | None:
        """Return the last time the tracker contacted the cloud."""
        return _to_datetime(self.status.get("last_event"))

    @property
    def state(self) -> str | None:
        """Return the tracker state as reported by the API."""
        state = self.status.get("state")
        return str(state) if state not in (None, "") else None


class InvoxiaCoordinator(DataUpdateCoordinator[dict[int, InvoxiaTracker]]):
    """Fetch all trackers of an Invoxia account."""

    config_entry: ConfigEntry

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, client: InvoxiaClient
    ) -> None:
        """Initialize the coordinator."""
        minutes = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        super().__init__(
            hass,
            LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(minutes=minutes),
        )
        self.client = client
        self.raw_devices: list[dict[str, Any]] = []
        self._base_interval = timedelta(minutes=minutes)
        self._failures = 0
        # Options the entry was loaded with: other entry updates must not reload it.
        self.loaded_options = dict(entry.options)

    async def _async_update_data(self) -> dict[int, InvoxiaTracker]:
        """Fetch devices, statuses and latest positions."""
        previous = self.data or {}
        try:
            devices = await self.client.async_get_devices()
        except InvoxiaAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except InvoxiaError as err:
            return self._keep_last_values(err)
        self._failures = 0
        self.update_interval = self._base_interval

        self.raw_devices = devices
        trackers: dict[int, InvoxiaTracker] = {}
        for device in devices:
            if not is_tracker(device):
                continue
            tracker = InvoxiaTracker(device=device)
            LOGGER.debug("Tracker %s has type %s", tracker.id, tracker.device_type)

            try:
                status = device.get("tracker_status")
                if not isinstance(status, dict):
                    status = await self.client.async_get_tracker_status(tracker.id)
                tracker.status = status or {}
                tracker.locations_raw = await self.client.async_get_locations(
                    tracker.id
                )
            except InvoxiaAuthError as err:
                raise ConfigEntryAuthFailed(str(err)) from err
            except InvoxiaError as err:
                LOGGER.debug("Partial data for tracker %s: %s", tracker.id, err)

            tracker.location = _newest_location(tracker.locations_raw, tracker.status)
            if tracker.id in previous:
                # Keep the last known values when a request failed this time.
                tracker.status = tracker.status or previous[tracker.id].status
                tracker.location = tracker.location or previous[tracker.id].location
            trackers[tracker.id] = tracker

        return trackers

    def _keep_last_values(self, err: InvoxiaError) -> dict[int, InvoxiaTracker]:
        """Keep the last values through a few failed updates in a row."""
        self._failures += 1
        # Slow down while the API fails, so a struggling server is not hammered.
        self.update_interval = min(
            self._base_interval * 2**self._failures, timedelta(minutes=MAX_BACKOFF)
        )
        if self.data is not None and self._failures < STALE_TOLERANCE:
            LOGGER.debug(
                "Invoxia update failed (%s in a row), keeping the last values: %s",
                self._failures,
                err,
            )
            return self.data
        raise UpdateFailed(f"Error communicating with Invoxia: {err}") from err
