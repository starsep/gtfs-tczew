from typing import Dict, List, Tuple, Set

from configuration import feedVersion, startTimeUTC
from gtfs.GTFSConverter import (
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
    StopSequence,
)
from log import printError
from tczew.TczewTransportData import TczewTransportData
from data.TransportData import StopTime

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

    def routeVariants(
        self, stops: Dict[StopId, GTFSStop], routes: Dict[RouteId, GTFSRoute]
    ) -> Dict[RouteVariantId, GTFSRouteVariant]:
        return {
            str(variant.id): GTFSRouteVariant(
                routeId=str(route.id),
                routeVariantId=str(variant.id),
                shapeId=str(variant.id),
                shape=variant.geometry,
                busStopIds=list(map(str, variant.busStopsIds)),
                routeVariantName=str(route.name),
            )
            for route in self.tczewRoutes
            for variant in route.variants
        }

    def trips(
        self,
        stops: Dict[StopId, GTFSStop],
        services: List[GTFSService],
        routeVariants: Dict[RouteVariantId, GTFSRouteVariant],
    ) -> Dict[TripId, GTFSTrip]:
        result = dict()
        for variantId, routeVariant in routeVariants.items():
            startBusStopId = routeVariant.busStopIds[0]
            busStopRouteId = [(int(startBusStopId), int(routeVariant.routeId))]
            for stopTimes in self.tczewTransportData.stopTimes(busStopRouteId):
                for dayType, times in stopTimes.dayTypeToTimes.items():
                    serviceId = DAY_TYPE_TO_SERVICE[dayType]
                    for time in times:
                        if str(time.routeVariantId) == routeVariant.routeVariantId:
                            tripStartTime = time.minutes
                            tripId = time.tripId
                            result[tripId] = GTFSTrip(
                                tripId=time.tripId,
                                routeId=routeVariant.routeId,
                                routeVariantId=routeVariant.routeVariantId,
                                shape=routeVariant.shape,
                                busStopIds=routeVariant.busStopIds,
                                shapeId=routeVariant.shapeId,
                                tripStartMinutes=tripStartTime,
                                serviceId=serviceId,
                                routeVariantName=routeVariant.routeVariantName,
                            )
        return result

    def shapes(
        self, routeVariants: Dict[RouteVariantId, GTFSRouteVariant]
    ) -> List[GTFSShape]:
        return shapesFromRouteVariants(routeVariants)

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
    def parseMinutesTimezone(minutes: int) -> str:
        hour, minute = minutes // 60, minutes % 60
        return (
            startTimeUTC.replace(hour=hour + 2, minute=minute, second=0)
            # TODO: fix timezone issue? currently constant +2 hours
            # .astimezone(timezone)
            .strftime("%H:%M:%S")
        )

    @staticmethod
    def _busStopRouteIds(
        routes: Dict[RouteId, GTFSRoute],
        routeVariants: Dict[RouteVariantId, GTFSRouteVariant],
    ) -> List[Tuple[int, int]]:
        routeIdToBusStopIds = {routeId: set() for routeId in routes.keys()}
        for variant in routeVariants.values():
            for stopId in variant.busStopIds:
                routeIdToBusStopIds[variant.routeId].add(stopId)
        return [
            (int(busStopId), int(routeId))
            for routeId in routeIdToBusStopIds
            for busStopId in routeIdToBusStopIds[routeId]
        ]

    @staticmethod
    def _groupTimesByVariant(
        times: List[StopTime],
    ) -> Dict[RouteVariantId, List[StopTime]]:
        timesGroupedByVariant: Dict[RouteVariantId, List[StopTime]] = dict()
        for time in times:
            if time.routeVariantId not in timesGroupedByVariant:
                timesGroupedByVariant[time.routeVariantId] = []
            timesGroupedByVariant[time.routeVariantId].append(time)
        return timesGroupedByVariant

    @staticmethod
    def _oneBeforeLastStopTimes(
        stopTimes: List[GTFSStopTime], trips: Dict[TripId, GTFSTrip]
    ) -> List[GTFSStopTime]:
        lookingFor: Set[Tuple[StopId, TripId, StopSequence]] = set()
        for trip in trips.values():
            oneBeforeLast = trip.busStopIds[-2]
            lookingFor.add((oneBeforeLast, trip.tripId, len(trip.busStopIds) - 2))
        result = []
        for stopTime in stopTimes:
            key = (stopTime.stopId, stopTime.tripId, stopTime.stopSequence)
            if key in lookingFor:
                result.append(stopTime)
        return result

    def _addLastStopTimes(
        self, stopTimes: List[GTFSStopTime], trips: Dict[TripId, GTFSTrip]
    ) -> List[GTFSStopTime]:
        lastLegTimes = self.tczewTransportData.lastLegTimes()
        oneBeforeLastStopTimes = self._oneBeforeLastStopTimes(stopTimes, trips)
        missing: Set[Tuple[StopId, StopId]] = set()
        for trip in trips.values():
            prev = trip.busStopIds[-2]
            last = trip.busStopIds[-1]
            key = (prev, last)
            if key not in lastLegTimes:
                missing.add(key)
                continue
            stopSequence = len(trip.busStopIds) - 1
            prevStopTime = next(
                filter(
                    lambda stopTime: stopTime.stopId == prev
                    and stopTime.tripId == trip.tripId
                    and stopTime.stopSequence == stopSequence - 1,
                    oneBeforeLastStopTimes,
                )
            )
            prevMinutes = prevStopTime.minutes
            lastLegMinutes = lastLegTimes[key]
            parsedTime = self.parseMinutesTimezone(prevMinutes + lastLegMinutes)
            stopTimes.append(
                GTFSStopTime(
                    tripId=trip.tripId,
                    minutes=prevMinutes + lastLegMinutes,
                    arrivalTime=parsedTime,
                    departureTime=parsedTime,
                    stopId=last,
                    stopSequence=len(trip.busStopIds) - 1,
                )
            )
        if len(missing) > 0:
            printError(f"Missing last leg times for bus stops: {missing}")
        return stopTimes

    def stopTimes(
        self,
        routes: Dict[RouteId, GTFSRoute],
        routeVariants: Dict[RouteVariantId, GTFSRouteVariant],
        trips: Dict[TripId, GTFSTrip],
    ) -> List[GTFSStopTime]:
        busStopRouteIds = self._busStopRouteIds(routes, routeVariants)
        result = []
        for stopTimes in self.tczewTransportData.stopTimes(busStopRouteIds):
            for dayType, times in stopTimes.dayTypeToTimes.items():
                timesGroupedByVariant = self._groupTimesByVariant(times)
                for routeVariantId, timesGroup in timesGroupedByVariant.items():
                    for index, time in enumerate(timesGroup):
                        parsedTime = self.parseMinutesTimezone(time.minutes)
                        stopId = str(stopTimes.stopId)
                        stopSequence = routeVariants[
                            str(time.routeVariantId)
                        ].busStopIds.index(stopId)
                        tripId = time.tripId
                        result.append(
                            GTFSStopTime(
                                tripId=tripId,
                                minutes=time.minutes,
                                arrivalTime=parsedTime,
                                departureTime=parsedTime,
                                stopId=stopId,
                                stopSequence=stopSequence,
                            )
                        )
        return self._addLastStopTimes(result, trips)
