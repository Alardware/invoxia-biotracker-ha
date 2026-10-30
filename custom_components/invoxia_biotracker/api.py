"""Minimal asynchronous client for the Invoxia cloud API.

Endpoints and authentication scheme come from the community `gps_tracker`
library (https://gitlab.com/ezlo.picori/gps_tracker). Unlike that library,
answers are kept as plain dictionaries: unknown device types (such as the
Minitailz Biotracker) or new fields never make the client fail.
"""

from __future__ import annotations

from typing import Any

import aiohttp
from yarl import URL

from .const import DEFAULT_API_URL, PHONE_DEVICE_TYPES

REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=30)


class InvoxiaError(Exception):
    """Base error raised by the Invoxia client."""


class InvoxiaAuthError(InvoxiaError):
    """Credentials were rejected by the API."""


class InvoxiaConnectionError(InvoxiaError):
    """The API could not be reached."""


class InvoxiaApiError(InvoxiaError):
    """The API answered with an error or an unexpected payload."""

    def __init__(self, path: str, status: int | None, message: str = "") -> None:
        """Store request details."""
        self.path = path
        self.status = status
        super().__init__(f"{path}: HTTP {status} {message}".strip())


class InvoxiaInsecureUrl(InvoxiaError):
    """The API URL is not an https URL: credentials would leak."""


def validate_api_url(api_url: str) -> str:
    """Return the API URL without trailing slash, refusing anything but https."""
    url = URL(api_url.strip())
    if url.scheme != "https" or not url.host:
        raise InvoxiaInsecureUrl(f"Refusing non-https API URL: {api_url}")
    return str(url).rstrip("/")


def is_tracker(device: dict[str, Any]) -> bool:
    """Return True if a device returned by the API is a tracker (not a phone)."""
    return "id" in device and str(device.get("type", "")) not in PHONE_DEVICE_TYPES


class InvoxiaClient:
    """Read-only client for the Invoxia API."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        username: str,
        password: str,
        api_url: str = DEFAULT_API_URL,
    ) -> None:
        """Initialize the client."""
        self._session = session
        self._auth = aiohttp.BasicAuth(username, password)
        # Credentials travel in every request: never send them in clear text.
        self._api_url = validate_api_url(api_url)

    async def _get(self, path: str) -> Any:
        """Run a GET request and return the decoded JSON answer."""
        url = f"{self._api_url}/{path}"
        try:
            async with self._session.get(
                url, auth=self._auth, timeout=REQUEST_TIMEOUT
            ) as resp:
                if resp.status == 401:
                    raise InvoxiaAuthError("Invalid credentials")
                if resp.status == 204:
                    return None
                if resp.status >= 400:
                    raise InvoxiaApiError(path, resp.status, await resp.text())
                try:
                    return await resp.json(content_type=None)
                except ValueError as err:
                    raise InvoxiaApiError(path, resp.status, "invalid JSON") from err
        except (aiohttp.ClientError, TimeoutError) as err:
            raise InvoxiaConnectionError(str(err) or type(err).__name__) from err

    async def async_get_devices(self) -> list[dict[str, Any]]:
        """Return every device of the account (trackers and phones)."""
        data = await self._get("devices/")
        if data is None:
            return []
        if not isinstance(data, list):
            raise InvoxiaApiError("devices/", 200, "unexpected answer")
        return [item for item in data if isinstance(item, dict)]

    async def async_get_tracker_status(self, device_id: int) -> dict[str, Any] | None:
        """Return the current status of a tracker."""
        data = await self._get(f"devices/{device_id}/tracker_status/")
        return data if isinstance(data, dict) else None

    async def async_get_locations(self, device_id: int) -> list[dict[str, Any]]:
        """Return the latest locations of a tracker (up to 20, newest first)."""
        data = await self._get(f"devices/{device_id}/tracker_data/")
        if not isinstance(data, list):
            return []
        return [item for item in data if isinstance(item, dict)]
