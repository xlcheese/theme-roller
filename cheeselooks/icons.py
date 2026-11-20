"""Icons tab: folders in your colors (off by default).

Mint-Y's folder and places icons (data/icons/mint-y/places/<size>/<name>.svg,
cut out of Mint's source sheet by tools/import-mint-y-places.py; CC BY-SA 4.0)
are recoloured as text, the way Mint makes Mint-Y-Blue and its other colours:
four colours swapped,

    folder      the front              your folder color (default: the accent)
    backfolder  the back and its tab   your second color (default: darker, as Mint shades)
    paper       the sheet inside       a light grey, as Mint's
    emblem      the picture on front   dark or light, whichever reads on the folder

and written as an icon theme, ~/.local/share/icons/xl-Cheeselooks, SVG at
every size (crisp, HiDPI included). It inherits the icon theme you had
before, then Mint-Y, so every other icon stays as it was. Cinnamon is
switched to it, and switched back to yours when this is off.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from . import palette as pal
from . import paths, reload

THEME = "xl-Cheeselooks"
KEY = ("org.cinnamon.desktop.interface", "icon-theme")
SIZES = (16, 22, 24, 32, 48, 64, 96, 128)
SOURCE = {"folder": "eeca8f", "backfolder": "c89e6b", "paper": "e8e8e8", "emblem": "575757"}
FALLBACK = ("Mint-Y", "Adwaita", "gnome", "hicolor")


def source_dir() -> Path:
    return paths.data_dir() / "data" / "icons" / "mint-y" / "places"


def theme_dir() -> Path:
    return paths._xdg("XDG_DATA_HOME", paths.HOME / ".local" / "share") / "icons" / THEME


def state_file() -> Path:
    return paths.config_dir() / "icons.json"


def colours(t: dict[str, str], icons: dict) -> dict[str, str]:
    """The four colours, from your settings (folder and second color) and the theme."""
    folder = icons.get("folder_color") or t["accent"]
    back = icons.get("second_color") or back_shade(folder)
    dark_emblem = pal.darker(folder, 0.72)
    light_emblem = "#F2F2F2"
    emblem = dark_emblem if pal.contrast(dark_emblem, folder) >= 3.0 else light_emblem
    return {"folder": folder, "backfolder": back, "paper": "#E4E4E4", "emblem": emblem}


def back_shade(folder: str) -> str:
    """The folder's back, as Mint shades its own colours (measured over Mint-Y's
    twelve: lightness about 0.15 lower, saturation a little less, the two
    about 1.6-1.7 apart in contrast). At least 1.6 apart here."""
    import colorsys
    h, l, s = colorsys.rgb_to_hls(*(v / 255 for v in pal.to_rgb(folder)))
    for drop in (0.15, 0.18, 0.21, 0.24, 0.27, 0.30):
        r, g, b = colorsys.hls_to_rgb(h, max(0.04, l - drop), s * 0.8)
        back = pal.from_rgb(r * 255, g * 255, b * 255)
        if pal.contrast(folder, back) >= 1.6:
            return back
    return back


def recolour(svg: str, c: dict[str, str]) -> str:
    for key, src in SOURCE.items():
        svg = svg.replace(src, c[key].lstrip("#").lower()).replace(src.upper(), c[key].lstrip("#").lower())
    return svg


def index_theme(inherits: list[str]) -> str:
    dirs = [f"places/{s}{x}" for s in SIZES for x in ("", "@2x")]
    out = ["[Icon Theme]", f"Name={THEME}",
           "Comment=Folders in your xl-Cheeselooks colors (Mint-Y's, CC BY-SA 4.0)",
           f"Inherits={','.join(inherits)}", f"Directories={','.join(dirs)}", ""]
    for s in SIZES:
        for x in ("", "@2x"):
            out += [f"[places/{s}{x}]", f"Size={s}"] + (["Scale=2"] if x else []) + \
                   ["Context=Places", "Type=Fixed", ""]
    return "\n".join(out)


def _load_state() -> dict:
    try:
        return json.loads(state_file().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _save_state(state: dict) -> None:
    f = state_file()
    if not state:
        if f.exists():
            f.unlink()
        return
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def build(t: dict[str, str], icons: dict, inherits: list[str], out: Path) -> int:
    """Write the icon theme to `out`. Returns the number of icons."""
    c = colours(t, icons)
    if out.exists():
        shutil.rmtree(out)
    count = 0
    for f in sorted(source_dir().glob("*/*.svg")):
        svg = recolour(f.read_text(encoding="utf-8"), c)
        for x in ("", "@2x"):
            d = out / "places" / f"{f.parent.name}{x}"
            d.mkdir(parents=True, exist_ok=True)
            (d / f.name).write_text(svg, encoding="utf-8")
        count += 1
    # Mint-Y's other names for them (nemo, file-manager, folder-open...): the
    # Files app's icon on the panel is the folder, as in Mint's own colours
    aliases = source_dir().parent / "aliases.txt"
    if aliases.exists():
        for line in aliases.read_text(encoding="utf-8").split("\n"):
            parts = line.split()
            if len(parts) != 3:
                continue
            size, alias, target = parts
            for x in ("", "@2x"):
                d = out / "places" / f"{size}{x}"
                link = d / f"{alias}.svg"
                if (d / f"{target}.svg").exists() and not link.exists():
                    link.symlink_to(f"{target}.svg")
    (out / "index.theme").write_text(index_theme(inherits), encoding="utf-8")
    (out / "COPYING").write_text((source_dir().parent / "COPYING").read_text(encoding="utf-8"),
                                 encoding="utf-8")
    if shutil.which("gtk-update-icon-cache"):
        subprocess.run(["gtk-update-icon-cache", "-q", "-f", "-t", str(out)], capture_output=True)
    return count


def enable(t: dict[str, str], icons: dict) -> list[str]:
    """Build the icon theme from your colors and make it Cinnamon's, remembering yours."""
    state = _load_state()
    current = reload.get(*KEY) if reload.available() else None
    if "previous" not in state and current and current != THEME:
        state["previous"] = current
    previous = state.get("previous")
    inherits = ([previous] if previous else []) + [n for n in FALLBACK if n != previous]
    n = build(t, icons, inherits, theme_dir())
    state["on"] = True
    _save_state(state)
    log = [f"Icons: {n} folder and places icons in your colors ({theme_dir()})"]
    if current is not None and current != THEME and reload.set_value(*KEY, THEME):
        log.append(f"Icons: Cinnamon now uses {THEME} (yours, {previous}, fills in the rest)")
    return log


def disable() -> list[str]:
    """Back to your previous icon theme; ours removed."""
    state = _load_state()
    if not state:
        return []
    previous = state.get("previous") or "Mint-Y"
    if reload.available() and reload.get(*KEY) == THEME:
        reload.set_value(*KEY, previous)
    if theme_dir().exists():
        shutil.rmtree(theme_dir())
    _save_state({})
    return [f"Icons: back to {previous}"]


def active() -> bool:
    return bool(_load_state())
