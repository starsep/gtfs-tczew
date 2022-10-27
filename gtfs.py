from osm import OSM
from transportData import TransportData

if __name__ == "__main__":
    transportData = TransportData()
    routes = transportData.getRoutes()
    osmData = OSM().getMainRelation()
