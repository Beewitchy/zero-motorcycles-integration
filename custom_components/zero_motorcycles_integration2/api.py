"""Mongol or starcom API used by Zero Motorcycles for sharing data.

For more details about this starcom API please refer to
https://bitbucket.org/cappelleh/zengo-android/src/master/
"""

from __future__ import annotations

import asyncio
from datetime import datetime
import socket
from typing import Any, Literal, Required, TypedDict

import aiohttp

PROP_VIN = "name" # the tracking unit property we expect to contain the VIN


class TrackingUnit(TypedDict, total=False):
    """Data returned when requesting units."""

    unitnumber: Required[str]
    name: Required[str]
    address: str
    vehiclemodel: str
    vehiclecolor: str
    unittype: str | int
    icon: str | int
    active: str | int | bool
    unitmodel: str | int
    regnumber: str
    platenumber: str | None
    custom: list[Any]

class TrackingUnitState(TypedDict, total=False):
    """Data returned when requesting update."""

    unitnumber: Required[str]
    name: str
    unittype: str | int
    unitmodel: str | int
    analog1: float
    analog2: float
    mileage: float | str
    software_version: str | datetime
    logic_state: int | str
    reason: int | str
    response: int | str
    driver: int | str
    longitude: float
    latitude: float
    altitude: float | str
    gps_valid: bool | int | str
    gps_connected: bool | int | str
    satellites: int | str
    velocity: float | str
    heading: float | str
    emergency: bool | int | str
    shock: bool | float | str
    ignition: bool | int | str
    door: bool | int | str
    hood: bool | int | str
    volume: float | str
    water_temp: float | str
    oil_pressure: float | str
    main_voltage: float
    fuel: float | str
    analog3: float
    siren: bool | float | str
    lock: bool | float | str
    int_lights: bool | float | str
    datetime_utc: datetime | str
    datetime_actual: datetime | str
    address: str
    perimeter: str
    color: int
    soc: int
    tipover: bool | int
    charging: bool | int
    chargecomplete: bool | int
    pluggedin: bool | int
    chargingtimeleft: int | float # measured in minutes
    storage: bool | int
    battery: float | int

TrackingUnitStateKeys = Literal[
    "unitnumber",
    "name",
    "unittype",
    "unitmodel",
    "analog1",
    "analog2",
    "mileage",
    "software_version",
    "logic_state",
    "reason",
    "response",
    "driver",
    "longitude",
    "latitude",
    "altitude",
    "gps_valid",
    "gps_connected",
    "satellites",
    "velocity",
    "heading",
    "emergency",
    "shock",
    "ignition",
    "door",
    "hood",
    "volume",
    "water_temp",
    "oil_pressure",
    "main_voltage",
    "fuel",
    "analog3",
    "siren",
    "lock",
    "int_lights",
    "datetime_utc",
    "datetime_actual",
    "address",
    "perimeter",
    "color",
    "soc",
    "tipover",
    "charging",
    "chargecomplete",
    "pluggedin",
    "chargingtimeleft",
    "storage",
    "battery",
]

class ZeroApiClientError(Exception):
    """Exception to indicate a general API error."""


class ZeroApiClientCommunicationError(ZeroApiClientError):
    """Exception to indicate a communication error."""


class ZeroApiClientAuthenticationError(ZeroApiClientError):
    """Exception to indicate an authentication error."""


class ZeroApiClient:
    """Starcom API used by Zero Motorcycles for sharing data."""

    def __init__(
        self,
        username: str,
        password: str,
        session: aiohttp.ClientSession,
    ) -> None:
        """Set user credentials for API."""
        self._username = username
        self._password = password
        self._session = session

    async def async_get_units(self) -> list[TrackingUnit]:
        """Get available unit numbers for given credentials from API."""
        return await self._api_wrapper(
            method="get",
            url="https://mongol.brono.com/mongol/api.php",
            params={
                "commandname": "get_units",
                "format": "json",
                "user": self._username,
                "pass": self._password
            }
        )

    async def async_get_last_transmit(self, unitnumber) -> TrackingUnitState:
        """Get available available data from API."""
        result = await self._api_wrapper(
            method="get",
            url="https://mongol.brono.com/mongol/api.php",
            params={
                "commandname": "get_last_transmit",
                "format": "json",
                "user": self._username,
                "pass": self._password,
                "unitnumber": unitnumber
            }
        )
        if not len(result) == 1:
            raise ZeroApiClientCommunicationError("Unexpected response value: {result}")

        return result[0] # only expecting the result for one unit

    async def _api_wrapper(
        self,
        method: str,
        url: str,
        params: dict | None = None,
        json: dict | None = None,
    ) -> Any:
        """Get information from the API."""
        try:
            async with asyncio.timeout(10):
                response = await self._session.request(
                    method=method,
                    url=url,
                    params=params,
                    json=json,
                )
            response.raise_for_status()
            return await response.json()

        except TimeoutError as exception:
            raise ZeroApiClientCommunicationError(
                "Timeout error fetching information",
            ) from exception
        except aiohttp.ClientResponseError as exception:
            if exception.status in (401, 403, 601):
                raise ZeroApiClientAuthenticationError(
                    "Invalid credentials",
                ) from exception

            raise ZeroApiClientCommunicationError(
                "Unexpected response",
            ) from exception
        except (aiohttp.ClientError, socket.gaierror) as exception:
            raise ZeroApiClientCommunicationError(
                "Couldn't make api request",
            ) from exception
        except Exception as exception:  # pylint: disable=broad-except
            raise ZeroApiClientError("Something really wrong happened!") from exception

