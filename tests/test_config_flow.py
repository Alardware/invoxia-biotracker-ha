"""Config flow tests."""

from __future__ import annotations

import aiohttp
from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.invoxia_biotracker.const import DOMAIN

from .conftest import API, PHONE, USER_INPUT, mock_api


async def _submit(hass: HomeAssistant, user_input: dict) -> dict:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    return await hass.config_entries.flow.async_configure(result["flow_id"], user_input)


async def test_user_flow_with_unknown_device_type(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """A Biotracker-like device of unknown type is accepted."""
    mock_api(aioclient_mock)
    result = await _submit(hass, USER_INPUT)
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "dog@example.com"
    assert result["data"][CONF_PASSWORD] == "secret"
    await hass.async_block_till_done()


async def test_user_flow_invalid_auth(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """A 401 answer is reported as invalid credentials."""
    aioclient_mock.get(f"{API}/devices/", status=401, json={"detail": "nope"})
    result = await _submit(hass, USER_INPUT)
    assert result["errors"] == {"base": "invalid_auth"}


async def test_user_flow_cannot_connect(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """A network error is reported as cannot_connect."""
    aioclient_mock.get(f"{API}/devices/", exc=aiohttp.ClientConnectionError())
    result = await _submit(hass, USER_INPUT)
    assert result["errors"] == {"base": "cannot_connect"}


async def test_user_flow_no_trackers(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """An account with only phones gets a dedicated error."""
    mock_api(aioclient_mock, devices=[PHONE])
    result = await _submit(hass, USER_INPUT)
    assert result["errors"] == {"base": "no_trackers"}


async def test_user_flow_server_error(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """A 500 answer is reported as an API error."""
    aioclient_mock.get(f"{API}/devices/", status=500, text="boom")
    result = await _submit(hass, USER_INPUT)
    assert result["errors"] == {"base": "api_error"}


async def test_options_flow(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    config_entry: MockConfigEntry,
) -> None:
    """The update interval can be changed."""
    mock_api(aioclient_mock)
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_SCAN_INTERVAL: 10}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert config_entry.options == {CONF_SCAN_INTERVAL: 10}


async def test_reauth_flow(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    config_entry: MockConfigEntry,
) -> None:
    """A new password is validated and stored."""
    mock_api(aioclient_mock)
    config_entry.add_to_hass(hass)
    result = await config_entry.start_reauth_flow(hass)
    assert result["step_id"] == "reauth_confirm"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_PASSWORD: "new-secret"}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert config_entry.data[CONF_PASSWORD] == "new-secret"
    await hass.async_block_till_done()


async def test_user_flow_refuses_http_url(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """Credentials are never sent to a plain http URL."""
    result = await _submit(hass, {**USER_INPUT, "api_url": "http://labs.invoxia.io"})
    assert result["errors"] == {"api_url": "insecure_url"}
    assert aioclient_mock.call_count == 0
