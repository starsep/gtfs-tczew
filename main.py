from data.GeoJSONSaver import GeoJSONSaver
from tczew.GTFSTczew import GTFSTczew

if __name__ == "__main__":
    gtfs = GTFSTczew()
    gtfs.generate()
    GeoJSONSaver().save(gtfs.operatorData)
    # gtfs.showTrips()
