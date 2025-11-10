"""DataUpdateCoordinator for zero_motorcycles_integration."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_SCAN_INTERVAL, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers import config_validation as cv
from homeassistant.util import dt as dt_util

from .api import (
    TrackingUnit,
    TrackingUnitState,
    ZeroApiClient,
    ZeroApiClientAuthenticationError,
    ZeroApiClientError,
)
from .const import LOGGER, CONF_RAPID_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL, DEFAULT_RAPID_SCAN_INTERVAL


OPTIONS_VALIDATOR_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): cv.positive_time_period,
        vol.Optional(CONF_RAPID_SCAN_INTERVAL, default=DEFAULT_RAPID_SCAN_INTERVAL): cv.positive_time_period,
    }
)


def parse_state_as_bool(state: bool | int | float | str) -> bool | None:
    """Interpret one of the many values the api provides for toggle states as a bool."""
    if isinstance(state, bool):
        return state
    elif isinstance(state, str):
        return state.lower() in {"true", "on", "1"}
    elif state is not None:
        return bool(state)
    return None


def parse_state_as_bool_or(state: bool | int | float | str, default: bool = False) -> bool:
    """Interpret one of the many values the api provides for toggle states as a bool."""
    value = parse_state_as_bool(state)
    return value if value else default


def parse_state_as_date(state: datetime | str | Any | None) -> datetime | None:
    """Interpret a datetime value in the format the api uses."""

    value: datetime | None = None
    if isinstance(state, str):
        return datetime.strptime(state, '%Y%m%d%H%M%S')
    elif isinstance(state, datetime):
        value = state

    if isinstance(value, datetime) and value.tzinfo is None:
        value = value.replace(tzinfo=dt_util.UTC)

    return value


class UnitScanState:
    """Thingy."""

    enable_rapid_scan: bool = False
    rapid_scan_auto_enabled: bool = False
    update_now: bool = True
    data_last_updated_time: datetime = datetime.min


# https://developers.home-assistant.io/docs/integration_fetching_data#coordinated-single-api-poll-for-data-for-all-entities
class ZeroCoordinator(DataUpdateCoordinator[dict[str, TrackingUnitState] | None]):
    """Class to manage fetching data from API."""

    entry: ConfigEntry | None = None
    client: ZeroApiClient | None = None
    units: list[TrackingUnit] = []
    units_last_updated_time: datetime = datetime.min
    refresh_units_interval = timedelta(hours=12)
    units_scan_state: dict[str, UnitScanState] = {}
    scan_interval: timedelta = DEFAULT_SCAN_INTERVAL
    rapid_scan_interval: timedelta = DEFAULT_RAPID_SCAN_INTERVAL

    data_timestamp: datetime | None = None

    def __init__(
        self,
        hass: HomeAssistant,
        configEntry: ConfigEntry
    ) -> None:
        """Initialize."""
        self.configEntry = configEntry

        options = OPTIONS_VALIDATOR_SCHEMA(dict(configEntry.options))
        self.scan_interval = options.get(
            CONF_SCAN_INTERVAL,
            DEFAULT_SCAN_INTERVAL,
        )
        self.rapid_scan_interval = options.get(
            CONF_RAPID_SCAN_INTERVAL,
            DEFAULT_RAPID_SCAN_INTERVAL,
        )

        LOGGER.debug("set scan interval to %s, rapid %s", self.scan_interval, self.rapid_scan_interval)

        super().__init__(
            hass=hass,
            logger=LOGGER,
            name=configEntry.title,
            update_interval=self.rapid_scan_interval,
        )

    def is_rapid_scan_enabled(self, unit: TrackingUnit) -> bool:
        """Do thing."""

        scan_state = self.units_scan_state.get(unit.get('unitnumber', ""))
        return scan_state.enable_rapid_scan if scan_state else False

    def is_rapid_scan_auto_enabled(self, unit: TrackingUnit) -> bool:
        """Do thing."""

        scan_state = self.units_scan_state.get(unit.get('unitnumber', ""))
        return scan_state.rapid_scan_auto_enabled if scan_state else False

    def enable_rapid_scan(self, unit: TrackingUnit, value: bool):
        """Do thing."""

        scan_state = self.units_scan_state.get(unit.get('unitnumber', ""))
        if scan_state:
            scan_state.enable_rapid_scan = value
            LOGGER.debug("rapid scan is now %s for %s", value, unit)
            self.update_interval = self.rapid_scan_interval
        else:
            LOGGER.warning("failed to enable rapid scan: %s is unknown", unit)
        # return self.async_request_refresh()

    def apply_scan_interval(self):
        """Do thing."""

        new_interval = self.rapid_scan_interval if any((scan_state.enable_rapid_scan or scan_state.rapid_scan_auto_enabled) for scan_state in self.units_scan_state.values()) else self.scan_interval
        if new_interval != self.update_interval:
            LOGGER.debug("new update interval is %s", new_interval)
        self.update_interval = new_interval

    async def _async_update_data(self) -> dict[str, TrackingUnitState]:
        """Update data using API."""

        fetchedData: dict[str, TrackingUnitState] = {}

        if not self.client:
            # Retrieve the stored credentials from config-flow
            username = self.configEntry.data.get(CONF_USERNAME)
            LOGGER.debug("Loaded %s: %s", CONF_USERNAME, username)
            password = self.configEntry.data.get(CONF_PASSWORD)
            LOGGER.debug("Loadded %s: ********", CONF_PASSWORD)

            self.client = ZeroApiClient(
                username=username,
                password=password,
                session=async_get_clientsession(self.hass),
            ) if username and password else None

        if self.client:
            timeNow = datetime.now()
            if len(self.units) == 0 or (timeNow - self.units_last_updated_time) >= self.refresh_units_interval:
                self.units_last_updated_time = timeNow
                try:
                    self.units = await self.client.async_get_units()
                except ZeroApiClientAuthenticationError as exception:
                    raise ConfigEntryAuthFailed(exception) from exception
                except ZeroApiClientError as exception:
                    raise UpdateFailed(exception) from exception

                LOGGER.debug("received units from API %s", self.units)

                updated_scan_state: dict[str, UnitScanState] = {}
                for unit in self.units:
                    unitnumber = unit['unitnumber']
                    updated_scan_state[unitnumber] = self.units_scan_state.get(unitnumber, UnitScanState())
                self.units_scan_state = updated_scan_state

            for unit in self.units:
                unitnumber = unit["unitnumber"]
                scan_state = self.units_scan_state.get(
                    unitnumber,
                    UnitScanState()
                )
                LOGGER.debug("fetching data for %s", unitnumber)
                scan_state.data_last_updated_time = timeNow
                scan_state.update_now = False
                try:
                    fetchedData[unitnumber] = await self.client.async_get_last_transmit(unitnumber)
                    ignition = parse_state_as_bool(fetchedData[unitnumber].get('ignition', False))
                    charging = parse_state_as_bool(fetchedData[unitnumber].get('charging', False))
                    scan_state.rapid_scan_auto_enabled = (ignition if ignition else False) or (charging if charging else False)
                except ZeroApiClientAuthenticationError as exception:
                    raise ConfigEntryAuthFailed(exception) from exception
                except ZeroApiClientError as exception:
                    raise UpdateFailed(exception) from exception

                self.apply_scan_interval()

        else:
            raise UpdateFailed("Remote api client isn't available, unknown error")

        return fetchedData
