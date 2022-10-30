from abc import abstractmethod, ABC
from dataclasses import dataclass
from typing import List, Dict, Tuple


@dataclass(eq=True)
class LatLon:
    latitude: float
    longitude: float


@dataclass
class BusStop(LatLon):
    id: str
    name: str


@dataclass
class RouteVariant:
    id: int
    direction: str
    firstStopName: str
    lastStopName: str
    busStopsIds: List[int]
    geometry: List[LatLon]


@dataclass
class Route:
    id: int
    name: str
    variants: List[RouteVariant]


@dataclass
class Timetable:
    id: int
    date: str


@dataclass
class StopTime:
    minutes: int
    routeVariantId: str
    tripId: str


@dataclass
class StopTimes:
    stopId: int
    routeId: int
    dayTypeToTimes: Dict[str, List[StopTime]]


class TransportData(ABC):
    @abstractmethod
    def getBusStops(self, timetableId: int = 0) -> Dict[int, BusStop]:
        raise NotImplementedError

    @abstractmethod
    def getRoutes(self, timetableId: int = 0) -> List[Route]:
        raise NotImplementedError

    @abstractmethod
    def getTimetableInformation(self) -> List[Timetable]:
        raise NotImplementedError

    @abstractmethod
    def getRouteVariants(
        self, routeId: int, timetableId: int = 0, transits: int = 1
    ) -> List[RouteVariant]:
        raise NotImplementedError

    @abstractmethod
    def stopTimes(
        self, busStopIdRouteIds: List[Tuple[int, int]], timetableId: int = 0
    ) -> List[StopTimes]:
        raise NotImplementedError
