from data.GeoJSONSaver import GeoJSONSaver
from gtfs.gtfsTczew import GTFSTczew

if __name__ == "__main__":
    gtfs = GTFSTczew()
    gtfs.generate()
    GeoJSONSaver().save(gtfs.validator.transportData)
    # gtfs.showTrips()
