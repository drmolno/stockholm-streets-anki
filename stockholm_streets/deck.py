"""Build the Anki deck (.apkg): three cards per street."""
import genanki

from . import config
from .overview import Overview
from .regions import build_regions
from .render import MapRenderer, load_road_segments
from .streets import load_inner_city, load_streets
from .water import load_water

# Fixed ids so re-importing a rebuilt deck updates the existing cards
MODEL_ID = 1607392319
DECK_ID = 2059400110

# Media referenced only from templates must start with "_" or Anki's
# "Check Media" deletes it as unused.
OVERVIEW_MEDIA = "_sthlm_overview.jpg"

CSS = """
.card {
  font-family: -apple-system, "Segoe UI", Roboto, sans-serif;
  text-align: center;
  color: #222;
  background: #fff;
}
.card.nightMode { color: #eee; background: #2b2b2b; }
.map img { max-width: 100%; height: auto; border-radius: 6px; }
/* same box for prompt and answer line so the region map doesn't jump */
.prompt, .regions { margin: 10px 0; color: #888; font-size: 16px; line-height: 20px; }
.name { font-size: 30px; font-weight: 600; margin: 8px 0; }
.districts { font-size: 16px; color: #888; margin-top: 4px; }
.overview { position: relative; width: 100%; max-width: 1000px; margin: 0 auto; }
.overview img { display: block; width: 100%; height: auto; border-radius: 6px; }
.overview svg { position: absolute; left: 0; top: 0; width: 100%; height: 100%; }
"""

TEMPLATES = [
    {
        "name": "Karta → Namn",
        "qfmt": """
<div class="map">{{Map}}</div>
<div class="prompt">Vilken gata är markerad?</div>""",
        "afmt": """
<div class="map">{{Map}}</div>
<div class="name">{{Name}}</div>
<div class="districts">{{Districts}}</div>""",
    },
    {
        "name": "Namn → Karta",
        "qfmt": """
<div class="name">{{Name}}</div>
<div class="prompt">Var ligger gatan?</div>""",
        "afmt": """
<div class="name">{{Name}}</div>
<div class="map">{{Map}}</div>
<div class="districts">{{Districts}}</div>""",
    },
    {
        "name": "Namn → Område",
        "qfmt": f"""
<div class="name">{{{{Name}}}}</div>
<div class="prompt">I vilket område ligger gatan?</div>
<div class="overview"><img src="{OVERVIEW_MEDIA}"></div>""",
        "afmt": f"""
<div class="name">{{{{Name}}}}</div>
<div class="regions">{{{{Regions}}}}</div>
<div class="overview"><img src="{OVERVIEW_MEDIA}">{{{{RegionMap}}}}</div>""",
    },
]

MODEL = genanki.Model(
    MODEL_ID,
    "Stockholm street",
    fields=[{"name": "Name"}, {"name": "Map"}, {"name": "Districts"},
            {"name": "Regions"}, {"name": "RegionMap"}],
    templates=TEMPLATES,
    css=CSS,
)


class StreetNote(genanki.Note):
    @property
    def guid(self):
        return genanki.guid_for(self.fields[0])


def image_name(street):
    return f"sthlm_{street.slug}.jpg"


def regions_text(street):
    word = "Område" if len(street.regions) == 1 else "Områden"
    return f"{word} {', '.join(map(str, street.regions))}"


def note_fields(street, overview):
    return {
        "Name": street.name,
        "Map": f'<img src="{image_name(street)}">',
        "Districts": ", ".join(street.districts),
        "Regions": regions_text(street),
        "RegionMap": overview.svg_overlay(street),
    }


def prepare(all_streets, streets, image_dir):
    """Render the overview and the close-up maps of `streets` (a subset of
    `all_streets`); returns (overview, media paths)."""
    image_dir.mkdir(parents=True, exist_ok=True)
    water = load_water()
    inner_city = load_inner_city()
    segments = load_road_segments()

    # regions come from all streets so they don't change with --limit or preview
    regions = build_regions(all_streets, inner_city, water)
    overview = Overview(inner_city, water, segments, regions)
    overview_path = image_dir / OVERVIEW_MEDIA
    overview.render_base(overview_path)

    renderer = MapRenderer(water, inner_city, segments)
    paths = [overview_path]
    for i, street in enumerate(streets, 1):
        path = image_dir / image_name(street)
        renderer.render(street, path)
        paths.append(path)
        if i % 100 == 0:
            print(f"  rendered {i}/{len(streets)}", flush=True)
    return overview, paths


def build_deck(limit=None):
    all_streets = load_streets()
    streets = all_streets[:limit] if limit else all_streets
    print(f"{len(streets)} streets")

    overview, paths = prepare(all_streets, streets, config.IMAGE_DIR)

    deck = genanki.Deck(DECK_ID, "Stockholm::Gatunamn innerstaden")
    for street in streets:
        fields = note_fields(street, overview)
        deck.add_note(StreetNote(model=MODEL, fields=[fields[f["name"]] for f in MODEL.fields]))
    package = genanki.Package(deck)
    package.media_files = [str(p) for p in paths]
    package.write_to_file(config.DECK_FILE)
    print(f"wrote {config.DECK_FILE}")
