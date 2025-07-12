"""Constants for zero_motorcycles_integration."""
from datetime import timedelta
from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

DOMAIN = "zero_motorcycles_integration2"
BRAND = "Zero Motorcycles"
BRAND_ATTRIBUTION = "Zero Motorcycles, Inc."

PROP_VIN = "name"
PROP_UNITNUMBER = "unitnumber"

DEFAULT_SCAN_INTERVAL = timedelta(minutes=30)
SCAN_INTERVAL_MINIMUM = timedelta(seconds=30)