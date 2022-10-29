from pathlib import Path

from diskcache import Cache

cache = Cache("cache")

outputDir = Path("output")
outputDir.mkdir(exist_ok=True)
outputGTFS = outputDir / "gtfs-tczew.zip"

OPENSTREETMAP_DOMAIN = "https://www.openstreetmap.org"
OVERPASS_URL = "https://gis-serwer.pl/osm/api/interpreter"
