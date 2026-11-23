#!/usr/bin/env python3
"""The app icon at panel and menu sizes, each with a crisp 1px edge.

    python3 tools/make_icon_sizes.py        (after tools/make_icon.py; needs rsvg-convert)

At 16-64px the SVG's own thin edge is a fraction of a pixel and vanishes, so
the swirl ran into the panel (xl_cheese, 23 Nov). Here each size is rendered
from the SVG and given a 1px edge drawn at that size: dark on the outside
(light panels), a fainter light line just inside (dark panels). Written to
data/icons/app/<size>.png; the package installs them in hicolor.
"""

from __future__ import annotations

import io
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SVG = ROOT / "data" / "icons" / "xl-cheeselooks.svg"
OUT = ROOT / "data" / "icons" / "app"
SIZES = (16, 22, 24, 32, 48, 64)
SS = 8                                   # drawn 8x larger, then scaled down: smooth corners


def edge(px: int) -> Image.Image:
    big = px * SS
    layer = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    inset = 8 / 256 * big                # the SVG's rounded square: 8..248, rx 52
    radius = 52 / 256 * big
    box = [inset, inset, big - inset - 1, big - inset - 1]
    d.rounded_rectangle(box, radius, outline=(0, 0, 0, 105), width=SS)          # 1px, dark
    inner = [inset + SS, inset + SS, big - inset - 1 - SS, big - inset - 1 - SS]
    d.rounded_rectangle(inner, radius - SS, outline=(255, 255, 255, 60), width=SS)  # 1px, light
    return layer.resize((px, px), Image.LANCZOS)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for px in SIZES:
        png = subprocess.run(["rsvg-convert", "-w", str(px), "-h", str(px), str(SVG)],
                             capture_output=True, check=True).stdout
        icon = Image.open(io.BytesIO(png)).convert("RGBA")
        icon.alpha_composite(edge(px))
        icon.save(OUT / f"{px}.png")
        print(f"Wrote {OUT / f'{px}.png'}")


if __name__ == "__main__":
    main()
