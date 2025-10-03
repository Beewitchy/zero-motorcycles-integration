"""DataUpdateCoordinator for zero_motorcycles_integration."""
from __future__ import annotations

from datetime import datetime, timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_SCAN_INTERVAL, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .binary_sensor import parse_state_as_bool

from .api import (
    TrackingUnit,
    TrackingUnitState,
    ZeroApiClient,
    ZeroApiClientAuthenticationError,
    ZeroApiClientError,
)
from .const import DEFAULT_SCAN_INTERVAL, LOGGER, CONF_RAPID_SCAN_INTERVAL, DEFAULT_RAPID_SCAN_INTERVAL


class UnitScanState:
    """Thingy."""

    enable_rapid_scan: bool = False
    rapid_scan_auto_enabled: bool = False
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

    def __init__(
        self,
        hass: HomeAssistant,
        configEntry: ConfigEntry
    ) -> None:
        """Initialize."""
        self.configEntry = configEntry

        # check options https://developers.home-assistant.io/docs/config_entries_options_flow_handler
        self.scan_interval = self.configEntry.options.get(
            CONF_SCAN_INTERVAL,
            DEFAULT_SCAN_INTERVAL,
        )

        self.rapid_scan_interval = self.configEntry.options.get(
            CONF_RAPID_SCAN_INTERVAL,
            DEFAULT_RAPID_SCAN_INTERVAL,
        )

        super().__init__(
            hass=hass,
            logger=LOGGER,
            name=configEntry.title,
            update_interval=self.rapid_scan_interval,
        )

    def is_rapid_scan_enabled(self, unit: TrackingUnitState) -> bool:
        """Do thing."""

        scan_state = self.units_scan_state.get(unit.get('unitnumber', ""))
        return scan_state.enable_rapid_scan if scan_state else False

    def enable_rapid_scan(self, unit: TrackingUnitState, value: bool):
        """Do thing."""

        scan_state = self.units_scan_state.get(unit.get('unitnumber', ""))
        if scan_state:
            scan_state.enable_rapid_scan = value

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
            if len(self.units) == 0 or (timeNow - self.units_last_updated_time) > self.refresh_units_interval:
                self.units_last_updated_time = timeNow
                try:
                    self.units = await self.client.async_get_units()
                except ZeroApiClientAuthenticationError as exception:
                    raise ConfigEntryAuthFailed(exception) from exception
                except ZeroApiClientError as exception:
                    raise UpdateFailed(exception) from exception

                LOGGER.debug("received units from API %s", self.units)

            for unit in self.units:
                unitnumber = unit["unitnumber"]
                rapid = self.units_scan_state[unitnumber].enable_rapid_scan or self.units_scan_state[unitnumber].rapid_scan_auto_enabled
                interval = self.rapid_scan_interval if rapid else self.scan_interval
                last_updated = self.units_scan_state[unitnumber].data_last_updated_time
                if (timeNow - last_updated) > interval:
                    self.units_scan_state[unitnumber].data_last_updated_time = timeNow
                    try:
                        fetchedData[unitnumber] = await self.client.async_get_last_transmit(unitnumber)
                        ignition = parse_state_as_bool(fetchedData[unitnumber].get('ignition', False))
                        charging = parse_state_as_bool(fetchedData[unitnumber].get('charging', False))
                        self.units_scan_state[unitnumber].rapid_scan_auto_enabled = (ignition if ignition else False) or (charging if charging else False)
                    except ZeroApiClientAuthenticationError as exception:
                        raise ConfigEntryAuthFailed(exception) from exception
                    except ZeroApiClientError as exception:
                        raise UpdateFailed(exception) from exception

        else:
            raise UpdateFailed("Remote api client isn't available, unknown error")

        return fetchedData
