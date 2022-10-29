from io import StringIO

from rich.table import Table

from data.OSMConverter import OSMConverter
from data.OSMOperatorMerger import OSMOperatorMerger
from data.OSMOverpass import OSMOverpass
from data.TczewGTFSConverter import TczewGTFSConverter
from data.TczewTransportData import TczewTransportData
from gtfs.gtfsGenerator import GTFSGenerator
from log import console


class GTFSTczew(GTFSGenerator):
    def __init__(self):
        self.gtfsConverter = OSMOperatorMerger(
            osmConverter=OSMConverter(OSMOverpass(mainRelationId=12625881)),
            operatorConverter=TczewGTFSConverter(TczewTransportData()),
        )

    def agencyInfo(self) -> str:
        agencyResult = StringIO()
        agencyResult.write("agency_name,agency_url,agency_timezone,agency_lang\n")
        agencyResult.write(
            f"Przewozy Autobusowe Gryf sp. z o.o. sp. k.,http://rozklady.tczew.pl/,Europe/Warsaw,pl"
        )
        return agencyResult.getvalue()

    def stopsString(self) -> str:
        stopsResult = StringIO()
        stopsResult.write("stop_id,stop_name,stop_lat,stop_lon\n")
        for stop in self.gtfsConverter.stops().values():
            stopsResult.write(
                f"{stop.stopId},{stop.stopName},{stop.stopLat},{stop.stopLon}\n"
            )
        return stopsResult.getvalue()

    def routesString(self) -> str:
        routesResult = StringIO()
        routesResult.write("route_id,route_short_name,route_long_name,route_type\n")
        routeType = 3  # Bus. Used for short- and long-distance bus routes.
        for route in self.gtfsConverter.routes().values():
            routesResult.write(
                f"{route.routeId},{route.routeName},{route.routeName},{routeType}\n"
            )
        return routesResult.getvalue()

    def tripsString(self) -> str:
        tripsResult = StringIO()
        tripsResult.write("route_id,service_id,trip_id\n")
        for trip in self.gtfsConverter.trips().values():
            tripsResult.write(f"{trip.routeId},{trip.serviceId},{trip.tripId}\n")
        return tripsResult.getvalue()

    def showTrips(self):
        stopIdToName = {
            stop.stopId: stop.stopName for stop in self.gtfsConverter.stops().values()
        }
        routeIdToName = {
            route.routeId: route.routeName
            for route in self.gtfsConverter.routes().values()
        }
        for trip in self.gtfsConverter.trips().values():
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
