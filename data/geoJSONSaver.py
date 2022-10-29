import geojson
from geojson import FeatureCollection, Feature, LineString

from configuration import outputDir
from data.transportData import TransportData


class GeoJSONSaver:
    @staticmethod
    def saveBusStopsGeoJSON(transportData: TransportData):
        stops = transportData.getBusStops().values()
        features = []
        for stop in stops:
            features.append(
                Feature(
                    geometry=stop.toPoint(),
                    properties=dict(ref=stop.id, name=stop.name),
                )
            )
        with (outputDir / "stops.geojson").open("w") as f:
            geojson.dump(FeatureCollection(features=features), f)

    @staticmethod
    def saveBusRoutesVariantsGeoJSON(transportData: TransportData):
        features = []
        for route in transportData.getRoutes():
            for variant in transportData.getRouteVariants(routeId=route.id):
                points = [
                    (point.latitude, point.longitude) for point in variant.geometry
                ]
                properties = dict(
                    name=f"Bus {route.name}",
                    variantId=variant.id,
                    to=variant.lastStopName,
                )
                properties["from"] = variant.firstStopName
                features.append(
                    Feature(
                        geometry=LineString(points),
                        properties=properties,
                    )
                )
        with (outputDir / f"routes.geojson").open("w") as f:
            geojson.dump(FeatureCollection(features=features), f)

    def save(self, transportData: TransportData):
        self.saveBusStopsGeoJSON(transportData)
        self.saveBusRoutesVariantsGeoJSON(transportData)

