from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List

from geojson import Point

from data.TransportData import LatLon

StopId = str
RouteId = str
RouteVariantId = str
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
class GTFSRouteVariant:
    routeId: RouteId
    routeVariantId: RouteVariantId
    shape: List[LatLon]
    busStopIds: List[StopId]
    shapeId: ShapeId

    def busStopNames(self, stops: Dict[StopId, GTFSStop]):
        return [stops[busStopId].stopName for busStopId in self.busStopIds]


@dataclass
class GTFSTrip(GTFSRouteVariant):
    tripStartMinutes: int
    serviceId: ServiceId
    tripId: TripId


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
    routeVariants: Dict[RouteVariantId, GTFSRouteVariant]
    trips: Dict[TripId, GTFSTrip]
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
    def routeVariants(
        self, stops: Dict[StopId, GTFSStop]
    ) -> Dict[RouteVariantId, GTFSRouteVariant]:
        raise NotImplementedError

    @abstractmethod
    def trips(
        self,
        stops: Dict[StopId, GTFSStop],
        services: List[GTFSService],
        routeVariants: Dict[RouteVariantId, GTFSRouteVariant],
    ) -> Dict[TripId, GTFSTrip]:
        raise NotImplementedError

    @abstractmethod
    def shapes(
        self, routeVariants: Dict[RouteVariantId, GTFSRouteVariant]
    ) -> List[GTFSShape]:
        raise NotImplementedError

    @abstractmethod
    def services(self) -> List[GTFSService]:
        raise NotImplementedError

    @abstractmethod
    def stopTimes(
        self,
        routes: Dict[RouteId, GTFSRoute],
        routeVariants: Dict[RouteVariantId, GTFSRouteVariant],
        trips: Dict[TripId, GTFSTrip],
    ) -> List[GTFSStopTime]:
        raise NotImplementedError

    def data(self) -> GTFSData:
        stops = self.stops()
        routes = self.routes()
        routeVariants = self.routeVariants(stops=stops)
        services = self.services()
        trips = self.trips(stops=stops, services=services, routeVariants=routeVariants)
        shapes = self.shapes(routeVariants=routeVariants)
        return GTFSData(
            stops=stops,
            routes=routes,
            routeVariants=routeVariants,
            trips=trips,
            shapes=shapes,
            services=services,
            stopTimes=self.stopTimes(
                routes=routes, routeVariants=routeVariants, trips=trips
            ),
        )


def shapesFromRouteVariants(
    routeVariants: Dict[RouteVariantId, GTFSRouteVariant]
) -> List[GTFSShape]:
    return [
        GTFSShape(
            shapeId=routeVariant.shapeId,
            shapeLat=point.latitude,
            shapeLon=point.longitude,
            shapeSequence=pointIndex,
        )
        for routeVariant in routeVariants.values()
        for pointIndex, point in enumerate(routeVariant.shape)
    ]
