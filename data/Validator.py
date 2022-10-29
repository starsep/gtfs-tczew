from abc import ABC
from dataclasses import dataclass
from typing import List

from data.TransportData import LatLon

STOP_DISTANCE_WARNING_THRESHOLD = 100.0
STOP_DISTANCE_ERROR_THRESHOLD = 200.0


@dataclass
class ValidatedStop:
    stopId: str
    stopName: str
    stopLat: float
    stopLon: float


@dataclass
class ValidatedRoute:
    routeId: str
    routeName: str


@dataclass
class ValidatedTrip:
    routeId: str
    serviceId: str
    tripId: str
    shape: List[LatLon]
    busStopIds: List[str]


class Validator(ABC):
    pass
