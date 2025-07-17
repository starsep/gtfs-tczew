#!/usr/bin/env -S uv run python
from data.GeoJSONSaver import GeoJSONSaver
from tczew.TczewGTFSGenerator import GTFSTczew
from starsep_utils import healthchecks


if __name__ == "__main__":
    healthchecks("/start")
    gtfs = GTFSTczew()
    gtfs.generate()
    GeoJSONSaver().save(gtfs.operatorData)
    # gtfs.showTrips()
    healthchecks()
