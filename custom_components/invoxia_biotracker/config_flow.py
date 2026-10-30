"""Config flow for the Invoxia GPS & Biotracker integration."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_PASSWORD, CONF_SCAN_INTERVAL, CONF_USERNAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)
import voluptuous as vol

from .api import (
    InvoxiaAuthError,
    InvoxiaClient,
    InvoxiaConnectionError,
    InvoxiaError,
    InvoxiaInsecureUrl,
    is_tracker,
)
from .const import (
    CONF_API_URL,
    DEFAULT_API_URL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    LOGGER,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)

PASSWORD_SELECTOR = TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD))


class NoTrackers(Exception):
    """Login worked but the account has no tracker."""


async def _async_validate(hass: HomeAssistant, data: Mapping[str, Any]) -> int:
    """Check credentials and return the number of trackers found."""
    client = InvoxiaClient(
        async_get_clientsession(hass),
        data[CONF_USERNAME],
        data[CONF_PASSWORD],
        data.get(CONF_API_URL, DEFAULT_API_URL),
    )
    devices = await client.async_get_devices()
    trackers = [device for device in devices if is_tracker(device)]
    types = [device.get("type") for device in devices]
    if not trackers:
        LOGGER.warning(
            "Invoxia login OK but no tracker found, device types returned: %s", types
        )
        raise NoTrackers
    LOGGER.debug("Invoxia login OK, device types returned: %s", types)
    return len(trackers)


def _errors_for(err: Exception) -> dict[str, str]:
    if isinstance(err, InvoxiaAuthError):
        return {"base": "invalid_auth"}
    if isinstance(err, InvoxiaConnectionError):
        return {"base": "cannot_connect"}
    if isinstance(err, InvoxiaInsecureUrl):
        return {CONF_API_URL: "insecure_url"}
    if isinstance(err, NoTrackers):
        return {"base": "no_trackers"}
    if isinstance(err, InvoxiaError):
        LOGGER.error("Unexpected answer from the Invoxia API: %s", err)
        return {"base": "api_error"}
    LOGGER.exception("Unexpected exception while connecting to Invoxia")
    return {"base": "unknown"}


class InvoxiaConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Invoxia."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for the Invoxia account credentials."""
        errors: dict[str, str] = {}
        if user_input is not None:
            user_input[CONF_USERNAME] = user_input[CONF_USERNAME].strip()
            await self.async_set_unique_id(user_input[CONF_USERNAME].lower())
            self._abort_if_unique_id_configured()
            try:
                await _async_validate(self.hass, user_input)
            except Exception as err:  # noqa: BLE001
                errors = _errors_for(err)
            else:
                return self.async_create_entry(
                    title=user_input[CONF_USERNAME], data=user_input
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_USERNAME): TextSelector(
                    TextSelectorConfig(type=TextSelectorType.EMAIL)
                ),
                vol.Required(CONF_PASSWORD): PASSWORD_SELECTOR,
                vol.Optional(CONF_API_URL, default=DEFAULT_API_URL): TextSelector(
                    TextSelectorConfig(type=TextSelectorType.URL)
                ),
            }
        )
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(schema, user_input),
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Start re-authentication after the password was rejected."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for the new password."""
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            data = {**entry.data, CONF_PASSWORD: user_input[CONF_PASSWORD]}
            try:
                await _async_validate(self.hass, data)
            except Exception as err:  # noqa: BLE001
                errors = _errors_for(err)
            else:
                return self.async_update_reload_and_abort(entry, data=data)

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_PASSWORD): PASSWORD_SELECTOR}),
            description_placeholders={"username": entry.data[CONF_USERNAME]},
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> InvoxiaOptionsFlow:
        """Return the options flow."""
        return InvoxiaOptionsFlow()


class InvoxiaOptionsFlow(OptionsFlow):
    """Let the user change the polling interval."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(
                data={CONF_SCAN_INTERVAL: int(user_input[CONF_SCAN_INTERVAL])}
            )

        current = self.config_entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
        )
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_SCAN_INTERVAL, default=current): NumberSelector(
                        NumberSelectorConfig(
                            min=MIN_SCAN_INTERVAL,
                            max=MAX_SCAN_INTERVAL,
                            step=1,
                            mode=NumberSelectorMode.BOX,
                            unit_of_measurement="min",
                        )
                    )
                }
            ),
        )
