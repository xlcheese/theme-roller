"""Velocitty, Linux Mint's terminal (Mint 23): a palette from your theme.

Velocitty (github.com/xapp-project/velocitty) draws its window in its own
colors: a palette, not the GTK theme. Its header bar is the palette's Titlebar
color, and turns red for root and blue for remote sessions (the palette's Admin
and Remote colors) as a warning. It reads palettes from
~/.local/share/velocitty/palettes as well as its own, and reloads when its
org.x.velocitty palette setting changes.

So, while Velocitty is installed: a "Theme Roller" palette, written at each
Apply from the Terminal tab's colors (background, text) and the title bar's
color, with Linux Mint's own Mint palette for the 16 terminal colors, the
warning colors and the tab colors (its light or dark set, as your terminal
is). The first time, Velocitty is switched to it (its palette before is
remembered); pick another palette in Velocitty and that choice is kept.
Taking our colors out of apps, or removing Theme Roller, puts the previous
palette back.
"""

from __future__ import annotations

import json
from pathlib import Path

from . import palette as pal
from . import paths, reload

SCHEMA, KEY = "org.x.velocitty", "palette"
NAME = "Theme Roller"

# Linux Mint's Mint.palette (Velocitty 1.1.1): the 16 terminal colors, and the
# session (Admin, Remote) and tab colors, light and dark
_MINT = {
    "light": {
        "colors": ["#020202", "#cd3232", "#00bc00", "#a5a900", "#0752a8", "#bc05bc", "#0598bc", "#343434",
                   "#5e5e5e", "#cd3333", "#23a321", "#adbb5b", "#0752a8", "#c451ce", "#52a8c7", "#a6a3a6"],
        "Admin": "#A31E1E", "Remote": "#1E55A3",
    },
    "dark": {
        "colors": ["#2e3436", "#cc0000", "#4e9a06", "#c4a000", "#3465a4", "#75507b", "#06989a", "#d3d7cf",
                   "#555753", "#ef2929", "#8ae234", "#fce94f", "#729fcf", "#ad7fa8", "#34e2e2", "#eeeeec"],
        "Admin": "#D82929", "Remote": "#2972D8",
    },
}
_TAB_COLORS = {"Blue": "#1E55A3", "Turquoise": "#0A85A3", "Teal": "#216C69", "Green": "#238F22",
               "Red": "#A31E1E", "Purple": "#722FAD", "Pink": "#AD2F6A", "Orange": "#ffa83d", "Yellow": "#efdf00"}


def palette_file() -> Path:
    data = paths._xdg("XDG_DATA_HOME", paths.HOME / ".local" / "share")
    return data / "velocitty" / "palettes" / f"{NAME}.palette"


def state_file() -> Path:
    return paths.config_dir() / "velocitty.json"


def installed() -> bool:
    return reload.available() and reload.get(SCHEMA, KEY) is not None


def palette_text(t: dict[str, str]) -> str:
    """The palette: one set of colors, for both Velocitty's light and dark styles."""
    bg, fg = t["term.bg"], t["term.text"]
    mint = _MINT["dark" if pal.luminance(bg) < pal.luminance(fg) else "light"]
    lines = ["[Palette]", f"Name={NAME}", f"Foreground={fg}", f"Background={bg}", f"Titlebar={t['wb.title']}"]
    lines += [f"Color{i + 1}={c}" for i, c in enumerate(mint["colors"])]
    lines += [f"Admin={mint['Admin']}", f"Remote={mint['Remote']}"]
    lines += [f"{k}={v}" for k, v in _TAB_COLORS.items()]
    return "\n".join(lines) + "\n"


def _load_state() -> dict:
    try:
        return json.loads(state_file().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _save_state(state: dict) -> None:
    f = state_file()
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def _current() -> str | None:
    value = reload.get(SCHEMA, KEY)
    return value.strip("'\"") if value is not None else None


def enable(t: dict[str, str]) -> list[str]:
    """Write our palette; the first time, switch Velocitty to it. Already on
    it: switch away and back, so it reads the new colors (it reloads a palette
    only when the setting changes)."""
    if not installed():
        return []
    f = palette_file()
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(palette_text(t), encoding="utf-8")
    state = _load_state()
    current = _current()
    if not state:
        state = {"previous": current if current != NAME else None}
        _save_state(state)
        reload.set_value(SCHEMA, KEY, NAME)
        return ["Velocitty: switched to the Theme Roller palette"]
    if current == NAME:
        other = state.get("previous") or "Mint"
        reload.set_value(SCHEMA, KEY, other)
        reload.set_value(SCHEMA, KEY, NAME)
        return ["Velocitty: Theme Roller palette updated"]
    return ["Velocitty: Theme Roller palette written (you use another palette there)"]


def disable() -> list[str]:
    """Velocitty's previous palette back (if it's still on ours), ours removed."""
    state = _load_state()
    if not state and not palette_file().exists():
        return []
    if installed() and _current() == NAME:
        reload.set_value(SCHEMA, KEY, state.get("previous") or "Espresso")
    f = palette_file()
    if f.exists():
        f.unlink()
    try:
        state_file().unlink()
    except OSError:
        pass
    return ["Velocitty: your previous palette back"]


def active() -> bool:
    return bool(_load_state()) or palette_file().exists()
