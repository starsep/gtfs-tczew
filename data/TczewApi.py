import httpx

from configuration import cache

DOMAIN = "http://rozklady.tczew.pl"


class TczewBusesAPI:
    @cache.memoize()
    def getMapBusStops(self, timetableId: int):
        url = f"{DOMAIN}/Home/GetMapBusStopList?q=&ttId={timetableId}"
        return httpx.get(url).json()

    @cache.memoize()
    def getRouteList(self, timetableId: int):
        url = f"{DOMAIN}/Home/GetRouteList?ttId={timetableId}"
        return httpx.get(url).json()[0]

    @cache.memoize()
    def getTimetableInformation(self):
        url = f"{DOMAIN}/Home/GetTimetableInformation"
        return httpx.get(url).json()

    @cache.memoize()
    def getTracks(self, routeId: int, timetableId: int, transits: int):
        url = f"{DOMAIN}/Home/GetTracks?routeId={routeId}&ttId={timetableId}&transits={transits}"
        return httpx.get(url).json()

    @cache.memoize()
    def getBusStopDetails(self, timetableId: int, busStopId: int):
        url = (
            f"{DOMAIN}/Home/GetBusStopDetails?ttId={timetableId}&nBusStopId={busStopId}"
        )
        return httpx.get(url).json()

    @cache.memoize()
    def getBusStopRouteList(self, timetableId: int, busStopId: int):
        url = f"{DOMAIN}/Home/GetBusStopRouteList?id={busStopId}&ttId={timetableId}"
        return httpx.get(url).json()

    @cache.memoize()
    def getBusStopTimeTable(self, timetableId: int, busStopId: int, routeId: int):
        url = f"{DOMAIN}/Home/GetBusStopTimeTable?busStopId={busStopId}&routeId={routeId}&ttId={timetableId}"
        return httpx.get(url).json()

    @cache.memoize()
    def getRouteVariant(self, routeVariantId: int, timetableId: int):
        url = f"{DOMAIN}/Home/GetRouteVariant?id={routeVariantId}&ttId={timetableId}"
        return httpx.get(url).json()

    @cache.memoize()
    def getNextDepartures(self, busStopId: int):
        url = f"{DOMAIN}/Home/GetNextDepartues?busStopId={busStopId}"
        return httpx.get(url).json()
