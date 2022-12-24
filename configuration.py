from datetime import datetime
from pathlib import Path

import pytz
from diskcache import Cache

cache = Cache("cache")

outputDir = Path("output")
outputDir.mkdir(exist_ok=True)
outputGTFS = outputDir / "gtfs-tczew.zip"

OPENSTREETMAP_DOMAIN = "https://www.openstreetmap.org"
OVERPASS_URL = None # "https://gis-serwer.pl/osm/api/interpreter"

TIMEZONE = "Europe/Warsaw"
timezone = pytz.timezone(TIMEZONE)

startTimeUTC = datetime.now(pytz.UTC)
startTime = datetime.now(timezone)
feedVersion = startTime.date().strftime("%Y%m%d")
