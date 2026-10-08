import argparse
import sys


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(prog="python -m stockholm_streets")
    sub = parser.add_subparsers(dest="command", required=True)

    p_fetch = sub.add_parser("fetch", help="download OSM data into data/")
    p_fetch.add_argument("--force", action="store_true", help="redownload existing files")

    p_build = sub.add_parser("build", help="render maps and build the Anki deck")
    p_build.add_argument("--limit", type=int, help="only build the first N streets")

    p_preview = sub.add_parser("preview", help="render card previews for a few streets")
    p_preview.add_argument("names", nargs="*", help="street names (default: a random sample)")

    args = parser.parse_args()
    if args.command == "fetch":
        from .fetch import fetch_all
        fetch_all(force=args.force)
    elif args.command == "build":
        from .deck import build_deck
        build_deck(limit=args.limit)
    elif args.command == "preview":
        from .preview import preview
        preview(args.names)


if __name__ == "__main__":
    main()
