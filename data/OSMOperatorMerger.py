from itertools import zip_longest
from typing import Dict, List

from rich.table import Table

from starsep_utils import haversine

from gtfs.GTFSConverter import (
    GTFSConverter,
    GTFSData,
    GTFSRoute,
    GTFSRouteVariant,
    GTFSService,
    GTFSShape,
    GTFSStop,
    GTFSStopTime,
    GTFSTrip,
    RouteId,
    RouteVariantId,
    StopId,
    TripId,
    shapesFromRouteVariants,
)
from log import console, printError, printWarning, printInfo

STOP_DISTANCE_WARNING_THRESHOLD = 100.0
STOP_DISTANCE_ERROR_THRESHOLD = 200.0


class OSMOperatorMerger(GTFSConverter):
    def __init__(
        self,
        osmData: GTFSData,
        operatorData: GTFSData,
    ):
        self.operatorData = operatorData
        self.osmData = osmData
        self.matchedOperatorToOSMVariantIds: Dict[RouteVariantId, RouteVariantId] = (
            dict()
        )

    @staticmethod
    def _validateStopOSM(stop):
        if "bus" not in stop.tags:
            printWarning(f"{stop} missing bus=yes tag")
        if "public_transport" not in stop.tags:
            printWarning(f"{stop} missing public_transport tag")

    def _validateStopsDistance(self, stopOperator: GTFSStop, stopOsm: GTFSStop):
        stopsDistance = haversine(stopOperator.toGeoPoint(), stopOsm.toGeoPoint())
        message = f"Distance between stops={stopsDistance}m. {stopOsm} {stopOperator}"
        if stopsDistance > STOP_DISTANCE_ERROR_THRESHOLD:
            printError(message)
        elif stopsDistance > STOP_DISTANCE_WARNING_THRESHOLD:
            printWarning(message)

    def stops(self) -> Dict[StopId, GTFSStop]:
        osmIds = set(self.osmData.stops.keys())
        operatorUsedStopIds = {
            busStopId
            for routeVariant in self.operatorData.routeVariants.values()
            for busStopId in routeVariant.busStopIds
        }
        missingOSMIds = sorted(operatorUsedStopIds - osmIds)
        if missingOSMIds:
            queryMissing = " or ".join(map(lambda x: f"ref={x}", missingOSMIds))
            printWarning(f"Missing OSM bus stop refs: {queryMissing}")
        extraOSMIds = sorted(osmIds - operatorUsedStopIds)
        if extraOSMIds:
            printWarning(f"Extra OSM bus stop refs: {extraOSMIds}")
        result = dict()
        for ref in operatorUsedStopIds:
            stopOsm = None
            stopOperator = self.operatorData.stops[ref]
            if ref in self.osmData.stops:
                stopOsm = self.osmData.stops[ref]
                self._validateStopsDistance(stopOperator, stopOsm)
            outputName = (
                stopOsm.stopName
                if stopOsm is not None and len(stopOsm.stopName) > 0
                else stopOperator.stopName
            )
            result[str(ref)] = GTFSStop(
                stopId=str(ref),
                stopName=outputName,
                stopLat=stopOsm.stopLat
                if stopOsm is not None
                else stopOperator.stopLat,
                stopLon=stopOsm.stopLon
                if stopOsm is not None
                else stopOperator.stopLon,
            )
        return result

    def _showTableCompareRouteRefs(self):
        if self.osmData.routes.keys() == self.operatorData.routes.keys():
            return
        table = Table(title="OSM route_master vs Operator Route")

        table.add_column("ref OSM")
        table.add_column("name Operator")
        table.add_column("gtfs:route_id OSM")
        table.add_column("id Operator")

        allRefs = sorted(self.osmData.routes.keys() | self.operatorData.routes.keys())
        for ref in allRefs:
            operatorRoute = self.operatorData.routes.get(ref)
            osmRoute = self.osmData.routes.get(ref)
            if osmRoute is None and operatorRoute is not None:
                matchedRoutes = list(
                    filter(
                        lambda route: route.routeName == operatorRoute.routeName,
                        self.osmData.routes.values(),
                    )
                )
                if len(matchedRoutes) == 1:
                    osmRoute = matchedRoutes[0]
                    printInfo(
                        f"Matched route by name (OSM ref): {osmRoute} vs {operatorRoute}"
                    )
            osmRef = osmRoute.routeName if osmRoute is not None else None
            osmId = osmRoute.routeId if osmRoute is not None else None
            operatorName = (
                operatorRoute.routeName if operatorRoute is not None else None
            )
            operatorId = operatorRoute.routeId if operatorRoute is not None else None
            table.add_row(
                osmRef,
                operatorName,
                osmId,
                operatorId,
                style="red" if osmRef != operatorName else None,
            )
            if osmRoute is None:
                printError(f"Missing OSM route with ref={ref}")
        console.print(table)

    def routes(self) -> Dict[RouteId, GTFSRoute]:
        self._showTableCompareRouteRefs()
        return self.operatorData.routes

    def _showTableCompareRoutes(
        self,
        osmBusStopIds: List[str],
        osmBusStopNames: List[str],
        operatorBusStopsIds: List[str],
        operatorBusStopNames: List[str],
        title: str,
    ):
        table = Table(title=title)

        table.add_column("ref OSM")
        table.add_column("name OSM")
        table.add_column("ref Operator")
        table.add_column("name Operator")

        for (refOSM, nameOSM), (refOperator, nameOperator) in zip_longest(
            zip(osmBusStopIds, osmBusStopNames),
            zip(operatorBusStopsIds, operatorBusStopNames),
            fillvalue=("", ""),
        ):
            style = None if refOperator == refOSM else "red"
            table.add_row(refOSM, nameOSM, refOperator, nameOperator, style=style)
        console.print(table)

    def _compareListOfBusStopsVariant(
        self,
        osmVariant: GTFSRouteVariant,
        operatorVariant: GTFSRouteVariant,
        stops: Dict[StopId, GTFSStop],
    ):
        difference = len(osmVariant.busStopIds) != len(
            operatorVariant.busStopIds
        ) or any(
            [
                operatorBusStopId != osmBusStopId
                for (osmBusStopId, operatorBusStopId) in zip(
                    osmVariant.busStopIds, operatorVariant.busStopIds
                )
            ]
        )
        if difference:
            self._showTableCompareRoutes(
                osmVariant.busStopIds,
                osmVariant.busStopNames(stops),
                operatorVariant.busStopIds,
                operatorVariant.busStopNames(stops),
                title=f"Issues in variant {osmVariant.routeVariantId} route {osmVariant.routeId}",
            )

    def routeVariants(
        self, stops: Dict[StopId, GTFSStop], routes: Dict[RouteId, GTFSRoute]
    ) -> Dict[RouteVariantId, GTFSRouteVariant]:
        result = dict()
        for variantId, operatorVariant in self.operatorData.routeVariants.items():
            osmVariant = self.osmData.routeVariants.get(variantId)
            if osmVariant is None:
                printWarning(
                    f"Missing variant {variantId} for route {operatorVariant.routeId} in OSM"
                )
                osmVariantByBusStopIds = list(
                    filter(
                        lambda osmRouteVariant: osmRouteVariant.busStopIds
                        == operatorVariant.busStopIds,
                        self.osmData.routeVariants.values(),
                    )
                )
                if len(osmVariantByBusStopIds) > 1:
                    printError(
                        f"Multiple OSM variants with matching bus stops ids: {osmVariantByBusStopIds} vs {operatorVariant}"
                    )
                    result[variantId] = operatorVariant
                    continue
                if len(osmVariantByBusStopIds) == 1:
                    printInfo(
                        f"Matched OSM variant by bus stop ids: OSM {osmVariantByBusStopIds[0].routeVariantId} vs {operatorVariant.routeVariantId}"
                    )
                    osmVariant = osmVariantByBusStopIds[0]
                    self.matchedOperatorToOSMVariantIds[variantId] = (
                        osmVariant.routeVariantId
                    )
                    result[osmVariant.routeVariantId] = osmVariant
                if len(osmVariantByBusStopIds) == 0:
                    printError(
                        f"Couldn't match OSM variant by bus stop ids for {operatorVariant.routeVariantId}"
                    )
                    result[variantId] = operatorVariant
                    continue
            self._compareListOfBusStopsVariant(osmVariant, operatorVariant, stops)
        self._compareRouteVariants(
            self.osmData.routeVariants,
            self.operatorData.routeVariants,
            stops,
        )
        return result

    def trips(
        self,
        stops: Dict[StopId, GTFSStop],
        services: List[GTFSService],
        routeVariants: Dict[RouteVariantId, GTFSRouteVariant],
    ) -> Dict[TripId, GTFSTrip]:
        return {
            tripId: GTFSTrip(
                tripId=tripId,
                routeId=trip.routeId,
                routeVariantId=trip.routeVariantId,
                shape=trip.shape,
                busStopIds=trip.busStopIds,
                shapeId=self.matchedOperatorToOSMVariantIds.get(
                    trip.routeVariantId, trip.shapeId
                ),
                tripStartMinutes=trip.tripStartMinutes,
                serviceId=trip.serviceId,
                routeVariantName=trip.routeVariantName,
            )
            for tripId, trip in self.operatorData.trips.items()
        }

    def shapes(
        self, routeVariants: Dict[RouteVariantId, GTFSRouteVariant]
    ) -> List[GTFSShape]:
        return shapesFromRouteVariants(routeVariants)

    def services(self) -> List[GTFSService]:
        return self.operatorData.services

    def stopTimes(
        self,
        routes: Dict[RouteId, GTFSRoute],
        routeVariants: Dict[RouteVariantId, GTFSRouteVariant],
        trips: Dict[TripId, GTFSTrip],
    ) -> List[GTFSStopTime]:
        return self.operatorData.stopTimes

    def _compareRouteVariants(
        self,
        osmVariants: Dict[RouteVariantId, GTFSRouteVariant],
        operatorVariants: Dict[RouteVariantId, GTFSRouteVariant],
        stops: Dict[StopId, GTFSStop],
    ):
        osmIds = set(osmVariants.keys())
        operatorVariantIds = set(operatorVariants.keys())
        if osmIds == operatorVariantIds:
            return
        table = Table(title=f"OSM route vs Operator Route Variants")

        table.add_column("ref OSM")
        table.add_column("name OSM")
        table.add_column("#OSM")
        table.add_column("ref Op")
        table.add_column("#Op")
        table.add_column("start Operator")
        table.add_column("end Operator")

        commonIds = osmIds & operatorVariantIds
        for variantId in sorted(osmIds | operatorVariantIds):
            if variantId in self.matchedOperatorToOSMVariantIds.values():
                continue
            osmId = variantId if variantId in osmIds else None
            osmId = (
                self.matchedOperatorToOSMVariantIds[variantId]
                if variantId in self.matchedOperatorToOSMVariantIds
                else osmId
            )
            osmVariant = osmVariants[osmId] if osmId is not None else None
            osmName = osmVariant.routeVariantName if osmVariant is not None else None
            osmBusStopsCount = (
                str(len(osmVariant.busStopIds)) if osmVariant is not None else None
            )
            operatorId = variantId if variantId in operatorVariantIds else None
            operatorVariant = (
                operatorVariants[variantId] if variantId in operatorVariants else None
            )
            start = operatorVariant.busStopNames(stops)[0] if operatorVariant else None
            end = operatorVariant.busStopNames(stops)[-1] if operatorVariant else None
            operatorBusStopsCount = (
                str(len(operatorVariant.busStopIds))
                if operatorVariant is not None
                else None
            )
            style = "red" if operatorId is None or osmId is None else None
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
