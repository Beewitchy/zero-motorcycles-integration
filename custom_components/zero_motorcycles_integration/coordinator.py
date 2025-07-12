"""DataUpdateCoordinator for zero_motorcycles_integration."""
from __future__ import annotations

from datetime import timedelta
import json
import os
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, CONF_SCAN_INTERVAL
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import (
    ZeroApiClient,
    ZeroApiClientAuthenticationError,
    ZeroApiClientError,
)
from .const import DOMAIN, LOGGER, DEFAULT_SCAN_INTERVAL

SCAN_INTERVAL = DEFAULT_SCAN_INTERVAL

# https://developers.home-assistant.io/docs/integration_fetching_data#coordinated-single-api-poll-for-data-for-all-entities
class ZeroCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from API."""

    configEntry: ConfigEntry
    info: Any
    client: ZeroApiClient
    units = {}  # all units fetched

    def __init__(
        self,
        hass: HomeAssistant,
        configEntry: ConfigEntry
    ) -> None:
        """Initialize."""
        self.configEntry = configEntry

        # get data from manifest here instead, is this the way to go?
        # mostly done so we wouldn't have to change version in several places
        self.info = json.load(
            open("{}/{}".format(os.path.dirname(os.path.realpath(__file__)), "manifest.json"))
        )
        LOGGER.debug("loaded info %s", self.info)

        # TODO maybe keep track of vehicles instead of mapping data
        # self.vehicles = None
        self.data = {}

        # check options https://developers.home-assistant.io/docs/config_entries_options_flow_handler
        scan_interval = timedelta(
           seconds=self.configEntry.options.get(
               CONF_SCAN_INTERVAL,
               SCAN_INTERVAL.minutes,
           )
        )

        super().__init__(
            hass=hass,
            logger=LOGGER,
            name=configEntry.title,
            update_interval=scan_interval,
        )

    async def _async_update_data(self):
        """Update data using API."""
        try:
            if self.client is None:
                # Retrieve the stored credentials from config-flow
                username = self.configEntry.data.get(CONF_USERNAME)
                LOGGER.debug("Loaded %s: %s", CONF_USERNAME, username)
                password = self.configEntry.data.get(CONF_PASSWORD)
                LOGGER.debug("Loadded %s: ********", CONF_PASSWORD)

                self.client = ZeroApiClient(
                    username=username,
                    password=password,
                    session=async_get_clientsession(self.hass),
                ),

            # start by getting all units with given login
            self.units = await self.client.async_get_units()

            # also get last transmit at this point
            LOGGER.debug("received units from API %s", self.units)

            # for all units get last transmit data
            data = {}
            for unit in self.units:
                unitnumber = unit["unitnumber"]
                # create quick access dict here
                data[unitnumber] = await self.client.async_get_last_transmit(unitnumber)
                # LOGGER.debug(
                #    "received data for unit %s from API %s",
                #    unitnumber,
                #    data[unitnumber],
                # )

            return data

        except ZeroApiClientAuthenticationError as exception:
            raise ConfigEntryAuthFailed(exception) from exception
        except ZeroApiClientError as exception:
            raise UpdateFailed(exception) from exception
