from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "output"
IMAGE_DIR = OUTPUT_DIR / "images"

STREETS_FILE = DATA_DIR / "streets.json"
DISTRICTS_FILE = DATA_DIR / "districts.json"
AREAS_FILE = DATA_DIR / "areas.json"
BACKGROUND_FILE = DATA_DIR / "background.json"
WATER_FILE = DATA_DIR / "water.json"
PLACES_FILE = DATA_DIR / "places.json"
DECK_FILE = OUTPUT_DIR / "stockholm_streets.apkg"

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
# overpass-api.de rejects the default python-requests User-Agent with 406
USER_AGENT = "stockholm-streets-anki/0.1 (personal learning project)"

# "Stockholms innerstad" isn't an area in OSM; the inner city is the union of
# these stadsdelsområden (OSM relation ids). For the whole municipality use
# 398021 (Stockholms kommun).
AREA_RELATIONS = {
    16404316: "Norra innerstaden",  # Norrmalm + Östermalm
    5689375: "Kungsholmen",
    5691336: "Södermalm",
}

# Surroundings drawn for context (south, west, north, east). Covers the inner
# city plus a margin so maps of edge streets don't end abruptly.
CONTEXT_BBOX = (59.27, 17.92, 59.39, 18.18)

# Proper roads. Regions are computed from streets with one of these types only,
# so adding more path types to STREET_TYPES doesn't renumber the regions.
ROAD_TYPES = {
    "motorway", "trunk", "primary", "secondary", "tertiary", "unclassified",
    "residential", "living_street", "pedestrian", "road", "busway",
}
# A name counts as a street if at least one of its ways has one of these types.
# Paths and stairs are included for names like Jeppes trappor or Karl XII:s Torg.
STREET_TYPES = ROAD_TYPES | {"steps", "footway", "service", "cycleway", "path", "bridleway"}
# Ways of these types are never drawn as part of a street.
IGNORED_TYPES = {"proposed", "construction", "platform", "elevator"}
