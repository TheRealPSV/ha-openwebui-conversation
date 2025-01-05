"""Custom integration to integrate openwebui_conversation with Home Assistant.
"""

from __future__ import annotations

from typing import Literal

from homeassistant.components import conversation as haconversation
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import MATCH_ALL, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import (
    ConfigEntryNotReady,
    HomeAssistantError,
    TemplateError,
)
from homeassistant.helpers import intent, template
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import ulid

from .api import OpenWebUIApiClient
from .const import (
    DOMAIN,
    LOGGER,
    CONF_BASE_URL,
    CONF_API_KEY,
    CONF_TIMEOUT,
    CONF_MODEL,
    CONF_VERIFY_SSL,
    DEFAULT_TIMEOUT,
    DEFAULT_MODEL,
    DEFAULT_VERIFY_SSL,
)
from .conversation import OpenWebUIAgent
from .coordinator import OpenWebUIDataUpdateCoordinator
from .exceptions import ApiClientError, ApiCommError, ApiJsonError, ApiTimeoutError

PLATFORMS = (Platform.CONVERSATION,)


# https://developers.home-assistant.io/docs/config_entries_index/#setting-up-an-entry
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up OpenWebUI conversation using UI."""
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = entry
    client = OpenWebUIApiClient(
        base_url=entry.data[CONF_BASE_URL],
        api_key=entry.data[CONF_API_KEY],
        timeout=entry.options.get(CONF_TIMEOUT, DEFAULT_TIMEOUT),
        session=async_get_clientsession(hass),
        verify_ssl=entry.options.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL),
    )

    hass.data[DOMAIN][entry.entry_id] = coordinator = OpenWebUIDataUpdateCoordinator(
        hass,
        client,
    )
    # https://developers.home-assistant.io/docs/integration_fetching_data#coordinated-single-api-poll-for-data-for-all-entities
    await coordinator.async_config_entry_first_refresh()

    try:
        response = await client.async_get_heartbeat()
        if not response:
            raise ApiClientError("Invalid OpenWebUI server")
    except ApiClientError as err:
        raise ConfigEntryNotReady(err) from err

    haconversation.async_set_agent(hass, entry, OpenWebUIAgent(hass, entry))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload OpenWebUI conversation."""
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False
    hass.data[DOMAIN].pop(entry.entry_id)
    return True


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload OpenWebUI conversation."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
