from typing import List, Dict, Tuple

import pytz

from configuration import feedVersion, timezone, startTime, startTimeUTC
from data.GTFSConverter import (
    GTFSConverter,
    GTFSRoute,
    GTFSStop,
    StopId,
    RouteId,
    GTFSTrip,
    TripId,
    GTFSShape,
    shapesFromTrips,
    GTFSService,
    GTFSStopTime,
    GTFSTripWithService,
    tripForEveryService,
)
from data.TczewTransportData import TczewTransportData

DAY_TYPE_TO_SERVICE = dict(PW="WD", SB="SA", ND="SU")


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

    def trips(self, stops: Dict[StopId, GTFSStop]) -> Dict[TripId, GTFSTrip]:
        return {
            str(variant.id): GTFSTrip(
                routeId=str(route.id),
                tripId=str(variant.id),
                shapeId=str(variant.id),
                shape=variant.geometry,
                busStopIds=list(map(str, variant.busStopsIds)),
            )
            for route in self.tczewRoutes
            for variant in route.variants
        }

    def tripsWithService(
        self, trips: Dict[TripId, GTFSTrip], services: List[GTFSService]
    ) -> List[GTFSTripWithService]:
        return tripForEveryService(trips, services)

    def shapes(self, trips: Dict[TripId, GTFSTrip]) -> List[GTFSShape]:
        return shapesFromTrips(trips)

    def services(self) -> List[GTFSService]:
        serviceWorkDay = GTFSService(
            serviceId="WD",
            monday=True,
            tuesday=True,
            wednesday=True,
            thursday=True,
            friday=True,
            saturday=False,
            sunday=False,
            startDate=feedVersion,
            endDate="20300101",
        )
        serviceSaturday = GTFSService(
            serviceId="SA",
            monday=False,
            tuesday=False,
            wednesday=False,
            thursday=False,
            friday=False,
            saturday=True,
            sunday=False,
            startDate=feedVersion,
            endDate="20300101",
        )
        serviceSunday = GTFSService(
            serviceId="SU",
            monday=False,
            tuesday=False,
            wednesday=False,
            thursday=False,
            friday=False,
            saturday=False,
            sunday=True,
            startDate=feedVersion,
            endDate="20300101",
        )
        return [
            serviceWorkDay,
            serviceSaturday,
            serviceSunday
            # for index, timetable in enumerate(self.tczewTransportData.getTimetableInformation())
            # TODO: handle multiple timetables
        ]

    @staticmethod
    def parseTime(time: str) -> Tuple[int, int]:
        minuteRaw = int(time[-2:])
        minute = minuteRaw % 60
        hour = int(time[: len(time) - 2]) + minuteRaw // 60
        return hour, minute

    def parseTimeTimezone(self, time: str) -> str:
        hour, minute = self.parseTime(time)
        return (
            startTimeUTC.replace(hour=hour, minute=minute, second=0)
            .astimezone(timezone)
            .strftime("%H:%M:%S")
        )

    def stopTimes(self, trips: Dict[TripId, GTFSTrip]) -> List[GTFSStopTime]:
        busStopRouteIds = [
            (int(busStopId), int(trip.routeId))
            for trip in trips.values()
            for busStopId in trip.busStopIds
        ]
        result = []
        for stopTimes in self.tczewTransportData.stopTimes(busStopRouteIds):
            for dayType, times in stopTimes.dayTypeToTimes.items():
                tripSuffix = DAY_TYPE_TO_SERVICE[dayType]
                for time in times:
                    parsedTime = self.parseTimeTimezone(time.time)
                    stopId = str(stopTimes.stopId)
                    stopSequence = trips[str(time.tripId)].busStopIds.index(stopId)
                    result.append(
                        GTFSStopTime(
                            tripId=f"{time.tripId}-{tripSuffix}",
                            arrivalTime=parsedTime,
                            departureTime=parsedTime,
                            stopId=stopId,
                            stopSequence=stopSequence,
                        )
                    )
        return result
