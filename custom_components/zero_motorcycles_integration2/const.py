"""Constants for zero_motorcycles_integration."""
from datetime import timedelta
from logging import Logger, getLogger
from typing import Final

LOGGER: Logger = getLogger(__package__)

DOMAIN: Final = "zero_motorcycles_integration2"
BRAND: Final = "Zero Motorcycles"
BRAND_ATTRIBUTION: Final = "Zero Motorcycles, Inc."

CONF_RAPID_SCAN_INTERVAL: Final = "rapid_scan_interval"

DEFAULT_SCAN_INTERVAL: Final = timedelta(minutes=30)
DEFAULT_RAPID_SCAN_INTERVAL: Final = timedelta(seconds=30)
