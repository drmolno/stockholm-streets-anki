"""Build water polygons (lakes, bays and the sea) from the raw shoreline data."""
import json

from shapely import STRtree
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import polygonize, unary_union

from . import config


def _line(element):
    return LineString([(p["lon"], p["lat"]) for p in element["geometry"]])


def _is_water(tags):
    return tags.get("natural") == "water" or tags.get("waterway") == "riverbank"


def _relation_polygon(relation):
    outer, inner = [], []
    for member in relation["members"]:
        if member["type"] != "way" or "geometry" not in member:
            continue
        line = LineString([(p["lon"], p["lat"]) for p in member["geometry"]])
        (inner if member["role"] == "inner" else outer).append(line)
    shape = unary_union(list(polygonize(unary_union(outer))))
    if inner:
        shape = shape.difference(unary_union(list(polygonize(unary_union(inner)))))
    return shape


def _sea_polygon(coastlines, bbox):
    """OSM coastline ways have land on their left, so a face of the
    coastline + bbox arrangement is sea if it lies right of its nearest coastline."""
    if not coastlines:
        return Polygon()
    frame = bbox.exterior
    faces = polygonize(unary_union(coastlines + [frame]))
    tree = STRtree(coastlines)
    sea = []
    for face in faces:
        if not face.within(bbox.buffer(1e-9)):
            continue
        point = face.representative_point()
        line = coastlines[tree.nearest(point)]
        # direction of the coastline at its closest point
        d = line.project(point)
        a = line.interpolate(max(d - 1e-5, 0))
        b = line.interpolate(min(d + 1e-5, line.length))
        cross = (b.x - a.x) * (point.y - a.y) - (b.y - a.y) * (point.x - a.x)
        if cross < 0:
            sea.append(face)
    return unary_union(sea)


def load_water():
    south, west, north, east = config.CONTEXT_BBOX
    bbox = box(west, south, east, north)
    elements = json.loads(config.WATER_FILE.read_text(encoding="utf-8"))["elements"]

    shapes, coastlines = [], []
    for e in elements:
        tags = e.get("tags", {})
        if e["type"] == "way" and tags.get("natural") == "coastline":
            coastlines.append(_line(e))
        elif e["type"] == "way" and _is_water(tags) and len(e["geometry"]) >= 4:
            coords = [(p["lon"], p["lat"]) for p in e["geometry"]]
            if coords[0] == coords[-1]:
                shapes.append(Polygon(coords).buffer(0))
        elif e["type"] == "relation" and _is_water(tags):
            shapes.append(_relation_polygon(e))

    shapes.append(_sea_polygon(coastlines, bbox))
    return unary_union(shapes).intersection(bbox)
