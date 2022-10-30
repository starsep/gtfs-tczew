import geojson
from geojson import Feature, FeatureCollection, LineString

from configuration import outputDir
from gtfs.GTFSConverter import GTFSData


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
        for routeVariant in operatorGTFSData.routeVariants.values():
            points = [(point.latitude, point.longitude) for point in routeVariant.shape]
            stopNames = routeVariant.busStopNames(operatorGTFSData.stops)[-1]
            properties = dict(
                name=f"Bus {routeVariant.routeId}",
                variantId=routeVariant.routeVariantId,
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
