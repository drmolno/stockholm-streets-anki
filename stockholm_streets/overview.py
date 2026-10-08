"""The zoomed-out inner city map with numbered regions.

One shared base image is used for every region card; the answer side draws the
street and its region(s) on top as an inline SVG, so no per-street image is needed.
"""
import matplotlib.pyplot as plt
from shapely.geometry import box
from shapely.plotting import plot_polygon

from . import config
from .render import DPI, HIGHLIGHT, KX, LAND, WATER, draw_attribution, draw_roads

OVERVIEW_WIDTH_PX = 1000
OVERVIEW_IMAGE = "sthlm_overview.jpg"
PAD = 0.012  # degrees latitude around the inner city


class Overview:
    def __init__(self, inner_city, water, segments, regions):
        self.inner_city = inner_city
        self.water = water
        self.segments = segments
        self.regions = regions

        minx, miny, maxx, maxy = inner_city.bounds
        cx, cy = (minx + maxx) / 2, (miny + maxy) / 2
        half_h = (maxy - miny) / 2 + PAD / 2
        half_w = (maxx - minx) / 2 + PAD / 2 / KX
        # stay inside the area we have background data for
        south, west, north, east = config.CONTEXT_BBOX
        self.x0, self.x1 = max(cx - half_w, west), min(cx + half_w, east)
        self.y0, self.y1 = max(cy - half_h, south), min(cy + half_h, north)
        half_w, half_h = (self.x1 - self.x0) / 2, (self.y1 - self.y0) / 2
        self.width = OVERVIEW_WIDTH_PX
        # pixel size follows the true (metric) aspect ratio so the map isn't stretched
        self.height = round(self.width * (2 * half_h) / (2 * half_w * KX))

    def to_px(self, x, y):
        return ((x - self.x0) / (self.x1 - self.x0) * self.width,
                (self.y1 - y) / (self.y1 - self.y0) * self.height)

    def render_base(self, path):
        fig = plt.figure(figsize=(self.width / DPI, self.height / DPI), dpi=DPI, facecolor=LAND)
        ax = fig.add_axes([0, 0, 1, 1])
        ax.axis("off")
        ax.set_xlim(self.x0, self.x1)
        ax.set_ylim(self.y0, self.y1)
        plot_polygon(self.water, ax=ax, add_points=False, facecolor=WATER, edgecolor="none", zorder=1)
        draw_roads(ax, self.segments, scale=0.3, casing=0.8)

        # fade everything outside the inner city
        outside = box(self.x0, self.y0, self.x1, self.y1).difference(self.inner_city)
        plot_polygon(outside, ax=ax, add_points=False, facecolor="white", alpha=0.55,
                     edgecolor="none", zorder=8)

        for region in self.regions:
            plot_polygon(region.polygon, ax=ax, add_points=False, facecolor="none",
                         edgecolor="#4a4a4a", linewidth=1.4, zorder=9)
        for region in self.regions:
            p = region.polygon.representative_point()
            ax.text(p.x, p.y, str(region.number), ha="center", va="center", fontsize=13,
                    fontweight="bold", color="#222", zorder=10,
                    bbox={"boxstyle": "circle,pad=0.25", "facecolor": "white",
                          "edgecolor": "#4a4a4a", "linewidth": 1})
        draw_attribution(fig)
        fig.savefig(path, dpi=DPI, format="jpg", facecolor=LAND, pil_kwargs={"quality": 88})
        plt.close(fig)

    def _path_d(self, coords):
        points = [self.to_px(x, y) for x, y in coords]
        return "M" + " L".join(f"{px:.1f},{py:.1f}" for px, py in points)

    def svg_overlay(self, street):
        """Inline SVG with the street's region(s) shaded and the street drawn in red."""
        parts = []
        for region in self.regions:
            if region.number not in street.regions:
                continue
            polygon = region.polygon.simplify(0.0002)
            for poly in getattr(polygon, "geoms", [polygon]):
                d = " ".join(self._path_d(ring.coords) + " Z"
                             for ring in [poly.exterior, *poly.interiors])
                parts.append(f'<path d="{d}" fill="{HIGHLIGHT}" fill-opacity="0.18" '
                             f'fill-rule="evenodd" stroke="{HIGHLIGHT}" stroke-width="2"/>')
        lines = [self._path_d(line.simplify(0.00005).coords) for line, _ in street.lines]
        for colour, width in (("white", 7), (HIGHLIGHT, 4)):
            parts.append(f'<path d="{" ".join(lines)}" fill="none" stroke="{colour}" '
                         f'stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round"/>')
        return (f'<svg viewBox="0 0 {self.width} {self.height}" '
                f'xmlns="http://www.w3.org/2000/svg">{"".join(parts)}</svg>')
