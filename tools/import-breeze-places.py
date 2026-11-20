#!/usr/bin/env python3
"""Copy Breeze's folder icons, marked for the Tool's colours, one SVG each.

    python3 tools/import-breeze-places.py BREEZE_ICONS_CHECKOUT

The same job as tools/import-mint-y-places.py, for KDE's Breeze
(github.com/KDE/breeze-icons, icons/places/<size>/). Breeze draws each folder
small and by hand, a file per size, so there's no sheet to cut: we copy the
ones we use and mark their colours. A Breeze folder is one shape in the
accent (class ColorScheme-Accent), with the back darkened by a black layer
at 33%, thin white and dark lines, and the picture in the text colour at 60%:

    the accent shape                     -> #3daee9 (front: your folder color)
    the black 33% layer (the back)       -> #3dae09, solid (back: your second color)
    the picture (ColorScheme-Text, 60%)  -> #3dae39, solid (emblem)
    the thin lines                       kept (light and dark edges)

Breeze's own colours are drawn at 32, 48, 64 and 96px; its 16 and 22px
folders are one-colour outlines, so the 32px drawing stands in at 16, 22 and
24px. Names Breeze draws elsewhere are taken through its links (folder-music
is its folder-sound, folder-recent its folder-temp); its desktop is a
monitor, not a folder, so it's left to your icon theme.

Breeze's icons are LGPL 3 or later (Uri Herrera and the KDE contributors);
the licence is in data/icons/breeze/COPYING.
"""
from __future__ import annotations

import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "icons" / "breeze" / "places"
SVG = "http://www.w3.org/2000/svg"
FRONT, BACK, EMBLEM = "#3daee9", "#3dae09", "#3dae39"
NAMES = ("folder", "folder-documents", "folder-download", "folder-music", "folder-open",
         "folder-pictures", "folder-publicshare", "folder-recent", "folder-templates",
         "folder-videos", "network-workgroup", "user-home")
DRAWN = (32, 48, 64, 96)
SMALL = (16, 22, 24)          # drawn from the 32px folder


def mark(svg_text: str) -> str:
    ET.register_namespace("", SVG)
    root = ET.fromstring(svg_text)
    for defs in [e for e in root if e.tag.endswith("defs")]:
        if not any(not c.tag.endswith("style") for c in defs):
            root.remove(defs)                      # only the colour scheme: not needed now
    for e in root.iter():
        style = e.get("style")
        if style is None:
            continue
        cls = e.get("class", "")
        rules = dict(r.split(":", 1) for r in style.replace(" ", "").split(";") if ":" in r)
        if "ColorScheme-Accent" in cls:
            rules["fill"], rules["fill-opacity"] = FRONT, "1"
        elif "fill" not in rules and rules.get("fill-opacity") == "0.33":
            rules["fill"], rules["fill-opacity"] = BACK, "1"
        elif "ColorScheme-Text" in cls and rules.get("fill") == "currentColor":
            rules["fill"], rules["fill-opacity"] = EMBLEM, "1"
        else:
            continue
        rules.pop("color", None)
        e.set("style", ";".join(f"{k}:{v}" for k, v in rules.items()))
        if "class" in e.attrib:
            del e.attrib["class"]
    return ET.tostring(root, encoding="unicode") + "\n"


def sized(svg_text: str, size: int) -> str:
    return re.sub(r"<svg ", f'<svg width="{size}" height="{size}" ', svg_text, count=1)


def main() -> int:
    places = Path(sys.argv[1]) / "icons" / "places"
    count = 0
    for name in NAMES:
        for size in DRAWN:
            f = places / str(size) / f"{name}.svg"
            if not f.exists():
                continue
            text = mark(f.resolve().read_text(encoding="utf-8"))
            for s in (size,) + (SMALL if size == 32 else ()):
                out = OUT / str(s) / f"{name}.svg"
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_text(sized(text, s), encoding="utf-8")
                count += 1
    print(f"{count} icons written to {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
