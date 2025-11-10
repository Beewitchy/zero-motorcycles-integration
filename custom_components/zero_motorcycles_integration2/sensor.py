"""Sensor platform for zero_motorcycles_integration."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from operator import itemgetter
from typing import cast

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    DEGREE,
    PERCENTAGE,
    UnitOfElectricPotential,
    UnitOfLength,
    UnitOfSpeed,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_platform
from homeassistant.util import dt as dt_util

from .api import TrackingUnit, TrackingUnitStateKeys
from .const import DOMAIN, LOGGER
from .coordinator import ZeroCoordinator, parse_state_as_date
from .entity import ZeroEntity


@dataclass(frozen=True)
class ZeroSensorEntityDescription(SensorEntityDescription):
    """"Does what it says on the tin."""

    value_fn: Callable = lambda sv: sv
    # Mapping of (max value, icon)
    iconset: list[tuple[float, str]] | None = None

    def __post_init__(self):
        """Reverse-sort the icon set by the 'max value' attributes so the correct icon can be found by just searching through."""
        if self.iconset:
            self.iconset.sort(key=itemgetter(0), reverse=True)

    @property
    def data_key(self) -> TrackingUnitStateKeys:
        """Literalifies."""
        return cast(TrackingUnitStateKeys, self.key)

SENSORS = (
    ZeroSensorEntityDescription(
        key="soc",
        name="State of Charge",
        icon="mdi:battery-50",
        iconset=[(10, "mdi:battery-10"), (20, "mdi:battery-20"), (30, "mdi:battery-30"),(40, "mdi:battery-40"),(50, "mdi:battery-50"),(60, "mdi:battery-60"),(70, "mdi:battery-70"),(80, "mdi:battery-80"),(90, "mdi:battery-90"),(100, "mdi:battery")],
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
    ),
    ZeroSensorEntityDescription(
        key="mileage",
        name="Mileage",
        icon="mdi:gauge",
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
    ),
    ZeroSensorEntityDescription(
        key="datetime_actual",
        name="Last data received",
        icon="mdi:update",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda v: datetime.strptime(v, '%Y%m%d%H%M%S'),
    ),
    ZeroSensorEntityDescription(
        key="datetime_utc",
        name="Last GPS update",
        icon="mdi:map-marker-up",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda v: datetime.strptime(v, '%Y%m%d%H%M%S'),
    ),
    ZeroSensorEntityDescription(
        key="altitude",
        name="Altitude",
        icon="mdi:elevation-rise",
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfLength.METERS,
    ),
    ZeroSensorEntityDescription(
        key="satellites",
        name="Satalites",
        icon="mdi:satellite-variant",
        device_class=None,
        native_unit_of_measurement=None,
    ),
    ZeroSensorEntityDescription(
        key="velocity",
        name="Velocity",
        icon="mdi:gauge",
        device_class=SensorDeviceClass.SPEED,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfSpeed.KILOMETERS_PER_HOUR,
    ),
    ZeroSensorEntityDescription(
        key="heading",
        name="Heading",
        icon="mdi:compass",
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT_ANGLE,
        native_unit_of_measurement=DEGREE,
    ),
    ZeroSensorEntityDescription(
        key="main_voltage",
        name="Accessory battery voltage",
        icon="mdi:car-battery",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
    ),
    ZeroSensorEntityDescription(
        key="chargingtimeleft",
        name="Charging time remaining",
        icon="mdi:battery-clock",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.MINUTES,
    ),
    ZeroSensorEntityDescription(
        key="battery",
        name="Tracking module battery",
        icon="mdi:battery",
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
    ),
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: entity_platform.AddEntitiesCallback):
    """Set up the sensor platform."""

    coordinator: ZeroCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        [
            ZeroSensor(
                coordinator,
                entity_description,
                unit=unitInfo
            )
            for unitInfo in coordinator.units
            for entity_description in SENSORS
        ],
        True
    )

class ZeroSensor(ZeroEntity, SensorEntity):
    """zero_motorcycles_integration Sensor class."""

    def __init__(
        self,
        coordinator: ZeroCoordinator,
        entity_description: ZeroSensorEntityDescription,
        unit: TrackingUnit,
    ) -> None:
        """Initialize the sensor class."""
        super().__init__(coordinator, unit)

        self.entity_description = entity_description

        self._attr_unique_id = f"{self.vin}-{entity_description.key}"

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""

        state = self.coordinator.data.get(self.unitnumber, {}).get(self.entity_description.data_key) if self.coordinator.data else None
        LOGGER.debug(
            "Sensor value for %s is %s",
            self.unique_id,
            state,
        )

        if state is not None:
            state = self.entity_description.value_fn(state)

            if isinstance(state, datetime) and state.tzinfo is None:
                state = state.replace(tzinfo=dt_util.get_default_time_zone())
        else:
            LOGGER.warning(
                "Invalid sensor value for %s: %s",
                self.unique_id,
                state,
            )

        self._attr_native_value = state

        datetime_data = self.coordinator.data.get(self.unitnumber, {}).get("datetime_actual") if self.coordinator.data else None

        self._attr_extra_state_attributes = {
            "timestamp": parse_state_as_date(datetime_data)
        }

        if isinstance(state, int | float) and self.entity_description.iconset:
            for (maxValue, icon) in self.entity_description.iconset:
                if state < maxValue:
                    self._attr_icon = icon

        super()._handle_coordinator_update()
