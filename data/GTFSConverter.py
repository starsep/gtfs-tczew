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
Time = str  # HH:MM:SS


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
    tripId: TripId
    shape: List[LatLon]
    busStopIds: List[StopId]
    shapeId: ShapeId

    def busStopNames(self, stops: Dict[StopId, GTFSStop]):
        return [stops[busStopId].stopName for busStopId in self.busStopIds]


@dataclass
class GTFSTripWithService(GTFSTrip):
    serviceId: ServiceId


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
class GTFSStopTime:
    tripId: TripId
    arrivalTime: Time
    departureTime: Time
    stopId: StopId
    stopSequence: int


@dataclass
class GTFSData:
    stops: Dict[StopId, GTFSStop]
    routes: Dict[RouteId, GTFSRoute]
    trips: Dict[TripId, GTFSTrip]
    tripsWithService: List[GTFSTripWithService]
    shapes: List[GTFSShape]
    services: List[GTFSService]
    stopTimes: List[GTFSStopTime]


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

    @abstractmethod
    def tripsWithService(
        self, trips: Dict[TripId, GTFSTrip], services: List[GTFSService]
    ) -> List[GTFSTripWithService]:
        raise NotImplementedError

    @abstractmethod
    def stopTimes(self, trips: Dict[TripId, GTFSTrip]) -> List[GTFSStopTime]:
        raise NotImplementedError

    def data(self) -> GTFSData:
        stops = self.stops()
        routes = self.routes()
        trips = self.trips(stops=stops)
        shapes = self.shapes(trips=trips)
        services = self.services()
        return GTFSData(
            stops=stops,
            routes=routes,
            trips=trips,
            tripsWithService=self.tripsWithService(trips, services),
            shapes=shapes,
            services=services,
            stopTimes=self.stopTimes(trips),
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


def tripForEveryService(
    trips: Dict[TripId, GTFSTrip], services: List[GTFSService]
) -> List[GTFSTripWithService]:
    return [
        GTFSTripWithService(
            routeId=trip.routeId,
            tripId=f"{trip.tripId}-{service.serviceId}",
            shapeId=trip.shapeId,
            shape=trip.shape,
            busStopIds=trip.busStopIds,
            serviceId=service.serviceId,
        )
        for service in services
        for trip in trips.values()
    ]
