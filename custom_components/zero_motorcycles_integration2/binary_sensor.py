"""Binary sensor platform for integration_blueprint."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, cast

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_platform

from .api import TrackingUnit, TrackingUnitStateKeys
from .const import DOMAIN, LOGGER
from .coordinator import ZeroCoordinator
from .entity import ZeroEntity


@dataclass(frozen=True)
class ZeroBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Senses."""

    off_icon: str | None = None
    attr_fn: Callable[[Any], dict[str, Any]] | None = None

    @property
    def data_key(self) -> TrackingUnitStateKeys:
        """Literalifies."""
        return cast(TrackingUnitStateKeys, self.key)

SENSORS = (
    ZeroBinarySensorEntityDescription(
        key="tipover",
        name="Tipped over",
        icon="mdi:alert",
        off_icon="mdi:emoticon-happy",
        device_class=BinarySensorDeviceClass.PROBLEM,
    ),
    ZeroBinarySensorEntityDescription(
        key="gps_valid",
        name="GPS accurate",
        icon="mdi:map-marker-alert",
        off_icon="mdi:map-marker",
        device_class=BinarySensorDeviceClass.PROBLEM,
    ),
    ZeroBinarySensorEntityDescription(
        key="gps_connected",
        name="GPS connected",
        icon="mdi:signal",
        off_icon="mdi:signal-off",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
    ),
    ZeroBinarySensorEntityDescription(
        key="charging",
        name="Charging",
        icon="mdi:battery-charging",
        off_icon="mdi:battery",
        device_class=BinarySensorDeviceClass.BATTERY_CHARGING,
    ),
    ZeroBinarySensorEntityDescription(
        key="chargecomplete",
        name="Charging complete",
        icon="mdi:battery-check",
        off_icon="mdi:battery-outline",
    ),
    ZeroBinarySensorEntityDescription(
        key="pluggedin",
        name="Plugged in",
        icon="mdi:power-plug",
        off_icon="mdi:power-plug-off",
        device_class=BinarySensorDeviceClass.PLUG,
    ),
    ZeroBinarySensorEntityDescription(
        key="storage",
        name="Storage mode",
        icon="mdi:sleep",
        off_icon="mdi:sleep-off",
    ),
    ZeroBinarySensorEntityDescription(
        key="ignition",
        name="Ignition",
        icon="mdi:toggle-switch-variant",
        off_icon="mdi:toggle-switch-variant-off",
        device_class=BinarySensorDeviceClass.RUNNING,
    ),
    ZeroBinarySensorEntityDescription(
        key="lock",
        name="Steering unlocked",
        icon="mdi:lock-open",
        off_icon="mdi:lock",
        device_class=BinarySensorDeviceClass.LOCK,
    ),
)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: entity_platform.AddEntitiesCallback):
    """Set up the binary_sensor platform."""

    coordinator: ZeroCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        [
            ZeroBinarySensor(
                coordinator,
                entity_description,
                unit=unitInfo
            )
            for unitInfo in coordinator.units
            for entity_description in SENSORS
        ],
        True
    )


class ZeroBinarySensor(ZeroEntity, BinarySensorEntity):
    """integration_blueprint binary_sensor class."""

    def __init__(
        self,
        coordinator: ZeroCoordinator,
        entity_description: ZeroBinarySensorEntityDescription,
        unit: TrackingUnit,
    ) -> None:
        """Initialize the binary_sensor class."""
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

        if isinstance(state, str):
            state = state.lower() in {"true", "on", "1"}
        elif state is not None:
            state = bool(state)
        else:
            LOGGER.warning(
                "Invalid sensor value for %s: %s",
                self.unique_id,
                state,
            )
            state = None

        self._attr_is_on = state

        if self.entity_description.off_icon:
            self._attr_icon = self.entity_description.icon if self._attr_is_on else self.entity_description.off_icon

        super()._handle_coordinator_update()
