import geojson
from geojson import FeatureCollection, Feature, LineString

from configuration import outputDir
from data.GTFSConverter import GTFSData


class GeoJSONSaver:
    @staticmethod
    def _saveBusStopsGeoJSON(operatorGTFSData: GTFSData):
        features = []
        for stop in operatorGTFSData.stops.values():
            features.append(
                Feature(
                    geometry=stop.toPoint(),
                    properties=dict(ref=stop.stopId, name=stop.stopName),
                )
            )
        with (outputDir / "stops.geojson").open("w") as f:
            geojson.dump(FeatureCollection(features=features), f)

    @staticmethod
    def _saveBusRoutesVariantsGeoJSON(operatorGTFSData: GTFSData):
        features = []
        for trip in operatorGTFSData.trips.values():
            points = [(point.latitude, point.longitude) for point in trip.shape]
            stopNames = trip.busStopNames(operatorGTFSData.stops)[-1]
            properties = dict(
                name=f"Bus {trip.routeId}",
                variantId=trip.tripId,
                to=stopNames[-1],
            )
            properties["from"] = stopNames[0]
            features.append(
                Feature(
                    geometry=LineString(points),
                    properties=properties,
                )
            )
        with (outputDir / f"routes.geojson").open("w") as f:
            geojson.dump(FeatureCollection(features=features), f)

    def save(self, operatorGTFSData: GTFSData):
        self._saveBusStopsGeoJSON(operatorGTFSData)
        self._saveBusRoutesVariantsGeoJSON(operatorGTFSData)
