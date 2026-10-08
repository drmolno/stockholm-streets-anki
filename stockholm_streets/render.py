"""Render the map image shown on a card."""
import json
import math

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.patches import Rectangle
from shapely.plotting import plot_polygon

from . import config
from .streets import is_tunnel, load_inner_city
from .water import load_water

LAT0 = 59.33
KX = math.cos(math.radians(LAT0))  # metres per degree lon / metres per degree lat
M_PER_DEG_LAT = 111_320

WIDTH_PX, HEIGHT_PX, DPI = 800, 600, 100
MIN_SPAN_M = 900  # smallest visible width, so short streets keep some context
PADDING = 0.35

LAND = "#f4f1ea"
WATER = "#a9cfe8"
ROAD = "#ffffff"
MAJOR_ROAD = {"motorway": "#f7c58c", "trunk": "#f7c58c", "primary": "#fbe0a0", "secondary": "#fbe0a0"}
ROAD_CASING = "#c9c3b6"
HIGHLIGHT = "#d62828"

# Required by the ODbL wherever the maps are shown
ATTRIBUTION = "© OpenStreetMap contributors"


def draw_attribution(fig):
    fig.text(0.008, 0.01, ATTRIBUTION, fontsize=7, color="#555", ha="left", va="bottom",
             zorder=20, bbox={"facecolor": "white", "alpha": 0.7, "edgecolor": "none", "pad": 1.5})

# (line width, zorder) per road type in the background
ROAD_STYLE = {
    "motorway": (3.2, 5), "trunk": (3.2, 5), "primary": (2.8, 4), "secondary": (2.6, 4),
    "tertiary": (2.2, 3), "unclassified": (1.6, 2), "residential": (1.6, 2),
    "living_street": (1.4, 2), "pedestrian": (1.4, 2), "road": (1.4, 2),
}


def load_road_segments():
    """{road type: [[(lon, lat), ...], ...]} for the background roads, tunnels left out."""
    segments = {t: [] for t in ROAD_STYLE}
    for e in json.loads(config.BACKGROUND_FILE.read_text(encoding="utf-8"))["elements"]:
        tags = e.get("tags", {})
        if not is_tunnel(tags):
            segments[tags["highway"]].append([(p["lon"], p["lat"]) for p in e["geometry"]])
    return segments


def draw_roads(ax, segments, scale=1.0, casing=1.2):
    for road_type, lines in segments.items():
        width, z = ROAD_STYLE[road_type]
        ax.add_collection(LineCollection(lines, colors=ROAD_CASING, linewidths=(width + casing) * scale,
                                         zorder=z, capstyle="round"))
        ax.add_collection(LineCollection(lines, colors=MAJOR_ROAD.get(road_type, ROAD),
                                         linewidths=width * scale, zorder=z + 0.5, capstyle="round"))


class MapRenderer:
    def __init__(self, water=None, inner_city=None, segments=None):
        self.water = water if water is not None else load_water()
        self.inner_city = inner_city if inner_city is not None else load_inner_city()
        self.fig, self.ax = self._base_map(segments or load_road_segments())
        self.inset = self._inset()
        self._dynamic = []

    def _base_map(self, segments):
        # axis("off") hides the axes background, so land colour goes on the figure
        fig = plt.figure(figsize=(WIDTH_PX / DPI, HEIGHT_PX / DPI), dpi=DPI, facecolor=LAND)
        ax = fig.add_axes([0, 0, 1, 1])
        ax.set_aspect(1 / KX)
        ax.axis("off")
        plot_polygon(self.water, ax=ax, add_points=False, facecolor=WATER, edgecolor="none", zorder=1)
        draw_roads(ax, segments)
        draw_attribution(fig)
        return fig, ax

    def _inset(self):
        """Small overview of the whole inner city in the corner."""
        inset = self.fig.add_axes([0.765, 0.015, 0.22, 0.22])
        inset.set_facecolor(LAND)
        inset.set_aspect(1 / KX)
        inset.set_xticks([])
        inset.set_yticks([])
        for spine in inset.spines.values():
            spine.set_edgecolor("#777")
        plot_polygon(self.water, ax=inset, add_points=False, facecolor=WATER, edgecolor="none")
        plot_polygon(self.inner_city, ax=inset, add_points=False, facecolor="none",
                     edgecolor="#555", linewidth=0.6, linestyle="--")
        minx, miny, maxx, maxy = self.inner_city.bounds
        pad = 0.08 * (maxx - minx)
        inset.set_xlim(minx - pad, maxx + pad)
        inset.set_ylim(miny - pad * KX, maxy + pad * KX)
        return inset

    def _extent(self, street):
        minx, miny, maxx, maxy = street.geometry.bounds
        cx, cy = (minx + maxx) / 2, (miny + maxy) / 2
        width_m = (maxx - minx) * KX * M_PER_DEG_LAT * (1 + 2 * PADDING)
        height_m = (maxy - miny) * M_PER_DEG_LAT * (1 + 2 * PADDING)
        width_m = max(width_m, height_m * WIDTH_PX / HEIGHT_PX, MIN_SPAN_M)
        height_m = width_m * HEIGHT_PX / WIDTH_PX
        half_w = width_m / 2 / (KX * M_PER_DEG_LAT)
        half_h = height_m / 2 / M_PER_DEG_LAT
        return cx - half_w, cx + half_w, cy - half_h, cy + half_h

    def render(self, street, path):
        for artist in self._dynamic:
            artist.remove()
        self._dynamic = []

        x0, x1, y0, y1 = self._extent(street)
        self.ax.set_xlim(x0, x1)
        self.ax.set_ylim(y0, y1)

        surface = [list(line.coords) for line, tunnel in street.lines if not tunnel]
        tunnels = [list(line.coords) for line, tunnel in street.lines if tunnel]
        self._dynamic += [
            self.ax.add_collection(LineCollection(surface, colors="white", linewidths=7.5,
                                                  zorder=10, capstyle="round")),
            self.ax.add_collection(LineCollection(surface, colors=HIGHLIGHT, linewidths=5,
                                                  zorder=11, capstyle="round")),
            self.ax.add_collection(LineCollection(tunnels, colors=HIGHLIGHT, linewidths=3,
                                                  linestyles=(0, (2, 1.5)), zorder=11)),
        ]
        # where we are in the inner city
        self._dynamic.append(self.inset.add_patch(Rectangle(
            (x0, y0), x1 - x0, y1 - y0, facecolor=HIGHLIGHT, alpha=0.35,
            edgecolor=HIGHLIGHT, linewidth=1)))
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        self._dynamic += self.inset.plot([cx], [cy], "o", color=HIGHLIGHT, markersize=3)

        self.fig.savefig(path, dpi=DPI, format="jpg", facecolor=LAND, pil_kwargs={"quality": 85})
