from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict

from geojson import Point

from data.TransportData import LatLon

StopId = str
RouteId = str
TripId = str
ShapeId = str


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
    shapeId: ShapeId

    def busStopNames(self, stops: Dict[StopId, GTFSStop]):
        return [stops[busStopId].stopName for busStopId in self.busStopIds]


@dataclass
class GTFSShape:
    shapeId: ShapeId
    shapeLat: float
    shapeLon: float
    shapeSequence: int


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

    @abstractmethod
    def shapes(self) -> List[GTFSShape]:
        raise NotImplementedError


def shapesFromTrips(trips: Dict[TripId, GTFSTrip]) -> List[GTFSShape]:
    return [
        GTFSShape(
            shapeId=trip.shapeId,
            shapeLat=point.latitude,
            shapeLon=point.longitude,
            shapeSequence=pointIndex,
        )
        for trip in trips.values()
        for pointIndex, point in enumerate(trip.shape)
    ]