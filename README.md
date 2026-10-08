# Stockholm streets Anki

Generates an Anki deck for learning the street names of Stockholm's inner city
(Norra innerstaden, Kungsholmen, Södermalm). Each street gives three cards:

- **Karta → Namn**: close-up map with the street highlighted; answer is the name and district
- **Namn → Karta**: the name; answer is the close-up map
- **Namn → Område**: the name and an overview of the inner city split into ~20 numbered
  regions; answer is the region(s) the street runs through

Requires Python 3.10+.

## Usage

```
python -m pip install -r requirements.txt
python -m stockholm_streets fetch      # download OSM data into data/ (once)
python -m stockholm_streets preview    # render a few random cards to output/preview/preview.html
python -m stockholm_streets preview Götgatan "Stora Nygatan"
python -m stockholm_streets build      # render all maps and write output/stockholm_streets.apkg
```

`data/` and `output/` are not in the repository; the commands above create them.
A full build takes a few minutes and produces a deck of about 70 MB.

Import `output/stockholm_streets.apkg` in Anki. Rebuilding and re-importing
updates the existing cards (notes are keyed on the street name).

## Layout

- `stockholm_streets/config.py`: areas, bounding box, which road types count as streets
- `fetch.py`: Overpass queries
- `streets.py`: groups OSM ways into one street per name and assigns districts
- `water.py`: builds water polygons from coastline and lake outlines
- `render.py`: draws the close-up map images
- `regions.py`: splits the inner city into regions (land masses, then k-means on street centres)
- `overview.py`: the region overview image and the per-street SVG answer overlay
- `deck.py`: card templates and `.apkg` packaging
- `preview.py`: renders sample cards to HTML

## License

The code is MIT licensed, see [LICENSE](LICENSE).

Map data © [OpenStreetMap contributors](https://www.openstreetmap.org/copyright),
available under the Open Database License (ODbL), fetched via the Overpass API.
The generated maps and decks carry this attribution; keep it if you share them.
