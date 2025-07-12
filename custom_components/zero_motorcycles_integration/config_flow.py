"""Adds config flow for Blueprint."""
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, CONF_SCAN_INTERVAL
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.schema_config_entry_flow import (
    SchemaFlowFormStep,
    SchemaOptionsFlowHandler,
)

from .api import (
    ZeroApiClient,
    ZeroApiClientAuthenticationError,
    ZeroApiClientCommunicationError,
    ZeroApiClientError,
)
from .const import DOMAIN, LOGGER, DEFAULT_SCAN_INTERVAL

SIMPLE_OPTIONS_SCHEMA = vol.Schema(
    {
        vol.Optional(
            CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(
                mode=selector.NumberSelectorMode.BOX,
                unit_of_measurement="minutes",
            ),
        ),
    }
)

OPTIONS_FLOW = {
    "init": SchemaFlowFormStep(next_step="simple_options"),
    "simple_options": SchemaFlowFormStep(SIMPLE_OPTIONS_SCHEMA),
}

class ZeroIntegrationConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Configuration flow implementation."""

    VERSION = 1  # configuration flow version, if more info is needed change one up

    async def async_step_user(
        self,
        user_input: dict | None = None,
    ) -> config_entries.FlowResult:
        """Handle a flow initialized by the user."""
        client: ZeroApiClient | None = None
        units = []
        _errors = {}
        if user_input is not None:
            try:
                units, client = await self.attempt_access(
                    username=user_input[CONF_USERNAME],
                    password=user_input[CONF_PASSWORD],
                )
            except ZeroApiClientAuthenticationError as exception:
                LOGGER.warning(exception)
                _errors["base"] = "auth"
            except ZeroApiClientCommunicationError as exception:
                LOGGER.error(exception)
                _errors["base"] = "connection"
            except ZeroApiClientError as exception:
                LOGGER.exception(exception)
                _errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title="Zero Motorcycles",
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_USERNAME,
                        default=(user_input or {}).get(CONF_USERNAME),
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.TEXT
                        ),
                    ),
                    vol.Required(CONF_PASSWORD): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.PASSWORD
                        ),
                    ),
                }
            ),
            errors=_errors,
        )

    async def attempt_access(self, username: str, password: str) -> None:
        """Validate credentials & get tracked units."""
        client = ZeroApiClient(
            username=username,
            password=password,
            session=async_create_clientsession(self.hass),
        )
        return await client.async_get_units(), client  # this only requires username and password and retrieves unit numbers

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> SchemaOptionsFlowHandler:
        """Get options flow for this handler."""
        return SchemaOptionsFlowHandler(config_entry, OPTIONS_FLOW)