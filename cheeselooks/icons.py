"""Icons tab: folders in your colors (off by default).

Each folder style is a set of SVGs, one per size and name, cut once out of
its project's source sheet by a tools/import-*-places.py script, in that
project's placeholder colours (STYLES). At Apply every style takes the same
path: the placeholders are swapped for yours, as text,

    folder      the front              your folder color (default: the accent)
    backfolder  the back and its tab   your second color (default: the accent, darker, as Mint shades)
    backdark    darker details on it   (Yaru) the back, darker
    paper       the sheet inside       (Mint-Y) a light grey, as Mint's
    emblem      the picture on front   dark or light, whichever reads on the folder

and written as an icon theme, ~/.icons/xl-Cheeselooks, SVG at
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
# folder styles: where their SVGs are, their sizes, and which placeholder
# colour in them is which part (both CC BY-SA 4.0; COPYING in each folder)
STYLES = {
    "mint-y": {"name": "Mint-Y", "dir": "mint-y", "sizes": (16, 22, 24, 32, 48, 64, 96, 128),
               "source": {"folder": "eeca8f", "backfolder": "c89e6b", "paper": "e8e8e8", "emblem": "575757"}},
    "yaru": {"name": "Yaru", "dir": "yaru", "sizes": (16, 24, 32, 48, 256),
             "source": {"folder": "00ff03", "backfolder": "00ff13", "backdark": "008512", "emblem": "008502"}},
}
DEFAULT_STYLE = "mint-y"
# names a style doesn't draw, borrowed from one it does (Yaru has an open
# folder but no drag-accept one); added to Mint-Y's own list of other names
EXTRA_ALIASES = {"yaru": {"folder-drag-accept": "folder-open"}}
SIZES = STYLES[DEFAULT_STYLE]["sizes"]
SOURCE = STYLES[DEFAULT_STYLE]["source"]
FALLBACK = ("Mint-Y", "Adwaita", "gnome", "hicolor")


def style_of(icons: dict) -> str:
    return icons.get("style") if icons.get("style") in STYLES else DEFAULT_STYLE


def source_dir(style: str = DEFAULT_STYLE) -> Path:
    return paths.data_dir() / "data" / "icons" / STYLES[style]["dir"] / "places"


def theme_dir() -> Path:
    """~/.icons, beside ~/.themes where the GTK theme goes: the traditional
    places Mint users and theme instructions use (both are searched)."""
    return paths.HOME / ".icons" / THEME


def old_theme_dir() -> Path:
    """Where the first version wrote it: removed when the theme is rebuilt."""
    return paths._xdg("XDG_DATA_HOME", paths.HOME / ".local" / "share") / "icons" / THEME


def state_file() -> Path:
    return paths.config_dir() / "icons.json"


def colours(t: dict[str, str], icons: dict) -> dict[str, str]:
    """The four colours, from your settings (folder and second color) and the theme."""
    folder = icons.get("folder_color") or t["accent"]
    # the back follows your accent (not the folder color): choose a grey front
    # and the back stays a darker accent, as Yaru's grey-front folders
    back = icons.get("second_color") or back_shade(t["accent"])
    dark_emblem = pal.darker(folder, 0.72)
    light_emblem = "#F2F2F2"
    emblem = dark_emblem if pal.contrast(dark_emblem, folder) >= 3.0 else light_emblem
    return {"folder": folder, "backfolder": back, "backdark": pal.darker(back, 0.45),
            "paper": "#E4E4E4", "emblem": emblem}


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


def recolour(svg: str, c: dict[str, str], style: str = DEFAULT_STYLE) -> str:
    for key, src in STYLES[style]["source"].items():
        svg = svg.replace(src, c[key].lstrip("#").lower()).replace(src.upper(), c[key].lstrip("#").lower())
    return svg


def index_theme(inherits: list[str], style: str = DEFAULT_STYLE) -> str:
    sizes = STYLES[style]["sizes"]
    dirs = [f"places/{s}{x}" for s in sizes for x in ("", "@2x")]
    out = ["[Icon Theme]", f"Name={THEME}",
           f"Comment=Folders in your xl-Cheeselooks colors ({STYLES[style]['name']}'s, CC BY-SA 4.0)",
           f"Inherits={','.join(inherits)}", f"Directories={','.join(dirs)}", ""]
    for s in sizes:
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


def aliases(style: str) -> dict[str, str]:
    """Other names for a style's icons: Mint-Y's list (data/icons/mint-y/
    aliases.txt, from Mint's own symlinks), plus the style's extras. Only
    names whose target the style draws are made, and never over a real icon."""
    out = {}
    f = source_dir().parent / "aliases.txt"
    if f.exists():
        for line in f.read_text(encoding="utf-8").split("\n"):
            parts = line.split()
            if len(parts) == 3:
                out[parts[1]] = parts[2]
    out.update(EXTRA_ALIASES.get(style, {}))
    return out


def build(t: dict[str, str], icons: dict, inherits: list[str], out: Path) -> int:
    """Write the icon theme to `out`. Returns the number of icons."""
    c = colours(t, icons)
    style = style_of(icons)
    src = source_dir(style)
    if out.exists():
        shutil.rmtree(out)
    count = 0
    for f in sorted(src.glob("*/*.svg")):
        svg = recolour(f.read_text(encoding="utf-8"), c, style)
        for x in ("", "@2x"):
            d = out / "places" / f"{f.parent.name}{x}"
            d.mkdir(parents=True, exist_ok=True)
            (d / f.name).write_text(svg, encoding="utf-8")
        count += 1
    # Mint-Y's other names for them (nemo, file-manager, folder-open...): the
    # Files app's icon on the panel is the folder, as in Mint's own colours
    for d in sorted((out / "places").iterdir()):
        for alias, target in aliases(style).items():
            link = d / f"{alias}.svg"
            if (d / f"{target}.svg").exists() and not link.exists():
                link.symlink_to(f"{target}.svg")
    (out / "index.theme").write_text(index_theme(inherits, style), encoding="utf-8")
    (out / "COPYING").write_text((src.parent / "COPYING").read_text(encoding="utf-8"), encoding="utf-8")
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
    if old_theme_dir().exists() and old_theme_dir() != theme_dir():
        shutil.rmtree(old_theme_dir())
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
    for d in (theme_dir(), old_theme_dir()):
        if d.exists():
            shutil.rmtree(d)
    _save_state({})
    return [f"Icons: back to {previous}"]


def active() -> bool:
    return bool(_load_state())
