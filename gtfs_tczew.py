from dataclasses import dataclass
from pathlib import Path
from typing import List

import geojson
import httpx
from diskcache import Cache
from geojson import Feature, FeatureCollection, Point

cache = Cache("cache")
output = Path("output")
output.mkdir(exist_ok=True)
DOMAIN = "http://rozklady.tczew.pl"


@dataclass
class BusStop:
    id: str
    name: str
    latitude: float
    longitude: float


@dataclass
class Route:
    id: int
    name: str


@dataclass
class Timetable:
    id: int
    date: str
    future: bool  # ?


@dataclass
class RouteVariant:
    # ref: int
    # ?: int
    # ?: int
    variantName: str
    firstStopName: str
    lastStopName: str
    direction: str


class TczewBusesAPI:
    @cache.memoize()
    def getMapBusStops(self, timetableId: int):
        url = f"{DOMAIN}/Home/GetMapBusStopList?q=&ttId={timetableId}"
        return httpx.get(url).json()

    @cache.memoize()
    def getRouteList(self, timetableId: int):
        url = f"{DOMAIN}/Home/GetRouteList?ttId={timetableId}"
        return httpx.get(url).json()[0]

    @cache.memoize()
    def getTimetableInformation(self):
        url = f"{DOMAIN}/Home/GetTimetableInformation"
        return httpx.get(url).json()

    @cache.memoize()
    def getTracks(self, routeId: int, timetableId: int, transits: int):
        url = f"{DOMAIN}/Home/GetTracks?routeId={routeId}&ttId={timetableId}&transits={transits}"
        return httpx.get(url).json()

    @cache.memoize()
    def getBusStopDetails(self, timetableId: int, busStopId: int):
        url = (
            f"{DOMAIN}/Home/GetBusStopDetails?ttId={timetableId}&nBusStopId={busStopId}"
        )
        return httpx.get(url).json()

    @cache.memoize()
    def getBusStopRouteList(self, timetableId: int, busStopId: int):
        url = f"{DOMAIN}/Home/GetBusStopRouteList?id={busStopId}&ttId={timetableId}"
        return httpx.get(url).json()

    @cache.memoize()
    def getBusStopTimeTable(self, timetableId: int, busStopId: int, routeId: int):
        url = f"{DOMAIN}/Home/GetBusStopTimeTable?busStopId={busStopId}&routeId={routeId}&ttId={timetableId}"
        return httpx.get(url).json()

    @cache.memoize()
    def getRouteVariant(self, routeVariantId: int, timetableId: int):
        url = f"{DOMAIN}/Home/GetRouteVariant?id={routeVariantId}&ttId={timetableId}"
        return httpx.get(url).json()

    @cache.memoize()
    def getNextDepartures(self, busStopId: int):
        url = f"{DOMAIN}/Home/GetNextDepartues?busStopId={busStopId}"
        return httpx.get(url).json()


class GTFSTczew(object):
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

    def getRouteList(self, timetableId: int = 0) -> List[Route]:
        routes = self.tczewBusesApi.getRouteList(timetableId=timetableId)
        result = []
        for i in range(len(routes) // 2):
            result.append(Route(id=routes[2 * i], name=routes[2 * i + 1]))
        return result

    def getTimetableInformation(self) -> List[Timetable]:
        return [
            Timetable(id=timetable[0], date=timetable[1], future=timetable[2])
            for timetable in self.tczewBusesApi.getTimetableInformation()
        ]

    def getTracks(self, routeId: int, timetableId: int = 0, transits: int = 0):
        tracks = self.tczewBusesApi.getTracks(
            routeId=routeId, timetableId=timetableId, transits=transits
        )
        stops = tracks[0]
        mapping = tracks[1]
        variants = tracks[2]
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


gtfsTczew = GTFSTczew()
# gtfsTczew.saveBusStopsGeoJSON()
for route in gtfsTczew.getRouteList():
    data = gtfsTczew.getTracks(routeId=route.id)
# print(gtfsTczew.getTimetableInformation())
