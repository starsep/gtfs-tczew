#!/usr/bin/env python3
from data.GeoJSONSaver import GeoJSONSaver
from tczew.TczewGTFSGenerator import GTFSTczew

if __name__ == "__main__":
    gtfs = GTFSTczew()
    gtfs.generate()
    GeoJSONSaver().save(gtfs.operatorData)
    # gtfs.showTrips()
