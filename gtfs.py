from io import StringIO
from zipfile import ZipFile

from configuration import outputDir, outputGTFS
from validator import Validator


class GTFS:
    def __init__(self):
        self.validator = Validator()

    @staticmethod
    def agencyInfo() -> str:
        timezone = "CEST"  # TODO: summer/winter time?
        agencyResult = StringIO()
        agencyResult.write("agency_name,agency_url,agency_timezone,agency_lang\n")
        agencyResult.write(
            f"Przewozy Autobusowe Gryf sp. z o.o. sp. k.,http://rozklady.tczew.pl/,{timezone},pl"
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
        routesResult.write("route_id,route_short_name,route_type\n")
        routeType = 3  # Bus. Used for short- and long-distance bus routes.
        for route in self.validator.validatedRoutes():
            routesResult.write(f"{route.routeId},{route.routeName},{routeType}\n")
        return routesResult.getvalue()

    def generate(self):
        with ZipFile(outputGTFS, "w") as zipOutput:
            zipOutput.writestr("agency.txt", self.agencyInfo())
            zipOutput.writestr("stops.txt", self.stops())
            zipOutput.writestr("routes.txt", self.routes())


if __name__ == "__main__":
    GTFS().generate()
