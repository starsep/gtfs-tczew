from io import StringIO
from zipfile import ZipFile

from rich.table import Table

from configuration import outputDir, outputGTFS
from log import console
from validator import Validator


class GTFS:
    def __init__(self):
        self.validator = Validator()

    @staticmethod
    def agencyInfo() -> str:
        agencyResult = StringIO()
        agencyResult.write("agency_name,agency_url,agency_timezone,agency_lang\n")
        agencyResult.write(
            f"Przewozy Autobusowe Gryf sp. z o.o. sp. k.,http://rozklady.tczew.pl/,Europe/Warsaw,pl"
        )
        return agencyResult.getvalue()

    def stops(self) -> str:
        stopsResult = StringIO()
        stopsResult.write("stop_id,stop_name,stop_lat,stop_lon\n")
        for stop in self.validator.validatedStops():
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

    def generate(self):
        with ZipFile(outputGTFS, "w") as zipOutput:
            zipOutput.writestr("agency.txt", self.agencyInfo())
            zipOutput.writestr("stops.txt", self.stops())
            zipOutput.writestr("routes.txt", self.routes())
            zipOutput.writestr("trips.txt", self.trips())

    def generateGeoJSONs(self):
        self.validator.transportData.saveBusRoutesVariantsGeoJSON()

    def showTrips(self):
        stopIdToName = {
            stop.stopId: stop.stopName for stop in self.validator.validatedStops()
        }
        routeIdToName = {
            route.routeId: route.routeName for route in self.validator.validatedRoutes()
        }
        for trip in self.validator.validatedTrips():
            table = Table(title=f"Route {routeIdToName[trip.routeId]}, trip {trip.tripId}")

            table.add_column("ref")
            table.add_column("name")

            for stopId in trip.busStopIds:
                table.add_row(stopId, stopIdToName[stopId])

            console.print(" or ".join([f"ref={ref}" for ref in trip.busStopIds]))
            console.print(table)


if __name__ == "__main__":
    gtfs = GTFS()
    gtfs.generate()
    gtfs.generateGeoJSONs()
    gtfs.showTrips()
