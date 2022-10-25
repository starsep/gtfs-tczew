from dataclasses import dataclass
from pathlib import Path
from typing import List

import geojson
import httpx
from diskcache import Cache
from geojson import Feature, FeatureCollection, Point

cache = Cache("cache")
output = Path("output")
output.mkdir(exist_ok=True)
DOMAIN = "http://rozklady.tczew.pl"


@dataclass
class BusStop:
    ref: str
    name: str
    latitude: float
    longitude: float


class GTFSTczew(object):
    @cache.memoize()
    def getBusStops(self) -> List[BusStop]:
        url = f"{DOMAIN}/Home/GetMapBusStopList?q=&ttId=0"
        response = httpx.get(url)
        stops = []
        for stop in response.json():
            stops.append(
                BusStop(ref=stop[0], name=stop[1], latitude=stop[5], longitude=stop[4])
            )
        return stops

    def saveBusStopsGeoJSON(self):
        stops = self.getBusStops()
        features = []
        for stop in stops:
            features.append(Feature(geometry=Point((stop.longitude, stop.latitude)), properties=dict(ref=stop.ref, name=stop.name)))
        with (output / "stops.geojson").open("w") as f:
            geojson.dump(FeatureCollection(features=features), f)


GTFSTczew().saveBusStopsGeoJSON()
