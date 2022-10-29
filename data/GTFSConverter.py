from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict

from geojson import Point

from data.TransportData import LatLon

StopId = str
RouteId = str
TripId = str


@dataclass
class GTFSStop:
    stopId: StopId
    stopName: str
    stopLat: float
    stopLon: float

    def toPoint(self):
        return Point((self.stopLon, self.stopLat))


@dataclass
class GTFSRoute:
    routeId: RouteId
    routeName: str


@dataclass
class GTFSTrip:
    routeId: RouteId
    serviceId: str
    tripId: TripId
    shape: List[LatLon]
    busStopIds: List[StopId]

    def busStopNames(self, stops: Dict[StopId, GTFSStop]):
        return [stops[busStopId].stopName for busStopId in self.busStopIds]


@dataclass
class GTFSData:
    stops: List[GTFSStop]
    routes: List[GTFSRoute]


class GTFSConverter(ABC):
    @abstractmethod
    def stops(self) -> Dict[StopId, GTFSStop]:
        raise NotImplementedError

    @abstractmethod
    def routes(self) -> Dict[RouteId, GTFSRoute]:
        raise NotImplementedError

    @abstractmethod
    def trips(self) -> Dict[TripId, GTFSTrip]:
        raise NotImplementedError
