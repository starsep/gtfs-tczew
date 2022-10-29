from itertools import zip_longest
from typing import List, Dict

from pyproj import Geod
from rich.table import Table

from data.GTFSConverter import (
    GTFSConverter,
    GTFSStop,
    GTFSRoute,
    GTFSTrip,
    RouteId,
    TripId,
    StopId, GTFSShape, shapesFromTrips,
)
from data.OSMConverter import OSMConverter
from log import printWarning, printError, console

STOP_DISTANCE_WARNING_THRESHOLD = 100.0
STOP_DISTANCE_ERROR_THRESHOLD = 200.0


class OSMOperatorMerger(GTFSConverter):
    def __init__(
        self,
        osmConverter: OSMConverter,
        operatorConverter: GTFSConverter,
    ):
        self.operatorConverter = operatorConverter
        self.stopsOperator = operatorConverter.stops()
        self.stopsOSM = osmConverter.stops()
        self.routesOperator = operatorConverter.routes()
        self.routesOSM = osmConverter.routes()
        self.tripsOperator = operatorConverter.trips()
        self.tripsOSM = osmConverter.trips()
        self.wgs84Geod = Geod(ellps="WGS84")

    @staticmethod
    def _validateStopOSM(stop):
        if "bus" not in stop.tags:
            printWarning(f"{stop} missing bus=yes tag")
        if "public_transport" not in stop.tags:
            printWarning(f"{stop} missing public_transport tag")

    def _validateStopsDistance(self, stopOperator: GTFSStop, stopOsm: GTFSStop):
        stopsDistance = int(
            self.wgs84Geod.inv(
                stopOperator.stopLon,
                stopOperator.stopLat,
                stopOsm.stopLon,
                stopOsm.stopLat,
            )[2]
        )
        message = f"Distance between stops={stopsDistance}m. {stopOsm} {stopOperator}"
        if stopsDistance > STOP_DISTANCE_ERROR_THRESHOLD:
            printError(message)
        elif stopsDistance > STOP_DISTANCE_WARNING_THRESHOLD:
            printWarning(message)

    def stops(self) -> Dict[StopId, GTFSStop]:
        osmIds = set(self.stopsOSM.keys())
        operatorIds = set(self.stopsOperator.keys())
        missingOSMIds = sorted(operatorIds - osmIds)
        if missingOSMIds:
            queryMissing = " or ".join(map(lambda x: f"ref={x}", missingOSMIds))
            printWarning(f"Missing OSM bus stop refs: {queryMissing}")
        extraOSMIds = sorted(osmIds - operatorIds)
        if extraOSMIds:
            printWarning(f"Extra OSM bus stop refs: {extraOSMIds}")
        result = dict()
        for ref in operatorIds:
            stopOsm = None
            stopOperator = self.stopsOperator[ref]
            if ref in self.stopsOSM:
                stopOsm = self.stopsOSM[ref]
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
        if self.routesOSM.keys() == self.routesOperator.keys():
            return
        table = Table(title="OSM route_master vs Operator Route")

        table.add_column("ref OSM")
        table.add_column("name Operator")
        table.add_column("gtfs:route_id OSM")
        table.add_column("id Operator")

        allRefs = sorted(self.routesOSM.keys() | self.routesOperator.keys())
        for ref in allRefs:
            osmRoute = self.routesOSM.get(ref)
            operatorRoute = self.routesOperator.get(ref)
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
            if osmRef is None:
                printError(f"Missing OSM route with ref={ref}")
        console.print(table)

    def routes(self) -> Dict[RouteId, GTFSRoute]:
        self._showTableCompareRouteRefs()
        return self.routesOperator

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

        for ((refOSM, nameOSM), (refOperator, nameOperator)) in zip_longest(
            zip(osmBusStopIds, osmBusStopNames),
            zip(operatorBusStopsIds, operatorBusStopNames),
            fillvalue=("", ""),
        ):
            style = None if refOperator == refOSM else "red"
            table.add_row(refOSM, nameOSM, refOperator, nameOperator, style=style)
        console.print(table)

    def _compareListOfBusStopsTrip(
        self,
        osmTrip: GTFSTrip,
        operatorTrip: GTFSTrip,
        stops: Dict[StopId, GTFSStop],
    ):
        difference = len(osmTrip.busStopIds) != len(operatorTrip.busStopIds) or any(
            [
                operatorBusStopId != osmBusStopId
                for (osmBusStopId, operatorBusStopId) in zip(
                    osmTrip.busStopIds, operatorTrip.busStopIds
                )
            ]
        )
        if difference:
            self._showTableCompareRoutes(
                osmTrip.busStopIds,
                osmTrip.busStopNames(stops),
                operatorTrip.busStopIds,
                operatorTrip.busStopNames(stops),
                title=f"Issues in trip {osmTrip.tripId} route {osmTrip.routeId}",
            )

    def trips(self) -> Dict[TripId, GTFSTrip]:
        serviceId = "42"  # TODO
        result = dict()
        stops = self.stops()
        for tripId, operatorTrip in self.tripsOperator.items():
            osmTrip = self.tripsOSM.get(tripId)
            if osmTrip is None:
                printError(
                    f"Missing trip {tripId} for route {operatorTrip.routeId} in OSM"
                )
                result[tripId] = operatorTrip
                continue
            self._compareListOfBusStopsTrip(osmTrip, operatorTrip, stops)
            # self._compareTrips(tripId, osmVariant, operatorTrip)
            result[tripId] = osmTrip
        return result

    def shapes(self) -> List[GTFSShape]:
        return shapesFromTrips(self.trips())

    # def _compareTrips(
    #     self,
    #     routeRef: str,
    #     osmVariants: dict[str, Relation],
    #     _operatorVariants: list[RouteVariant],
    # ):
    #     operatorVariants = {str(variant.id): variant for variant in _operatorVariants}
    #     osmIds = set(osmVariants.keys())
    #     operatorVariantIds = set(operatorVariants.keys())
    #     if osmIds == operatorVariantIds:
    #         return
    #     table = Table(title=f"OSM route vs Operator Trip for Route {routeRef}")
    #
    #     table.add_column("ref OSM")
    #     table.add_column("name OSM")
    #     table.add_column("#OSM")
    #     table.add_column("ref Op")
    #     table.add_column("#Op")
    #     table.add_column("start Operator")
    #     table.add_column("end Operator")
    #
    #     commonIds = osmIds & operatorVariantIds
    #     for variantId in sorted(osmIds | operatorVariantIds):
    #         style = "red" if variantId not in commonIds else None
    #         osmId = variantId if variantId in osmIds else None
    #         osmVariant = osmVariants[osmId] if osmId is not None else None
    #         osmName = osmVariant.tags["name"] if osmId is not None else None
    #         osmBusStopsCount = (
    #             str(
    #                 len(
    #                     [
    #                         member.element
    #                         for member in osmVariant.members
    #                         if member.role.startswith("platform")
    #                     ]
    #                 )
    #             )
    #             if osmId is not None
    #             else None
    #         )
    #         operatorId = variantId if variantId in operatorVariantIds else None
    #         operatorVariant = (
    #             operatorVariants[variantId] if variantId in operatorVariants else None
    #         )
    #         start = operatorVariant.firstStopName if operatorVariant else None
    #         end = operatorVariant.lastStopName if operatorVariant else None
    #         operatorBusStopsCount = (
    #             str(len(operatorVariant.busStopsIds))
    #             if operatorVariant is not None
    #             else None
    #         )
    #         table.add_row(
    #             osmId,
    #             osmName,
    #             osmBusStopsCount,
    #             operatorId,
    #             operatorBusStopsCount,
    #             start,
    #             end,
    #             style=style,
    #         )
    #     console.print(table)
