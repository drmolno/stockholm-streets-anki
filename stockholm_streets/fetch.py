"""Download the raw OSM data from Overpass into data/."""
import json
import time

import requests

from . import config


def run_query(query, retries=4):
    headers = {"User-Agent": config.USER_AGENT}
    for attempt in range(retries):
        response = requests.post(config.OVERPASS_URL, data={"data": query}, headers=headers, timeout=300)
        if response.status_code in (429, 504):  # rate limited / server busy
            time.sleep(15 * (attempt + 1))
            continue
        response.raise_for_status()
        return response.json()
    response.raise_for_status()


def _areas():
    # Overpass area ids are relation id + 3600000000
    lines = "\n".join(f"  area(id:{3600000000 + rel});" for rel in config.AREA_RELATIONS)
    return f"(\n{lines}\n)->.a;"


def _bbox():
    return ",".join(str(c) for c in config.CONTEXT_BBOX)


QUERIES = {
    config.STREETS_FILE: lambda: f"""
[out:json][timeout:180];
{_areas()}
way["highway"]["name"](area.a);
out tags geom;
""",
    # Outline of the whole area (the stadsdelsområden themselves)
    config.AREAS_FILE: lambda: f"""
[out:json][timeout:180];
rel(id:{",".join(str(r) for r in config.AREA_RELATIONS)});
out geom;
""",
    # Neighbourhoods (Vasastaden, Gamla stan, ...) shown on the answer side
    config.DISTRICTS_FILE: lambda: f"""
[out:json][timeout:180];
{_areas()}
rel["boundary"="administrative"]["admin_level"="10"](area.a);
out geom;
""",
    # Named places, fallback for streets outside every admin_level 10 district
    config.PLACES_FILE: lambda: f"""
[out:json][timeout:180];
{_areas()}
node["place"~"^(suburb|quarter|neighbourhood)$"]["name"](area.a);
out;
""",
    config.BACKGROUND_FILE: lambda: f"""
[out:json][timeout:180];
way["highway"~"^(motorway|trunk|primary|secondary|tertiary|unclassified|residential|living_street|pedestrian|road)$"]({_bbox()});
out tags geom;
""",
    # Shorelines: sea coastline plus the outlines of lakes and bays
    config.WATER_FILE: lambda: f"""
[out:json][timeout:180];
(
  way["natural"="coastline"]({_bbox()});
  way["natural"="water"]({_bbox()});
  rel["natural"="water"]({_bbox()});
  way(r)({_bbox()});
);
out geom;
""",
}


def fetch_all(force=False):
    config.DATA_DIR.mkdir(exist_ok=True)
    for path, make_query in QUERIES.items():
        if path.exists() and not force:
            print(f"{path.name}: already downloaded (use --force to refetch)")
            continue
        print(f"{path.name}: downloading...", flush=True)
        data = run_query(make_query())
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        print(f"{path.name}: {len(data['elements'])} elements")
        time.sleep(5)  # be nice to the public server
