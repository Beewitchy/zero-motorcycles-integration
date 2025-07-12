"""ZeroEntity class."""
from __future__ import annotations
from typing import Any

from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import LOGGER, DOMAIN, BRAND, BRAND_ATTRIBUTION, PROP_VIN, PROP_UNITNUMBER
from .coordinator import ZeroCoordinator


class ZeroEntity(CoordinatorEntity):
    """Zero Entity class."""

    _attr_attribution = BRAND_ATTRIBUTION

    unit: Any | None = None
    unitnumber: str | None = None

    def __init__(self, coordinator: ZeroCoordinator, unit: Any) -> None:
        """Initialize."""
        super().__init__(coordinator)

        self.unit = unit;
        # set unit number for unit reference here, this is used as a key in received data
        self.unitnumber = unit[PROP_UNITNUMBER]
        self.vin = unit[PROP_VIN]

        data = {}
        if self.unitnumber:
            data = coordinator.data[self.unitnumber]

        if not self.unit:
            LOGGER.warning("no vehicle unit number provided to entity")
        else:
            self._attr_device_info = DeviceInfo(
                identifiers={(DOMAIN, self.vin)},
                name=self.unitnumber,
                model=self.unit["vehiclemodel"],
                model_id=self.unit["unitmodel"],
                manufacturer=BRAND,
                sw_version=data["software_version"] or None
            )
