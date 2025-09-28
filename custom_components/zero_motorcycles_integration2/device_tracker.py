"""Support for tracking devices."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from propcache.api import cached_property

from homeassistant.components.device_tracker.config_entry import TrackerEntity
from homeassistant.components.device_tracker.const import SourceType
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_platform

from .api import PROP_VIN, TrackingUnit
from .const import DOMAIN, LOGGER
from .coordinator import ZeroCoordinator
from .entity import ZeroEntity
from .binary_sensor import parse_state_as_bool


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: entity_platform.AddEntitiesCallback):
    """Set up device tracket by config_entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]

    async_add_entities(
        [
            ZeroTrackerEntity(
                coordinator=coordinator,
                unit=unit,
            )
            for unit in coordinator.units
        ],
        True
    )

class ZeroTrackerEntity(ZeroEntity, TrackerEntity):
    """A class representing a trackable device."""

    _attr_force_update = False
    _attr_name = None

    def __init__(
        self,
        coordinator: ZeroCoordinator,
        unit: TrackingUnit,
    ) -> None:
        """Initialize the sensor class."""
        super().__init__(coordinator, unit)

        self._attr_unique_id = unit[PROP_VIN]
        LOGGER.debug("init tracker for %s", self.unitnumber)

    @cached_property
    def battery_level(self) -> int | None:
        """Return battery level value of the device."""
        return self.coordinator.data.get(self.unitnumber, {}).get("soc") if self.coordinator.data else None

    @cached_property
    def latitude(self) -> float | None:
        """Return latitude value of the device."""
        return self.coordinator.data.get(self.unitnumber, {}).get("latitude") if self.coordinator.data else None

    @cached_property
    def longitude(self) -> float | None:
        """Return longitude value of the device."""
        return self.coordinator.data.get(self.unitnumber, {}).get("longitude") if self.coordinator.data else None

    @property
    def source_type(self):
        """Return the source type, eg gps or router, of the device."""
        return SourceType.GPS

    @cached_property
    def icon(self):
        """Return the icon of the sensor."""
        gpsValid = self.coordinator.data.get(self.unitnumber, {}).get("gps_valid") if self.coordinator.data else None
        if gpsValid and parse_state_as_bool(gpsValid):
            return "mdi:motorbike-electric"
        return "mdi:motorbike-off"

    @cached_property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        """Return the state attributes of the device."""
        unit = self.coordinator.data.get(self.unitnumber, {}) if self.coordinator.data else None
        if not unit:
            return None

        return {
            key: value
            for key, value in unit.items()
            if key in {
                "heading",
                "velocity",
                "altitude",
                "gps_connected",
                "gps_valid",
                "satellites",
                "address"
            }
        }
