from dataclasses import dataclass
from typing import List

from log import printWarning, printError
from osm import OSM, Node
from pyproj import Geod
from transportData import TransportData, BusStop, LatLon

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


class Validator:
    def __init__(self):
        self.transportData = TransportData()
        self.osm = OSM()
        self.osm.fetchMainRelation()
        self.stopsTczew = self.transportData.getBusStops()
        self.stopsOSM = self.osm.getStops()
        self.routesTczew = self.transportData.getRoutes()
        self.wgs84Geod = Geod(ellps="WGS84")

    @staticmethod
    def _validateStopOSM(stop):
        if "bus" not in stop.tags:
            printWarning(f"{stop} missing bus=yes tag")
        if "public_transport" not in stop.tags:
            printWarning(f"{stop} missing public_transport tag")

    def _validateStopsDistance(self, stopTczew: BusStop, stopOsm: Node):
        stopsDistance = int(
            self.wgs84Geod.inv(
                stopTczew.longitude, stopTczew.latitude, stopOsm.lon, stopOsm.lat
            )[2]
        )
        message = f"Distance between stops={stopsDistance}m. {stopOsm} {stopTczew}"
        if stopsDistance > STOP_DISTANCE_ERROR_THRESHOLD:
            printError(message)
        elif stopsDistance > STOP_DISTANCE_WARNING_THRESHOLD:
            printWarning(message)

    def validatedStops(self) -> List[ValidatedStop]:
        osmIds = set(self.stopsOSM.keys())
        tczewIds = set(self.stopsTczew.keys())
        missingOSMIds = sorted(tczewIds - osmIds)
        if missingOSMIds:
            queryMissing = " or ".join(map(lambda x: f"ref={x}", missingOSMIds))
            printWarning(f"Missing OSM bus stop refs: {queryMissing}")
        extraOSMIds = sorted(osmIds - tczewIds)
        if extraOSMIds:
            printWarning(f"Extra OSM bus stop refs: {extraOSMIds}")
        result = []
        for ref in tczewIds:
            stopOsm = None
            stopTczew = self.stopsTczew[ref]
            if ref in self.stopsOSM:
                stopOsm = self.stopsOSM[ref]
                self._validateStopOSM(stopOsm)
                self._validateStopsDistance(stopTczew, stopOsm)
            if stopOsm is None or "name" not in stopOsm.tags:
                if stopOsm is not None:
                    printWarning(f"{stopOsm} missing name tag")
                name = stopTczew.name
            else:
                name = stopOsm.tags["name"]
            result.append(
                ValidatedStop(
                    stopId=str(ref),
                    stopName=name,
                    stopLat=stopOsm.lat if stopOsm is not None else stopTczew.latitude,
                    stopLon=stopOsm.lon if stopOsm is not None else stopTczew.longitude,
                )
            )
        return result

    def validatedRoutes(self) -> List[ValidatedRoute]:
        # TODO: validate with OSM
        return [
            ValidatedRoute(routeId=str(route.id), routeName=route.name)
            for route in self.routesTczew
        ]

    def validatedTrips(self):
        # TODO: validate with OSM
        serviceId = "42"  # TODO
        return [
            ValidatedTrip(
                routeId=str(route.id),
                serviceId=serviceId,
                tripId=str(variant.id),
                shape=variant.geometry,
                busStopIds=list(map(str, variant.busStopsIds)),
            )
            for route in self.routesTczew
            for variant in route.variants
        ]
