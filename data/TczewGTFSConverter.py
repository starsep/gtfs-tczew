from typing import List, Dict

from data.GTFSConverter import (
    GTFSConverter,
    GTFSRoute,
    GTFSStop,
    StopId,
    RouteId,
    GTFSTrip,
    TripId,
)
from data.TczewTransportData import TczewTransportData


class TczewGTFSConverter(GTFSConverter):
    def __init__(self, tczewTransportData: TczewTransportData):
        self.tczewTransportData = tczewTransportData
        self.tczewRoutes = self.tczewTransportData.getRoutes()

    def stops(self) -> Dict[StopId, GTFSStop]:
        return {
            str(stop.id): GTFSStop(
                stopId=str(stop.id),
                stopName=stop.name,
                stopLat=stop.latitude,
                stopLon=stop.longitude,
            )
            for stop in self.tczewTransportData.getBusStops().values()
        }

    def routes(self) -> Dict[RouteId, GTFSRoute]:
        return {
            str(route.id): GTFSRoute(routeId=str(route.id), routeName=route.name)
            for route in self.tczewRoutes
        }

    def trips(self) -> Dict[TripId, GTFSTrip]:
        serviceId = "42"  # TODO
        return {
            str(variant.id): GTFSTrip(
                routeId=str(route.id),
                serviceId=serviceId,
                tripId=str(variant.id),
                shape=variant.geometry,
                busStopIds=list(map(str, variant.busStopsIds)),
            )
            for route in self.tczewRoutes
            for variant in route.variants
        }
