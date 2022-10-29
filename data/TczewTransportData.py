from typing import List, Dict, Tuple

from tqdm import tqdm

from data.TczewApi import TczewBusesAPI
from data.TransportData import (
    TransportData,
    BusStop,
    Route,
    RouteVariant,
    Timetable,
    LatLon,
    StopTimes,
    StopTime,
)
from log import console


class TczewTransportData(TransportData):
    def __init__(self) -> None:
        super().__init__()
        self.tczewBusesApi = TczewBusesAPI()

    def getBusStops(self, timetableId: int = 0) -> Dict[int, BusStop]:
        stops = dict()
        for stop in self.tczewBusesApi.getMapBusStops(timetableId=timetableId):
            stops[stop[0]] = BusStop(
                id=stop[0], name=stop[1], latitude=stop[5], longitude=stop[4]
            )
        return stops

    def getRoutes(self, timetableId: int = 0) -> List[Route]:
        routes = self.tczewBusesApi.getRouteList(timetableId=timetableId)
        result = []
        for i in range(len(routes) // 2):
            routeId = routes[2 * i]
            result.append(
                Route(
                    id=routeId,
                    name=routes[2 * i + 1],
                    variants=self.getRouteVariants(
                        routeId=routeId, timetableId=timetableId
                    ),
                )
            )
        return result

    def getTimetableInformation(self) -> List[Timetable]:
        return [
            Timetable(id=timetable[0], date=timetable[1])
            for timetable in self.tczewBusesApi.getTimetableInformation()
        ]

    def getRouteVariants(
        self, routeId: int, timetableId: int = 0, transits: int = 1
    ) -> List[RouteVariant]:
        tracks = self.tczewBusesApi.getTracks(
            routeId=routeId, timetableId=timetableId, transits=transits
        )
        stops = tracks[0]
        mapping = tracks[1]
        geometry = tracks[2]

        def parseCoords(coords: List[float]) -> List[LatLon]:
            result = []
            for i in range(len(coords) // 2):
                result.append(LatLon(coords[2 * i], coords[2 * i + 1]))
            return result

        legsGeometry = dict()
        for leg in geometry:
            legsGeometry[(leg[1], leg[2])] = parseCoords(leg[3])
        variants = []
        for variant in tracks[3]:
            variantRouteBusStopIds = variant[6][0]
            variantGeometry = []
            for stopPair in zip(
                variantRouteBusStopIds[:-1], variantRouteBusStopIds[1:]
            ):
                for point in legsGeometry[stopPair]:
                    variantGeometry.append(point)
            variants.append(
                RouteVariant(
                    id=variant[0],
                    direction=variant[3],
                    firstStopName=variant[4],
                    lastStopName=variant[5],
                    busStopsIds=[
                        stops[routeBusStopId][0]
                        for routeBusStopId in variantRouteBusStopIds
                    ],
                    geometry=variantGeometry,
                )
            )
        return variants

    def stopTimes(
        self, busStopIdRouteIds: List[Tuple[int, int]], timetableId: int = 0
    ) -> List[StopTimes]:
        result = []
        for (stopId, routeId) in tqdm(busStopIdRouteIds):
            timetable = self.tczewBusesApi.getBusStopTimeTable(
                timetableId=timetableId, busStopId=stopId, routeId=routeId
            )
            dayTypeToTimes = dict()
            for dayTypeTimes in timetable[3]:
                dayType = dayTypeTimes[0]
                dayTypeToTimes[dayType] = [
                    StopTime(tripId=x[0], time=x[2]) for x in dayTypeTimes[4]
                ]
            result.append(
                StopTimes(stopId=stopId, routeId=routeId, dayTypeToTimes=dayTypeToTimes)
            )
        return result
