"""Divide the inner city into numbered regions with roughly equal street counts.

Land is first split along the water (Södermalm, Kungsholmen, Gamla stan, ...),
then each land mass is cut into Voronoi cells around k-means clusters of the
street centres, so dense areas get small regions and sparse ones big regions.
"""
from dataclasses import dataclass

import numpy as np
from shapely import voronoi_polygons
from shapely.geometry import MultiPoint
from shapely.ops import unary_union

from . import config
from .render import KX

TARGET_REGIONS = 20
# How regions are shared out between land masses: by street count, by area, or a
# mix. Pure street count splits tiny dense Gamla stan; pure area ignores density.
AREA_WEIGHT = 0.4
MIN_STREETS_PER_LANDMASS = 25  # smaller islands are merged into a neighbour
MIN_SHARE = 0.2  # a street belongs to every region holding this share of its length


@dataclass
class Region:
    number: int
    polygon: object


def _kmeans(points, k, seed=0, iterations=100):
    rng = np.random.default_rng(seed)
    # k-means++ initialisation
    centres = [points[rng.integers(len(points))]]
    for _ in range(1, k):
        d2 = np.min([((points - c) ** 2).sum(axis=1) for c in centres], axis=0)
        centres.append(points[rng.choice(len(points), p=d2 / d2.sum())])
    centres = np.array(centres)
    for _ in range(iterations):
        labels = np.argmin(((points[:, None, :] - centres[None]) ** 2).sum(axis=2), axis=1)
        new = np.array([points[labels == i].mean(axis=0) if (labels == i).any() else centres[i]
                        for i in range(k)])
        if np.allclose(new, centres):
            break
        centres = new
    return centres


def _split_landmass(landmass, centres_xy):
    if len(centres_xy) == 1:
        return [landmass]
    # undo the x scaling used for clustering before building cells
    seeds = MultiPoint([(x / KX, y) for x, y in centres_xy])
    cells = voronoi_polygons(seeds, extend_to=landmass.envelope.buffer(0.01))
    return [cell.intersection(landmass) for cell in cells.geoms if cell.intersects(landmass)]


def build_regions(streets, inner_city, water):
    land = inner_city.difference(water)
    landmasses = [g for g in getattr(land, "geoms", [land]) if g.area > 0]
    # only proper roads shape the regions, so adding path types to the deck
    # doesn't move the borders; every street is still assigned a region below
    roads = [s for s in streets if s.highway_types & config.ROAD_TYPES]
    centres = {s.name: s.geometry.centroid for s in roads}

    def landmass_of(point):
        return min(range(len(landmasses)), key=lambda i: landmasses[i].distance(point))

    members = {i: [] for i in range(len(landmasses))}
    for street in roads:
        members[landmass_of(centres[street.name])].append(street)

    big = [i for i, m in members.items() if len(m) >= MIN_STREETS_PER_LANDMASS]
    total_streets = sum(len(members[i]) for i in big)
    total_area = sum(landmasses[i].area for i in big)
    polygons = []
    for i in big:
        share = ((1 - AREA_WEIGHT) * len(members[i]) / total_streets
                 + AREA_WEIGHT * landmasses[i].area / total_area)
        k = max(1, round(TARGET_REGIONS * share))
        points = np.array([(centres[s.name].x * KX, centres[s.name].y) for s in members[i]])
        polygons += _split_landmass(landmasses[i], _kmeans(points, k))

    # small islands join the nearest region
    for i in set(range(len(landmasses))) - set(big):
        nearest = min(range(len(polygons)), key=lambda j: polygons[j].distance(landmasses[i]))
        polygons[nearest] = unary_union([polygons[nearest], landmasses[i]])

    # number north to south in bands, west to east within a band
    _, south, _, north = inner_city.bounds
    band = (north - south) / 5

    def reading_order(polygon):
        p = polygon.representative_point()
        return (int((north - p.y) / band), p.x)

    regions = [Region(n, p) for n, p in enumerate(sorted(polygons, key=reading_order), 1)]
    for street in streets:
        _assign(street, regions)
    return regions


def _assign(street, regions):
    geometry = street.geometry
    shares = [(geometry.intersection(r.polygon).length / geometry.length, r.number) for r in regions]
    chosen = sorted(n for share, n in shares if share >= MIN_SHARE)
    if not chosen:
        # e.g. a bridge mostly over water: use the closest region
        chosen = [min(regions, key=lambda r: r.polygon.distance(geometry.centroid)).number]
    street.regions = chosen
