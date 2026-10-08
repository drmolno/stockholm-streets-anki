"""Group the raw OSM ways into one Street per name."""
import json
from collections import Counter, defaultdict
from dataclasses import dataclass, field

from shapely.geometry import LineString, MultiLineString, Point
from shapely.ops import polygonize, unary_union

from . import config


@dataclass
class Street:
    name: str
    highway_types: set
    lines: list = field(default_factory=list)  # [(LineString, is_tunnel)]
    districts: list = field(default_factory=list)
    regions: list = field(default_factory=list)  # region numbers, see regions.py

    @property
    def geometry(self):
        return MultiLineString([line for line, _ in self.lines])

    @property
    def slug(self):
        return "".join(c if c.isalnum() else "_" for c in self.name.lower())


def is_tunnel(tags):
    return tags.get("tunnel") not in (None, "no") or tags.get("layer", "0").startswith("-")


def _line(element):
    return LineString([(p["lon"], p["lat"]) for p in element["geometry"]])


def _boundary_polygons(path):
    """{name: Polygon} for the boundary relations in an Overpass file."""
    polygons = {}
    for rel in json.loads(path.read_text(encoding="utf-8"))["elements"]:
        outer = [
            LineString([(p["lon"], p["lat"]) for p in m["geometry"]])
            for m in rel["members"]
            if m["type"] == "way" and m["role"] == "outer" and "geometry" in m
        ]
        polygons[rel["tags"]["name"]] = unary_union(list(polygonize(unary_union(outer))))
    return polygons


def load_districts():
    """{name: Polygon} for the admin_level 10 neighbourhoods."""
    return _boundary_polygons(config.DISTRICTS_FILE)


def load_inner_city():
    """The whole area as one polygon (union of the stadsdelsområden)."""
    return unary_union(list(_boundary_polygons(config.AREAS_FILE).values()))


def load_places():
    """[(name, Point)] for named suburb/quarter/neighbourhood nodes."""
    elements = json.loads(config.PLACES_FILE.read_text(encoding="utf-8"))["elements"]
    return [(e["tags"]["name"], Point(e["lon"], e["lat"])) for e in elements]


def _assign_districts(street, districts, places, min_share=0.1):
    geometry = street.geometry
    shares = []
    for name, polygon in districts.items():
        share = geometry.intersection(polygon).length / geometry.length
        if share >= min_share:
            shares.append((share, name))
    street.districts = [name for _, name in sorted(shares, reverse=True)]
    if not street.districts:
        # e.g. Hammarby sjöstad has no admin_level 10 district in OSM
        centre = geometry.centroid
        street.districts = [min(places, key=lambda place: place[1].distance(centre))[0]]


def load_streets():
    elements = json.loads(config.STREETS_FILE.read_text(encoding="utf-8"))["elements"]
    # group case-insensitively: OSM has both "Sergels Torg" and "Sergels torg"
    by_name = defaultdict(list)
    for e in elements:
        if e["tags"]["highway"] not in config.IGNORED_TYPES:
            by_name[e["tags"]["name"].casefold()].append(e)

    districts = load_districts()
    places = load_places()
    streets = []
    for ways in by_name.values():
        types = {w["tags"]["highway"] for w in ways}
        # underscores are OSM typos ("Spanska_Trappan")
        name = Counter(w["tags"]["name"] for w in ways).most_common(1)[0][0].replace("_", " ")
        # bare numbers like "1", "5" are labels on service roads, not street names
        if not types & config.STREET_TYPES or name.isdigit():
            continue
        street = Street(name, types, [(_line(w), is_tunnel(w["tags"])) for w in ways])
        _assign_districts(street, districts, places)
        streets.append(street)
    return sorted(streets, key=lambda s: s.name)
