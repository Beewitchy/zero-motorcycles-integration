"""Switch for ZeroMotorcycles."""

from collections.abc import Callable, Coroutine
from dataclasses import dataclass
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from propcache.api import cached_property

from .const import DOMAIN
from .api import TrackingUnit, TrackingUnitState
from .coordinator import ZeroCoordinator, UnitScanState
from .entity import ZeroEntity
from .binary_sensor import parse_state_as_bool_or

PARALLEL_UPDATES = 1

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class ZeroSwitchEntityDescription(SwitchEntityDescription):
    """Describes a switch entity."""

    value_fn: Callable[[ZeroCoordinator, TrackingUnitState], bool]
    set_fn: Callable[[ZeroCoordinator, TrackingUnitState, bool]]
    is_available: Callable[[ZeroCoordinator, TrackingUnitState], bool] = lambda _,_1: True


SWITCHES = (
    ZeroSwitchEntityDescription(
        key="rapid_scan",
        value_fn=lambda co, unit: co.is_rapid_scan_enabled(unit),
        set_fn=lambda co, unit, value: co.enable_rapid_scan(unit, value),
    ),
    ZeroSwitchEntityDescription(
        key="super_alert",
        value_fn=lambda co, unit: False,
        set_fn=lambda co, unit, value: (),
    )
)


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

    @cached_property
    def is_on(self) -> bool | None:
        """Return the entity value to represent the entity state."""

        return self.entity_description.value_fn(self.coordinator, self.unit_state) if self.unit_state else None

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        if self.unit_state:
            self.entity_description.set_fn(self.coordinator, self.unit_state, True)
            self.coordinator.async_update_listeners()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        if self.unit_state:
            self.entity_description.set_fn(self.coordinator, self.unit_state, False)
            self.coordinator.async_update_listeners()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""

        self.unit_state = self.coordinator.data.get(self.unitnumber)