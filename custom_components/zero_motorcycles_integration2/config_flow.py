"""Adds config flow."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.const import CONF_PASSWORD, CONF_SCAN_INTERVAL, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)
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
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN, LOGGER, DEFAULT_RAPID_SCAN_INTERVAL, CONF_RAPID_SCAN_INTERVAL

SIMPLE_OPTIONS_SCHEMA = vol.Schema(
    {
        vol.Optional(
            CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL
        ): vol.All(cv.time_period, cv.positive_time_period),
        vol.Optional(
            CONF_RAPID_SCAN_INTERVAL, default=DEFAULT_RAPID_SCAN_INTERVAL
        ): vol.All(cv.time_period, cv.positive_time_period),
    }
)

OPTIONS_FLOW = {
    "init": SchemaFlowFormStep(SIMPLE_OPTIONS_SCHEMA),
}


class ZeroIntegrationConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Configuration flow implementation."""

    VERSION = 1  # configuration flow version, if more info is needed change one up

    async def async_step_user(
        self,
        user_input: dict | None = None,
    ) -> ConfigFlowResult:
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
                        CONF_USERNAME
                    ): TextSelector(
                        TextSelectorConfig(
                            type=TextSelectorType.TEXT
                        ),
                    ),
                    vol.Required(
                        CONF_PASSWORD
                    ): TextSelector(
                        TextSelectorConfig(
                            type=TextSelectorType.PASSWORD
                        ),
                    ),
                }
            ),
            errors=_errors,
        )

    async def attempt_access(self, username: str, password: str) -> tuple[Any, ZeroApiClient]:
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
