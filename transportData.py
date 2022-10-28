from dataclasses import dataclass
from typing import List, Dict

import geojson
from geojson import Feature, FeatureCollection, Point, LineString

from api import TczewBusesAPI
from configuration import outputDir


@dataclass(eq=True)
class LatLon:
    latitude: float
    longitude: float

    def toPoint(self):
        return Point((self.longitude, self.latitude))


@dataclass
class BusStop(LatLon):
    id: str
    name: str


@dataclass
class RouteVariant:
    id: int
    # ?: int
    # ?: int
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
    future: bool  # ?


class TransportData(object):
    def __init__(self) -> None:
        super().__init__()
        self.tczewBusesApi = TczewBusesAPI()

    def getBusStops(self, timetableId: int = 0) -> Dict[int, BusStop]:
        stops = dict()
        for stop in self.tczewBusesApi.getMapBusStops(timetableId=timetableId):
            stops[stop[0]] = BusStop(
                id=stop[0], name=stop[1], latitude=stop[5], longitude=stop[4]
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
        self, routeId: int, timetableId: int = 0, transits: int = 1
    ) -> List[RouteVariant]:
        tracks = self.tczewBusesApi.getTracks(
            routeId=routeId, timetableId=timetableId, transits=transits
        )
        stops = tracks[0]
        mapping = tracks[1]
        geometry = tracks[2]

        def parseCoords(coords: List[float]) -> List[LatLon]:
            result = []
            for i in range(len(coords) // 2):
                result.append(LatLon(coords[2 * i], coords[2 * i + 1]))
            return result

        legsGeometry = dict()
        for leg in geometry:
            legsGeometry[(leg[1], leg[2])] = parseCoords(leg[3])
        variants = []
        for variant in tracks[3]:
            variantRouteBusStopIds = variant[6][0]
            variantGeometry = []
            for stopPair in zip(
                variantRouteBusStopIds[:-1], variantRouteBusStopIds[1:]
            ):
                for point in legsGeometry[stopPair]:
                    variantGeometry.append(point)
            variants.append(
                RouteVariant(
                    id=variant[0],
                    direction=variant[3],
                    firstStopName=variant[4],
                    lastStopName=variant[5],
                    busStopsIds=[
                        stops[routeBusStopId][0]
                        for routeBusStopId in variantRouteBusStopIds
                    ],
                    geometry=variantGeometry,
                )
            )
        return variants

    def saveBusStopsGeoJSON(self):
        stops = self.getBusStops().values()
        features = []
        for stop in stops:
            features.append(
                Feature(
                    geometry=stop.toPoint(),
                    properties=dict(ref=stop.id, name=stop.name),
                )
            )
        with (outputDir / "stops.geojson").open("w") as f:
            geojson.dump(FeatureCollection(features=features), f)

    def saveBusRoutesVariantsGeoJSON(self):
        features = []
        for route in self.getRoutes():
            for variant in self.getRouteVariants(routeId=route.id):
                points = [
                    (point.latitude, point.longitude) for point in variant.geometry
                ]
                properties = dict(
                    name=f"Bus {route.name}",
                    variantId=variant.id,
                    to=variant.lastStopName,
                )
                properties["from"] = variant.firstStopName
                features.append(
                    Feature(
                        geometry=LineString(points),
                        properties=properties,
                    )
                )
        with (outputDir / f"routes.geojson").open("w") as f:
            geojson.dump(FeatureCollection(features=features), f)

    def generateGeoJSONs(self):
        self.saveBusStopsGeoJSON()
        self.saveBusRoutesVariantsGeoJSON()
