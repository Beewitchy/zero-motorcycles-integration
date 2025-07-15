"""ZeroEntity class."""
from __future__ import annotations

from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import PROP_VIN, TrackingUnit, TrackingUnitState
from .const import BRAND, BRAND_ATTRIBUTION, DOMAIN
from .coordinator import ZeroCoordinator


class ZeroEntity(CoordinatorEntity[ZeroCoordinator]):
    """Zero Entity class."""

    _attr_attribution = BRAND_ATTRIBUTION

    unit: TrackingUnit
    unitnumber: str

    def __init__(self, coordinator: ZeroCoordinator, unit: TrackingUnit) -> None:
        """Initialize."""
        super().__init__(coordinator)

        self.unit = unit
        # set unit number for unit reference here, this is used as a key in received data
        self.unitnumber = unit["unitnumber"]
        self.vin = unit[PROP_VIN]

        data: TrackingUnitState | None = (
            coordinator.data[self.unitnumber]
            if self.unitnumber and coordinator.data
            else None
        )

        softwareVersion = data.get("software_version", None) if data else None
        softwareVersion = str(softwareVersion) if softwareVersion else None

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self.vin)},
            name=self.unitnumber,
            model=self.unit.get("vehiclemodel", None),
            manufacturer=BRAND,
            sw_version=softwareVersion
        )
