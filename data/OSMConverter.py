from typing import Dict, List, cast

from data.GTFSConverter import (
    GTFSConverter,
    GTFSData,
    GTFSStop,
    GTFSRoute,
    GTFSTrip,
    RouteId,
    StopId,
    TripId, GTFSShape, shapesFromTrips,
)
from data.OSMSource import Relation, OSMSource, Way, Node
from data.TransportData import LatLon
from log import printWarning, printError

GTFS_TRIP_ID_TAG = "gtfs:trip_id"
GTFS_ROUTE_ID_TAG = "gtfs:route_id"


class OSMConverter(GTFSConverter):
    def data(self) -> GTFSData:
        pass

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

    def trips(self) -> Dict[TripId, GTFSTrip]:
        serviceId = "42"  # TODO
        result = dict()
        for osmRoute in self.routesOSM:
            for gtfsTripId, route in self._validateOSMVariants(osmRoute).items():
                result[gtfsTripId] = GTFSTrip(
                    routeId=route.tags[GTFS_ROUTE_ID_TAG],
                    serviceId=serviceId,
                    tripId=gtfsTripId,
                    shapeId=gtfsTripId,
                    shape=self._extractRouteGeometry(route),
                    busStopIds=self._extractBusStopIds(route),
                )
        return result

    def shapes(self) -> List[GTFSShape]:
        return shapesFromTrips(self.trips())


