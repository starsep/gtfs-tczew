import geojson
from geojson import FeatureCollection, Feature, LineString

from configuration import outputDir
from data.OSMOperatorMerger import OSMOperatorMerger


class GeoJSONSaver:
    @staticmethod
    def _saveBusStopsGeoJSON(osmOperatorMerger: OSMOperatorMerger):
        features = []
        for stop in osmOperatorMerger.stopsOperator.values():
            features.append(
                Feature(
                    geometry=stop.toPoint(),
                    properties=dict(ref=stop.stopId, name=stop.stopName),
                )
            )
        with (outputDir / "stops.geojson").open("w") as f:
            geojson.dump(FeatureCollection(features=features), f)

    @staticmethod
    def _saveBusRoutesVariantsGeoJSON(osmOperatorMerger: OSMOperatorMerger):
        features = []
        for trip in osmOperatorMerger.tripsOperator.values():
            points = [(point.latitude, point.longitude) for point in trip.shape]
            stopNames = trip.busStopNames(osmOperatorMerger.stopsOperator)[-1]
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

    def save(self, osmOperatorMerger: OSMOperatorMerger):
        self._saveBusStopsGeoJSON(osmOperatorMerger)
        self._saveBusRoutesVariantsGeoJSON(osmOperatorMerger)
