"""Support for tracking devices."""
from __future__ import annotations

from typing import Any

from homeassistant.components.device_tracker.const import SourceType
from homeassistant.components.device_tracker.config_entry import TrackerEntity

from .const import DOMAIN, LOGGER, PROP_VIN, PROP_UNITNUMBER
from .coordinator import ZeroCoordinator
from .entity import ZeroEntity


async def async_setup_entry(hass, config_entry, async_add_entities):
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
        unit: Any,
    ) -> None:
        """Initialize the sensor class."""
        super().__init__(coordinator, unit)

        self._attr_unique_id = unit[PROP_VIN]
        LOGGER.debug("init tracker for %s", self.unitnumber)

    @property
    def battery_level(self) -> int | None:
        """Return battery level value of the device."""
        return self.coordinator.data[self.unitnumber]["soc"]

    @property
    def latitude(self) -> float | None:
        """Return latitude value of the device."""
        return self.coordinator.data[self.unitnumber]["latitude"]

    @property
    def longitude(self) -> float | None:
        """Return longitude value of the device."""
        return self.coordinator.data[self.unitnumber]["longitude"]

    @property
    def source_type(self):
        """Return the source type, eg gps or router, of the device."""
        return SourceType.GPS

    @property
    def icon(self):
        """Return the icon of the sensor."""
        if eval(self.coordinator.data[self.unitnumber]["gps_valid"]):
            return "mdi:motorbike-electric"
        else:
            return "mdi:motorbike-off"

    @property
    def extra_state_attributes(self):
        """Return the state attributes of the device."""
        heading = self.coordinator.data[self.unitnumber]["heading"]
        velocity = self.coordinator.data[self.unitnumber]["velocity"]
        altitude = self.coordinator.data[self.unitnumber]["altitude"]
        gps_connected = self.coordinator.data[self.unitnumber]["gps_connected"]
        gps_valid = self.coordinator.data[self.unitnumber]["gps_valid"]
        satellites = self.coordinator.data[self.unitnumber]["satellites"]
        name = self.coordinator.data[self.unitnumber][PROP_VIN]
        address = self.coordinator.data[self.unitnumber]["address"]
        return {
            "heading": heading,
            "vin": name,
            "velocity": velocity,
            "altitude": altitude,
            "gps_connected": gps_connected,
            "gps_valid": gps_valid,
            "satellites": satellites,
            "address": address,
        }
