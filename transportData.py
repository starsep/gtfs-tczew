from dataclasses import dataclass
from pathlib import Path
from typing import List

import geojson
from geojson import Feature, FeatureCollection, Point

from api import TczewBusesAPI

output = Path("output")
output.mkdir(exist_ok=True)


@dataclass
class BusStop:
    id: str
    name: str
    latitude: float
    longitude: float


@dataclass
class RouteVariant:
    id: int
    # ?: int
    # ?: int
    direction: str
    firstStopName: str
    lastStopName: str
    busStopsIds: List[int]


@dataclass
class Route:
    id: int
    name: str
    variants: List[RouteVariant]


@dataclass
class Timetable:
    id: int
    date: str
    future: bool  # ?


class TransportData(object):
    def __init__(self) -> None:
        super().__init__()
        self.tczewBusesApi = TczewBusesAPI()

    def getBusStops(self, timetableId: int = 0) -> List[BusStop]:
        stops = []
        for stop in self.tczewBusesApi.getMapBusStops(timetableId=timetableId):
            stops.append(
                BusStop(id=stop[0], name=stop[1], latitude=stop[5], longitude=stop[4])
            )
        return stops

    def getRoutes(self, timetableId: int = 0) -> List[Route]:
        routes = self.tczewBusesApi.getRouteList(timetableId=timetableId)
        result = []
        for i in range(len(routes) // 2):
            routeId = routes[2 * i]
            result.append(
                Route(
                    id=routeId,
                    name=routes[2 * i + 1],
                    variants=self.getRouteVariants(
                        routeId=routeId, timetableId=timetableId
                    ),
                )
            )
        return result

    def getTimetableInformation(self) -> List[Timetable]:
        return [
            Timetable(id=timetable[0], date=timetable[1], future=timetable[2])
            for timetable in self.tczewBusesApi.getTimetableInformation()
        ]

    def getRouteVariants(
        self, routeId: int, timetableId: int = 0, transits: int = 0
    ) -> List[RouteVariant]:
        tracks = self.tczewBusesApi.getTracks(
            routeId=routeId, timetableId=timetableId, transits=transits
        )
        stops = tracks[0]
        mapping = tracks[1]
        variants = [
            RouteVariant(
                id=variant[0],
                direction=variant[3],
                firstStopName=variant[4],
                lastStopName=variant[5],
                busStopsIds=[
                    stops[routeBusStopId][0] for routeBusStopId in variant[6][0]
                ],
            )
            for variant in tracks[2]
        ]
        return variants

    def saveBusStopsGeoJSON(self):
        stops = self.getBusStops()
        features = []
        for stop in stops:
            features.append(
                Feature(
                    geometry=Point((stop.longitude, stop.latitude)),
                    properties=dict(ref=stop.id, name=stop.name),
                )
            )
        with (output / "stops.geojson").open("w") as f:
            geojson.dump(FeatureCollection(features=features), f)
