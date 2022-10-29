from dataclasses import dataclass
from itertools import zip_longest
from typing import List, Dict

from rich.table import Table

from configuration import TCZEW_PUBLIC_TRANSPORT_RELATION_ID
from data.tczewTransportData import TczewTransportData
from log import printWarning, printError, console
from data.osmOverpass import OSMOverpass
from data.osmSource import Node, Relation
from pyproj import Geod
from data.transportData import TransportData, BusStop, LatLon, RouteVariant

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
        self.transportData = TczewTransportData()
        self.osmSource = OSMOverpass()
        self.osmSource.savePublicTransportRelation(TCZEW_PUBLIC_TRANSPORT_RELATION_ID)
        self.stopsTczew = self.transportData.getBusStops()
        self.stopsOSM = self.osmSource.getStops()
        self.routesTczew = self.transportData.getRoutes()
        self.routesOSM = self.osmSource.getRoutes()
        self.routeIdToOSMRoute: Dict[str, Relation] = dict()
        self.validatedStops = None
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

    def validateStops(self) -> List[ValidatedStop]:
        if self.validatedStops is not None:
            return self.validatedStops
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
        self.validatedStops = result
        return result

    def validatedRoutes(self) -> List[ValidatedRoute]:
        osmRouteIds = set()
        gtfsRouteIdTag = "gtfs:route_id"
        for osmRoute in self.routesOSM:
            if gtfsRouteIdTag not in osmRoute.tags:
                printError(f"Missing tag {gtfsRouteIdTag} for relation {osmRoute.id}")
            else:
                osmRouteId = osmRoute.tags[gtfsRouteIdTag]
                self.routeIdToOSMRoute[osmRouteId] = osmRoute
                osmRouteIds.add(osmRouteId)
        tczewRoutesIds = {str(route.id) for route in self.routesTczew}
        if osmRouteIds != tczewRoutesIds:
            printError(
                f"Different route ids (OSM vs Tczew):\n{osmRouteIds}\n{tczewRoutesIds}"
            )
        for routeId in osmRouteIds & tczewRoutesIds:
            osmRoute = next(
                filter(
                    lambda route: route.tags[gtfsRouteIdTag] == routeId, self.routesOSM
                )
            )
            tczewRoute = next(
                filter(lambda route: str(route.id) == routeId, self.routesTczew)
            )
            osmRef = osmRoute.tags.get("ref")
            if osmRef != tczewRoute.name:
                printError(
                    f"Different ref/name {osmRef}/{tczewRoute.name} for relation {osmRoute.id}"
                )
        return [
            ValidatedRoute(routeId=str(route.id), routeName=route.name)
            for route in self.routesTczew
        ]

    def _validateOSMVariants(self, osmRoute: Relation) -> Dict[str, Relation]:
        result = dict()
        gtfsTripIdsTag = "gtfs:trip_id"
        for member in osmRoute.members:
            route = member.element
            if gtfsTripIdsTag not in route.tags:
                printError(f"Relation {route.id} missing {gtfsTripIdsTag} tag")
            else:
                result[route.tags[gtfsTripIdsTag]] = route
        return result

    def _showTableCompareRoutes(
        self,
        osmBusStopIds: List[str],
        osmBusStopNames: List[str],
        operatorBusStopNames: List[str],
        operatorBusStopsIds: List[str],
        title: str,
    ):
        table = Table(title=title)

        table.add_column("ref OSM")
        table.add_column("name OSM")
        table.add_column("ref Operator")
        table.add_column("name Operator")

        for ((refOSM, nameOSM), (refOperator, nameOperator)) in zip_longest(
            zip(osmBusStopIds, osmBusStopNames),
            zip(operatorBusStopsIds, operatorBusStopNames),
            fillvalue=("", ""),
        ):
            style = None if refOperator in refOSM else "red"
            table.add_row(refOSM, nameOSM, refOperator, nameOperator, style=style)
        console.print(table)

    def _compareListOfBusStopsVariants(
        self,
        osmVariant: Relation,
        variant: RouteVariant,
        stopIdToValidatedStop: Dict[str, ValidatedStop],
    ):
        osmBusStops = [
            member.element
            for member in osmVariant.members
            if member.role.startswith("platform")
        ]
        operatorBusStopIds = list(map(str, variant.busStopsIds))
        osmBusStopIds = [busStop.tags["ref"] for busStop in osmBusStops]
        difference = len(osmBusStopIds) != len(operatorBusStopIds) and any(
            [
                operatorBusStopId not in osmBusStopId
                for (operatorBusStopId, osmBusStopId) in zip(
                    operatorBusStopIds, osmBusStopIds
                )
            ]
        )
        if difference:
            osmBusStopNames = [busStop.tags["name"] for busStop in osmBusStops]
            tczewBusStopNames = [
                stopIdToValidatedStop[busStopId].stopName
                for busStopId in operatorBusStopIds
            ]
            self._showTableCompareRoutes(
                osmBusStopIds,
                osmBusStopNames,
                tczewBusStopNames,
                operatorBusStopIds,
                title=f"Issues in relation {osmVariant.tags['name']} {osmVariant.id}",
            )

    def validatedTrips(self):
        serviceId = "42"  # TODO
        result = []
        for route in self.routesTczew:
            routeId = str(route.id)
            osmRoute = self.routeIdToOSMRoute[routeId]
            osmVariants = self._validateOSMVariants(osmRoute)
            stopIdToValidatedStop = {stop.stopId: stop for stop in self.validateStops()}
            for variant in route.variants:
                variantId = str(variant.id)
                osmVariant = osmVariants[variantId]
                self._compareListOfBusStopsVariants(
                    osmVariant, variant, stopIdToValidatedStop
                )
                result.append(
                    ValidatedTrip(
                        routeId=routeId,
                        serviceId=serviceId,
                        tripId=str(variant.id),
                        shape=variant.geometry,
                        busStopIds=list(map(str, variant.busStopsIds)),
                    )
                )
        return result
