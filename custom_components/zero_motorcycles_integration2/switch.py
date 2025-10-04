"""Switch for ZeroMotorcycles."""

from collections.abc import Callable
from dataclasses import dataclass
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN
from .api import TrackingUnit, TrackingUnitState
from .coordinator import ZeroCoordinator
from .entity import ZeroEntity


PARALLEL_UPDATES = 1

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class ZeroSwitchEntityDescription(SwitchEntityDescription):
    """Describes a switch entity."""

    value_fn: Callable[[ZeroCoordinator, TrackingUnit], bool]
    set_fn: Callable[[ZeroCoordinator, TrackingUnit, bool], None]
    is_available: Callable[[ZeroCoordinator, TrackingUnit], bool] = lambda _, _1: True


SWITCHES = list({
    ZeroSwitchEntityDescription(
        key="rapid_scan",
        name="Active Scan",
        value_fn=lambda co, unit: co.is_rapid_scan_enabled(unit),
        set_fn=lambda co, unit, value: co.enable_rapid_scan(unit, value),
    )
})


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up switches."""

    coordinator: ZeroCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    async_add_entities(
        [
            ZeroSwitch(
                coordinator,
                entity_description,
                unit=unitInfo
            )
            for unitInfo in coordinator.units
            for entity_description in SWITCHES
        ],
        True
    )


class ZeroSwitch(ZeroEntity, SwitchEntity):
    """Representation of a switch."""

    unit_state: TrackingUnitState | None = None

    def __init__(
        self,
        coordinator: ZeroCoordinator,
        entity_description: ZeroSwitchEntityDescription,
        unit: TrackingUnit,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator, unit)
        self.entity_description = entity_description
        self._attr_unique_id = f"{self.vin}-{entity_description.key}"

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        if self.unit:
            self.entity_description.set_fn(self.coordinator, self.unit, True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        if self.unit:
            self.entity_description.set_fn(self.coordinator, self.unit, False)
        await self.coordinator.async_request_refresh()

    @property
    def is_on(self) -> bool:
        """Return the state of the switch."""

        return self.entity_description.value_fn(self.coordinator, self.unit) if self.unit else False

