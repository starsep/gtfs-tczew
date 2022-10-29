from io import StringIO

from rich.table import Table

from data.OSMOverpass import OSMOverpass
from data.TczewTransportData import TczewTransportData
from gtfs.gtfsGenerator import GTFSGenerator
from log import console
from data.OSMOperatorMerger import Validator, OSMOperatorMerger


class GTFSTczew(GTFSGenerator):
    def __init__(self):
        self.validator = OSMOperatorMerger(
            osmSource=OSMOverpass(mainRelationId=12625881),
            transportData=TczewTransportData(),
        )

    def agencyInfo(self) -> str:
        agencyResult = StringIO()
        agencyResult.write("agency_name,agency_url,agency_timezone,agency_lang\n")
        agencyResult.write(
            f"Przewozy Autobusowe Gryf sp. z o.o. sp. k.,http://rozklady.tczew.pl/,Europe/Warsaw,pl"
        )
        return agencyResult.getvalue()

    def stops(self) -> str:
        stopsResult = StringIO()
        stopsResult.write("stop_id,stop_name,stop_lat,stop_lon\n")
        for stop in self.validator.validateStops():
            stopsResult.write(
                f"{stop.stopId},{stop.stopName},{stop.stopLat},{stop.stopLon}\n"
            )
        return stopsResult.getvalue()

    def routes(self) -> str:
        routesResult = StringIO()
        routesResult.write("route_id,route_short_name,route_long_name,route_type\n")
        routeType = 3  # Bus. Used for short- and long-distance bus routes.
        for route in self.validator.validatedRoutes():
            routesResult.write(
                f"{route.routeId},{route.routeName},{route.routeName},{routeType}\n"
            )
        return routesResult.getvalue()

    def trips(self) -> str:
        tripsResult = StringIO()
        tripsResult.write("route_id,service_id,trip_id\n")
        for trip in self.validator.validatedTrips():
            tripsResult.write(f"{trip.routeId},{trip.serviceId},{trip.tripId}\n")
        return tripsResult.getvalue()

    def showTrips(self):
        stopIdToName = {
            stop.stopId: stop.stopName for stop in self.validator.validateStops()
        }
        routeIdToName = {
            route.routeId: route.routeName for route in self.validator.validatedRoutes()
        }
        for trip in self.validator.validatedTrips():
            print(routeIdToName)
            table = Table(
                title=f"Route {routeIdToName[trip.routeId]}, trip {trip.tripId}"
            )

            table.add_column("ref")
            table.add_column("name")

            for stopId in trip.busStopIds:
                table.add_row(stopId, stopIdToName[stopId])

            console.print(" or ".join([f"ref={ref}" for ref in trip.busStopIds]))
            console.print(table)
