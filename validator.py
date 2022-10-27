from dataclasses import dataclass
from typing import List

from log import printWarning
from osm import OSM
from transportData import TransportData


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


class Validator:
    def __init__(self):
        self.transportData = TransportData()
        self.osm = OSM()
        self.osm.fetchMainRelation()
        self.stopsTczew = self.transportData.getBusStops()
        self.stopsOSM = self.osm.getStops()
        self.routesTczew = self.transportData.getRoutes()

    @staticmethod
    def _validateStopOSM(stop):
        if "bus" not in stop.tags:
            printWarning(f"{stop} missing bus=yes tag")
        if "public_transport" not in stop.tags:
            printWarning(f"{stop} missing public_transport tag")

    def validatedStops(self) -> List[ValidatedStop]:
        osmIds = set(self.stopsOSM.keys())
        tczewIds = set(self.stopsTczew.keys())
        missingOSMIds = sorted(tczewIds - osmIds)
        if missingOSMIds:
            printWarning(f"Missing OSM bus stop refs: {missingOSMIds}")
        extraOSMIds = sorted(osmIds - tczewIds)
        if extraOSMIds:
            printWarning(f"Extra OSM bus stop refs: {extraOSMIds}")
        commonIds = osmIds & tczewIds
        result = []
        for ref in commonIds:
            stopOsm = self.stopsOSM[ref]
            self._validateStopOSM(stopOsm)
            stopTczew = self.stopsTczew[ref]
            if "name" not in stopOsm.tags:
                printWarning(f"{stopOsm} missing name tag")
                name = stopTczew.name
            else:
                name = stopOsm.tags["name"]
            result.append(
                ValidatedStop(
                    stopId=str(ref),
                    stopName=name,
                    stopLat=stopOsm.lat,
                    stopLon=stopOsm.lon,
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
        serviceId = "42" # TODO
        return [
            ValidatedTrip(routeId=str(route.id), serviceId=serviceId, tripId=str(variant.id))
            for route in self.routesTczew
            for variant in route.variants
        ]
