"""Constants for the Invoxia GPS & Biotracker integration."""

from __future__ import annotations

import logging

DOMAIN = "invoxia_biotracker"
LOGGER = logging.getLogger(__package__)

ATTRIBUTION = "Data retrieved from the Invoxia cloud (unofficial integration)"

CONF_API_URL = "api_url"
DEFAULT_API_URL = "https://labs.invoxia.io"

# Polling interval, in minutes. Kept conservative: the API is not public.
DEFAULT_SCAN_INTERVAL = 5
MIN_SCAN_INTERVAL = 3
MAX_SCAN_INTERVAL = 60
# Consecutive failed updates during which the last values stay shown, so a
# single failed answer does not make the trackers unavailable.
STALE_TOLERANCE = 3
# After a failed update the interval doubles, up to this many minutes.
MAX_BACKOFF = 30

# Device types returned by the API that are smartphones, not trackers.
PHONE_DEVICE_TYPES = {"android", "iphone", "ios"}

# Location acquisition methods (tracker_data "method" field).
LOCATION_METHODS: dict[int, str] = {
    0: "unknown",
    1: "network",
    2: "gps",
    3: "wifi",
    4: "place",
    5: "ubiscale",
    6: "phone",
    7: "wifi",
    8: "server",
    9: "wifi",
    10: "wifi",
    11: "wifi",
    12: "fleet_correction",
    13: "bluetooth",
    14: "gps",
    15: "phone",
}

# Icon id configured in the Invoxia app -> Material Design icon.
TRACKER_ICONS: dict[int, str] = {
    0: "mdi:cube",
    1: "mdi:purse",
    2: "mdi:briefcase",
    3: "mdi:bag-suitcase",
    5: "mdi:bag-personal",
    7: "mdi:bicycle-basket",
    8: "mdi:sail-boat",
    10: "mdi:car-hatchback",
    12: "mdi:caravan",
    13: "mdi:dolly",
    14: "mdi:dog",
    15: "mdi:kayaking",
    16: "mdi:laptop",
    17: "mdi:motorbike",
    18: "mdi:helicopter",
    19: "mdi:airplane",
    21: "mdi:moped",
    23: "mdi:tent",
    24: "mdi:truck",
    26: "mdi:tractor",
    31: "mdi:cat",
    32: "mdi:face-man",
    34: "mdi:face-woman",
    36: "mdi:excavator",
    37: "mdi:paw",
    38: "mdi:human-female",
    39: "mdi:human-male",
    40: "mdi:scooter",
    41: "mdi:beehive-outline",
    42: "mdi:garage",
    43: "mdi:antenna",
    44: "mdi:hospital-box",
    45: "mdi:washing-machine",
    46: "mdi:key-chain-variant",
    47: "mdi:television",
    48: "mdi:cellphone",
}

USAGE_ICONS: dict[str, str] = {
    "dog": "mdi:dog",
    "cat": "mdi:cat",
    "pet": "mdi:paw",
    "bike": "mdi:bicycle",
    "moto": "mdi:motorbike",
    "vehicle": "mdi:car",
    "child": "mdi:human-child",
    "person": "mdi:account",
}

DEFAULT_ICON = "mdi:crosshairs-gps"
