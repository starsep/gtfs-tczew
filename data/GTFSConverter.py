from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict

from geojson import Point

from data.TransportData import LatLon

StopId = str
RouteId = str
TripId = str
ShapeId = str
ServiceId = str
GTFSDate = str  # YYYYMMDD


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
    serviceId: ServiceId
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
class GTFSService:
    serviceId: ServiceId
    monday: bool
    tuesday: bool
    wednesday: bool
    thursday: bool
    friday: bool
    saturday: bool
    sunday: bool
    startDate: GTFSDate
    endDate: GTFSDate


@dataclass
class GTFSData:
    stops: Dict[StopId, GTFSStop]
    routes: Dict[RouteId, GTFSRoute]
    trips: Dict[TripId, GTFSTrip]
    shapes: List[GTFSShape]
    services: List[GTFSService]


class GTFSConverter(ABC):
    @abstractmethod
    def stops(self) -> Dict[StopId, GTFSStop]:
        raise NotImplementedError

    @abstractmethod
    def routes(self) -> Dict[RouteId, GTFSRoute]:
        raise NotImplementedError

    @abstractmethod
    def trips(self, stops: Dict[StopId, GTFSStop]) -> Dict[TripId, GTFSTrip]:
        raise NotImplementedError

    @abstractmethod
    def shapes(self, trips: Dict[TripId, GTFSTrip]) -> List[GTFSShape]:
        raise NotImplementedError

    @abstractmethod
    def services(self) -> List[GTFSService]:
        raise NotImplementedError

    def data(self) -> GTFSData:
        stops = self.stops()
        routes = self.routes()
        trips = self.trips(stops=stops)
        shapes = self.shapes(trips=trips)
        return GTFSData(
            stops=stops,
            routes=routes,
            trips=trips,
            shapes=shapes,
            services=self.services(),
        )


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
