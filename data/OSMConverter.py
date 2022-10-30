from typing import Dict, List, cast

from data.GTFSConverter import (
    GTFSConverter,
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
from data.OSMSource import Node, OSMSource, Relation, Way
from data.TransportData import LatLon
from log import printError, printWarning

GTFS_TRIP_ID_TAG = "gtfs:trip_id"
GTFS_ROUTE_ID_TAG = "gtfs:route_id"


class OSMConverter(GTFSConverter):
    def __init__(self, osmSource: OSMSource):
        self.osmSource = osmSource
        self.osmSource.savePublicTransportRelation()
        self.stopsOSM = self.osmSource.getStops()
        self.routesOSM = self.osmSource.getRoutes()
        self.routeRefToOSMRoute: Dict[str, Relation] = dict()

    @staticmethod
    def _validateStopOSM(stop):
        if "bus" not in stop.tags:
            printWarning(f"{stop} missing bus=yes tag")
        if "public_transport" not in stop.tags:
            printWarning(f"{stop} missing public_transport tag")

    def stops(self) -> Dict[StopId, GTFSStop]:
        osmIds = set(self.stopsOSM.keys())
        result = dict()
        for ref in osmIds:
            name = ""
            stopOsm = self.stopsOSM[ref]
            self._validateStopOSM(stopOsm)
            if stopOsm is None or "name" not in stopOsm.tags:
                if stopOsm is not None:
                    printWarning(f"{stopOsm} missing name tag")
            else:
                name = stopOsm.tags["name"]
            result[ref] = GTFSStop(
                stopId=ref,
                stopName=name,
                stopLat=stopOsm.lat,
                stopLon=stopOsm.lon,
            )
        return result

    def routes(self) -> Dict[RouteId, GTFSRoute]:
        gtfsRouteIdTag = "gtfs:route_id"
        result = dict()
        for osmRoute in self.routesOSM:
            routeId = ""
            if gtfsRouteIdTag not in osmRoute.tags:
                printError(f"Missing tag {gtfsRouteIdTag} for relation {osmRoute.id}")
            else:
                routeId = osmRoute.tags[gtfsRouteIdTag]
            osmRouteRef = osmRoute.tags["ref"]
            self.routeRefToOSMRoute[osmRouteRef] = osmRoute
            result[routeId] = GTFSRoute(routeId=routeId, routeName=osmRouteRef)
        return result

    @staticmethod
    def _validateOSMVariants(osmRoute: Relation) -> Dict[TripId, Relation]:
        result: Dict[TripId, Relation] = dict()
        for member in osmRoute.members:
            route = member.element
            if GTFS_TRIP_ID_TAG not in route.tags:
                printError(f"Relation {route.id} missing {GTFS_TRIP_ID_TAG} tag")
            elif GTFS_ROUTE_ID_TAG not in route.tags:
                printError(f"Relation {route.id} missing {GTFS_ROUTE_ID_TAG} tag")
            else:
                result[route.tags[GTFS_TRIP_ID_TAG]] = cast(Relation, route)
        return result

    @staticmethod
    def _extractRouteGeometry(osmRoute: Relation) -> List[LatLon]:
        result = []
        for member in osmRoute.members:
            if member.role != "" or member.type != "way":
                continue
            way = cast(Way, member.element)
            for node in way.nodes:
                result.append(LatLon(latitude=node.lat, longitude=node.lon))
        return result

    @staticmethod
    def _extractBusStopIds(osmRoute: Relation) -> List[StopId]:
        result = []
        for member in osmRoute.members:
            if not member.role.startswith("platform"):
                continue
            if member.type != "node":
                printError(f"Invalid platform {member.element.id} type {member.type}")
                continue
            stop = cast(Node, member.element)
            result.append(stop.tags["ref"])
        return result

    def routeVariants(
        self, stops: Dict[StopId, GTFSStop]
    ) -> Dict[RouteVariantId, GTFSRouteVariant]:
        result = dict()
        for osmRoute in self.routesOSM:
            for routeVariantId, route in self._validateOSMVariants(osmRoute).items():
                result[routeVariantId] = GTFSRouteVariant(
                    routeId=route.tags[GTFS_ROUTE_ID_TAG],
                    routeVariantId=routeVariantId,
                    shapeId=routeVariantId,
                    shape=self._extractRouteGeometry(route),
                    busStopIds=self._extractBusStopIds(route),
                )
        return result

    def trips(
        self,
        stops: Dict[StopId, GTFSStop],
        services: List[GTFSService],
        routeVariants: Dict[RouteVariantId, GTFSRouteVariant],
    ) -> Dict[TripId, GTFSTrip]:
        return dict()

    def shapes(
        self, routeVariants: Dict[RouteVariantId, GTFSRouteVariant]
    ) -> List[GTFSShape]:
        return shapesFromRouteVariants(routeVariants)

    def services(self) -> List[GTFSService]:
        return []

    def stopTimes(
        self,
        routes: Dict[RouteId, GTFSRoute],
        routeVariants: Dict[RouteVariantId, GTFSRouteVariant],
        trips: Dict[TripId, GTFSTrip],
    ) -> List[GTFSStopTime]:
        return []
