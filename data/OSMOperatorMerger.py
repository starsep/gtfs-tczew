from dataclasses import dataclass
from itertools import zip_longest
from typing import List, Dict

from rich.table import Table

from data.Validator import (
    Validator,
    STOP_DISTANCE_ERROR_THRESHOLD,
    STOP_DISTANCE_WARNING_THRESHOLD,
    ValidatedStop,
    ValidatedRoute,
    ValidatedTrip,
)
from log import printWarning, printError, console
from data.OSMSource import Node, Relation, OSMSource
from pyproj import Geod
from data.TransportData import TransportData, BusStop, LatLon, RouteVariant, Route


class OSMOperatorMerger(Validator):
    def __init__(self, osmSource: OSMSource, transportData: TransportData):
        self.transportData = transportData
        self.osmSource = osmSource
        self.osmSource.savePublicTransportRelation()
        self.stopsOperator = self.transportData.getBusStops()
        self.stopsOSM = self.osmSource.getStops()
        self.routesOperator = self.transportData.getRoutes()
        self.routesOSM = self.osmSource.getRoutes()
        self.routeRefToOSMRoute: Dict[str, Relation] = dict()
        self.validatedStops = None
        self.wgs84Geod = Geod(ellps="WGS84")

    @staticmethod
    def _validateStopOSM(stop):
        if "bus" not in stop.tags:
            printWarning(f"{stop} missing bus=yes tag")
        if "public_transport" not in stop.tags:
            printWarning(f"{stop} missing public_transport tag")

    def _validateStopsDistance(self, stopOperator: BusStop, stopOsm: Node):
        stopsDistance = int(
            self.wgs84Geod.inv(
                stopOperator.longitude, stopOperator.latitude, stopOsm.lon, stopOsm.lat
            )[2]
        )
        message = f"Distance between stops={stopsDistance}m. {stopOsm} {stopOperator}"
        if stopsDistance > STOP_DISTANCE_ERROR_THRESHOLD:
            printError(message)
        elif stopsDistance > STOP_DISTANCE_WARNING_THRESHOLD:
            printWarning(message)

    def validateStops(self) -> List[ValidatedStop]:
        if self.validatedStops is not None:
            return self.validatedStops
        osmIds = set(self.stopsOSM.keys())
        operatorIds = set(self.stopsOperator.keys())
        missingOSMIds = sorted(operatorIds - osmIds)
        if missingOSMIds:
            queryMissing = " or ".join(map(lambda x: f"ref={x}", missingOSMIds))
            printWarning(f"Missing OSM bus stop refs: {queryMissing}")
        extraOSMIds = sorted(osmIds - operatorIds)
        if extraOSMIds:
            printWarning(f"Extra OSM bus stop refs: {extraOSMIds}")
        result = []
        for ref in operatorIds:
            stopOsm = None
            stopOperator = self.stopsOperator[ref]
            if ref in self.stopsOSM:
                stopOsm = self.stopsOSM[ref]
                self._validateStopOSM(stopOsm)
                self._validateStopsDistance(stopOperator, stopOsm)
            if stopOsm is None or "name" not in stopOsm.tags:
                if stopOsm is not None:
                    printWarning(f"{stopOsm} missing name tag")
                name = stopOperator.name
            else:
                name = stopOsm.tags["name"]
            result.append(
                ValidatedStop(
                    stopId=str(ref),
                    stopName=name,
                    stopLat=stopOsm.lat
                    if stopOsm is not None
                    else stopOperator.latitude,
                    stopLon=stopOsm.lon
                    if stopOsm is not None
                    else stopOperator.longitude,
                )
            )
        self.validatedStops = result
        return result

    def _showTableCompareRouteRefs(
        self,
        routeRefToOSMRoute: Dict[str, Relation],
        operatorRouteNameToRoute: Dict[str, Route],
    ):
        table = Table(title="OSM route_master vs Operator Route")

        table.add_column("ref OSM")
        table.add_column("name Operator")
        table.add_column("gtfs:route_id OSM")
        table.add_column("id Operator")

        gtfsRouteIdTag = "gtfs:route_id"

        allRefs = sorted(routeRefToOSMRoute | operatorRouteNameToRoute)
        for ref in allRefs:
            osmRoute = routeRefToOSMRoute.get(ref)
            operatorRoute = operatorRouteNameToRoute.get(ref)
            osmRef = osmRoute.tags["ref"] if osmRoute is not None else None
            operatorName = operatorRoute.name if operatorRoute is not None else None
            gtfsRouteIdOSM = (
                osmRoute.tags["gtfs:route_id"]
                if osmRoute is not None and gtfsRouteIdTag in osmRoute.tags
                else None
            )
            operatorId = str(operatorRoute.id) if operatorRoute is not None else None
            table.add_row(
                osmRef,
                operatorName,
                gtfsRouteIdOSM,
                operatorId,
                style="red" if osmRef != operatorName else None,
            )
            if osmRef is None:
                printError(f"Missing OSM route with ref={ref}")
        console.print(table)

    def validatedRoutes(self) -> List[ValidatedRoute]:
        gtfsRouteIdTag = "gtfs:route_id"
        for osmRoute in self.routesOSM:
            if gtfsRouteIdTag not in osmRoute.tags:
                printError(f"Missing tag {gtfsRouteIdTag} for relation {osmRoute.id}")
            osmRouteRef = osmRoute.tags["ref"]
            self.routeRefToOSMRoute[osmRouteRef] = osmRoute
        operatorRouteNameToRoute = {
            str(route.name): route for route in self.routesOperator
        }
        if self.routeRefToOSMRoute.keys() != operatorRouteNameToRoute.keys():
            self._showTableCompareRouteRefs(
                self.routeRefToOSMRoute, operatorRouteNameToRoute
            )
        osmRouteNames = set(self.routeRefToOSMRoute.keys())
        operatorRouteNames = set(operatorRouteNameToRoute.keys())
        for routeRef in osmRouteNames & operatorRouteNames:
            osmRoute = next(
                filter(lambda route: route.tags["ref"] == routeRef, self.routesOSM)
            )
            operatorRoute = next(
                filter(lambda route: str(route.name) == routeRef, self.routesOperator)
            )
            osmRef = osmRoute.tags.get("ref")
            if osmRef != operatorRoute.name:
                printError(
                    f"Different ref/name {osmRef}/{operatorRoute.name} for relation {osmRoute.id}"
                )
        return [
            ValidatedRoute(routeId=str(route.id), routeName=route.name)
            for route in self.routesOperator
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
            operatorBusStopNames = [
                stopIdToValidatedStop[busStopId].stopName
                for busStopId in operatorBusStopIds
            ]
            self._showTableCompareRoutes(
                osmBusStopIds,
                osmBusStopNames,
                operatorBusStopNames,
                operatorBusStopIds,
                title=f"Issues in relation {osmVariant.tags['name']} {osmVariant.id}",
            )

    def validatedTrips(self):
        serviceId = "42"  # TODO
        result = []
        for route in self.routesOperator:
            routeRef = str(route.name)
            if routeRef not in self.routeRefToOSMRoute:
                continue
            osmRoute = self.routeRefToOSMRoute[routeRef]
            osmVariants = self._validateOSMVariants(osmRoute)
            stopIdToValidatedStop = {stop.stopId: stop for stop in self.validateStops()}
            self._compareVariants(routeRef, osmVariants, route.variants)
            for variant in route.variants:
                variantId = str(variant.id)
                osmVariant = osmVariants[variantId]
                self._compareListOfBusStopsVariants(
                    osmVariant, variant, stopIdToValidatedStop
                )
                result.append(
                    ValidatedTrip(
                        routeId=str(route.id),
                        serviceId=serviceId,
                        tripId=str(variant.id),
                        shape=variant.geometry,
                        busStopIds=list(map(str, variant.busStopsIds)),
                    )
                )
        return result

    def _compareVariants(
        self,
        routeRef: str,
        osmVariants: dict[str, Relation],
        _operatorVariants: list[RouteVariant],
    ):
        operatorVariants = {str(variant.id): variant for variant in _operatorVariants}
        osmIds = set(osmVariants.keys())
        operatorVariantIds = set(operatorVariants.keys())
        if osmIds == operatorVariantIds:
            return
        table = Table(title=f"OSM route vs Operator Trip for Route {routeRef}")

        table.add_column("ref OSM")
        table.add_column("name OSM")
        table.add_column("#OSM")
        table.add_column("ref Op")
        table.add_column("#Op")
        table.add_column("start Operator")
        table.add_column("end Operator")

        commonIds = osmIds & operatorVariantIds
        for variantId in sorted(osmIds | operatorVariantIds):
            style = "red" if variantId not in commonIds else None
            osmId = variantId if variantId in osmIds else None
            osmVariant = osmVariants[osmId] if osmId is not None else None
            osmName = osmVariant.tags["name"] if osmId is not None else None
            osmBusStopsCount = (
                str(
                    len(
                        [
                            member.element
                            for member in osmVariant.members
                            if member.role.startswith("platform")
                        ]
                    )
                )
                if osmId is not None
                else None
            )
            operatorId = variantId if variantId in operatorVariantIds else None
            operatorVariant = (
                operatorVariants[variantId] if variantId in operatorVariants else None
            )
            start = operatorVariant.firstStopName if operatorVariant else None
            end = operatorVariant.lastStopName if operatorVariant else None
            operatorBusStopsCount = (
                str(len(operatorVariant.busStopsIds))
                if operatorVariant is not None
                else None
            )
            table.add_row(
                osmId,
                osmName,
                osmBusStopsCount,
                operatorId,
                operatorBusStopsCount,
                start,
                end,
                style=style,
            )
        console.print(table)
