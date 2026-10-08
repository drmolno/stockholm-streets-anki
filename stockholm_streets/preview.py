"""Render a few notes (all card types) to output/preview/preview.html."""
import html
import random

from . import config
from .deck import CSS, TEMPLATES, note_fields, prepare
from .streets import load_streets

PREVIEW_DIR = config.OUTPUT_DIR / "preview"


def _fill(template, fields):
    for key, value in fields.items():
        template = template.replace("{{" + key + "}}", value)
    return template


def preview(names, sample_size=4):
    all_streets = load_streets()
    if names:
        wanted = set(names)
        streets = [s for s in all_streets if s.name in wanted]
        missing = wanted - {s.name for s in streets}
        if missing:
            print("not found:", ", ".join(sorted(missing)))
    else:
        streets = random.sample(all_streets, sample_size)

    overview, _ = prepare(all_streets, streets, PREVIEW_DIR)
    sections = []
    for street in streets:
        fields = note_fields(street, overview)
        # everything but the SVG overlay is plain text that needs escaping
        fields = {k: v if k in ("Map", "RegionMap") else html.escape(v) for k, v in fields.items()}
        rows = "".join(
            f'<h3>{t["name"]}</h3><div class="pair">'
            f'<div class="card">{_fill(t["qfmt"], fields)}</div>'
            f'<div class="card">{_fill(t["afmt"], fields)}</div></div>'
            for t in TEMPLATES
        )
        sections.append(f"<section><h2>{html.escape(street.name)}</h2>{rows}</section>")
    page = f"""<!doctype html><meta charset="utf-8"><title>Card preview</title>
<style>{CSS}
body {{ background: #ddd; margin: 16px; font-family: sans-serif; }}
section {{ margin-bottom: 40px; }}
h3 {{ margin: 12px 0 6px; color: #555; font-weight: 500; }}
.pair {{ display: flex; gap: 16px; flex-wrap: wrap; }}
.pair .card {{ flex: 1 1 400px; max-width: 640px; padding: 12px; border-radius: 8px; }}
</style>
<p>Each street gives three cards. Left: front · Right: back</p>
{''.join(sections)}"""
    out = PREVIEW_DIR / "preview.html"
    out.write_text(page, encoding="utf-8")
    print(f"wrote {out}")
    for street in streets:
        print(f"  {street.name}: {', '.join(street.districts)} · regions {street.regions}")
