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


# ---------------------------------------------------------------- its window, in the GTK 4 file

# Velocitty's session classes on its window and tabs (velocitty/palette.py:
# STATES, CUSTOM_COLORS), and the palette keys for their colors
_STATE_KEYS = {"admin": "Admin", "remote": "Remote", **{f"custom-{c.lower()}": c for c in _TAB_COLORS}}


def _palette_dirs() -> list[Path]:
    data = paths._xdg("XDG_DATA_HOME", paths.HOME / ".local" / "share")
    return [data / "velocitty" / "palettes", Path("/usr/share/velocitty/palettes")]


def _read_palette(name: str, dark: bool) -> dict[str, str] | None:
    """The colors of a palette as Velocitty reads them: its [Dark] or [Light]
    section, else [Palette]."""
    import configparser
    for d in _palette_dirs():
        f = d / f"{name}.palette"
        if not f.is_file():
            continue
        cp = configparser.ConfigParser(interpolation=None)
        cp.optionxform = str
        try:
            cp.read(f, encoding="utf-8")
        except (configparser.Error, OSError):
            return None
        section = "Dark" if dark and cp.has_section("Dark") else "Light" if cp.has_section("Light") else "Palette"
        return dict(cp[section]) if cp.has_section(section) else None
    return None


def _with(*shadows: str) -> str:
    """Box-shadows together (none left out)."""
    parts = [x for x in shadows if x and x != "none"]
    return ", ".join(parts) or "none"


def _readable(bg: str) -> str:
    return "#ffffff" if pal.contrast("#ffffff", bg) >= pal.contrast("#1e1e1e", bg) else "#1e1e1e"


def scope_to_velocitty(css: str) -> str:
    """Window button rules for Velocitty's windows only: each selector starts
    from its window (window.maximized ... becomes window.terminal.maximized ...,
    headerbar windowcontrols becomes window.terminal headerbar windowcontrols)."""
    import re

    def one(selector: str) -> str:
        s = selector.strip()
        m = re.match(r"window((?:\.[\w-]+)*)\s+(.*)", s)
        if m:
            return f"window.terminal{m.group(1)} {m.group(2)}"
        return f"window.terminal {s}"

    def rule(m: re.Match) -> str:
        return ",\n".join(one(p) for p in m.group(1).split(",")) + " {"
    return re.sub(r"(?m)^([^{}/\n][^{}]*?)\s*\{", rule, css)


def gtk4_css(t: dict[str, str], titlebuttons: str = "", full: bool = False) -> str:
    """Velocitty's window in the theme's style, on top of its own palette CSS
    (this file outranks an app's CSS): the header bar keeps the palette's color
    for each session (root red, remote blue, a tab's own color), with the
    theme's title bar gradient over it as a see-through highlight; the tab
    strip a step away from the header bar, so the header bar is clearly the
    place to grab (xl_cheese); the window buttons and rounded top corners of
    the theme. The running and bell shades and the colored lines under tabs
    stay. Empty when Velocitty isn't installed."""
    if not installed():
        return ""
    name = _current() or "Espresso"
    scheme = (reload.get(SCHEMA, "color-scheme") or "'dark'").strip("'\"")
    dark_ui = scheme == "dark" or (scheme == "system" and pal.luminance(t["bg"]) < pal.luminance(t["text"]))
    p = _read_palette(name, dark_ui)
    if not p or not all(k in p for k in ("Foreground", "Background", "Titlebar")):
        return ""
    bg, fg, title = p["Background"], p["Foreground"], p["Titlebar"]
    title_fg = fg if pal.contrast(fg, title) >= 4.5 else _readable(title)
    shade = "rgba(255, 255, 255, 0.16)" if pal.luminance(bg) < 0.179 else "rgba(0, 0, 0, 0.10)"
    # the theme's title bar gradient: its top is the color lightened by this much
    amount = 0.0
    try:
        top, base = pal.to_rgb(t["wb.title_top"]), pal.to_rgb(t["wb.title"])
        amount = max(0.0, min(1.0, max((a - b) / (255 - b) for a, b in zip(top, base) if b < 255)))
    except (KeyError, ValueError):
        pass
    gloss = f"linear-gradient(to bottom, rgba(255, 255, 255, {amount:.3f}), rgba(255, 255, 255, 0))" \
        if amount > 0.005 else "none"
    if full:
        # with full styling the tabs are your theme's (as Nemo's): their strip too
        from . import tabs
        under = min(t["bg"], t["header"], t["base"], key=pal.luminance)
        dark_theme = pal.luminance(t["bg"]) < 0.25
        strip = pal.darker(under, tabs.STRIP_DARKER[dark_theme]) if float(t["r"]) > 0 else t["bg"]
        strip_fg = t["text"]
    else:
        strip = pal.mix(title, bg, 0.45)
        strip_fg = fg if pal.contrast(fg, strip) >= 4.5 else _readable(strip)
    r = t.get("wb.r", "0")
    head = "window.terminal headerbar, window.terminal headerbar:backdrop"
    out = ["/* Velocitty (Linux Mint's terminal): its window in your theme, on its own colors (velocitty.py) */",
           f"{head} {{\n  background-color: {title};\n  color: {title_fg};\n  background-image: {gloss}; }}"]
    from . import tabs as _tabs
    edges = _tabs.adw_edges(t) if full else {}
    for cls, key in _STATE_KEYS.items():
        if key in p:
            c = p[key]
            out.append(f"window.{cls} headerbar, window.{cls} headerbar:backdrop {{\n"
                       f"  background-color: {c};\n  color: {_readable(c)}; }}")
            line = f"inset 0 -3px 0 {c}"
            if full:   # the line over the tab's own edges (your tab style), not instead of them
                out.append(f"window.terminal tabbar tab.{cls} {{ box-shadow: {_with(line, edges['rest'])}; }}\n"
                           f"window.terminal tabbar tab.{cls}:hover:not(:selected) {{ box-shadow: {_with(line, edges['hover'])}; }}\n"
                           f"window.terminal tabbar tab.{cls}:selected, window.terminal tabbar tab.{cls}:selected:hover "
                           f"{{ box-shadow: {_with(line, edges['selected'])}; }}")
            else:
                out.append(f"window.terminal tabbar tab.{cls} {{ box-shadow: {line}; }}")
    # the tab color swatches (right-click a tab) and the custom tabs' color bars:
    # our button style (full styling) painted over their colors (xl_cheese)
    for name in _TAB_COLORS:
        if name in p:
            c, sel = p[name], f"window.terminal button.custom-swatch.custom-{name.lower()}"
            out.append(f"{sel}, {sel}:hover, {sel}:active, {sel}:checked, {sel}:backdrop,\n"
                       f"window.terminal .color-bar.custom-{name.lower()} {{\n"
                       f"  background-color: {c};\n  background-image: none;\n  border-color: transparent; }}")
            out.append(f"{sel} {{ box-shadow: none; }}\n"
                       f"{sel}:hover {{ box-shadow: 0 0 0 2px {pal.rgba(fg if pal.luminance(bg) < 0.179 else '#000000', 0.25)}; }}\n"
                       f"{sel}:checked {{ box-shadow: 0 0 0 2px {fg}; }}")
    run = f"linear-gradient({shade}, {shade})"
    out += [f"window.terminal.running headerbar, window.terminal.running headerbar:backdrop {{\n"
            f"  background-image: {run}, {gloss}; }}",
            f"window.terminal.bell headerbar, window.terminal.bell headerbar:backdrop {{\n"
            f"  background-image: {run}, {run}, {gloss}; }}",
            # the tab strip: neither the header bar nor the terminal; the open tab joins the terminal
            # (on the tab bar itself too: newer libadwaita draws the strip there,
            # or lets the top bar's color behind it show, xl_cheese's Mint 23 beta)
            f"window.terminal tabbar, window.terminal tabbar:backdrop,\n"
            f"window.terminal tabbar .box, window.terminal tabbar .box:backdrop {{\n"
            f"  background-color: {strip};\n  color: {strip_fg};\n  background-image: none; }}",
            f"window.terminal tabbar tab.running {{ background-image: {run}; }}",
            # Velocitty's menus take its header bar's colors (white text on its
            # blue); full styling gave them our menu background, under the white
            # text (xl_cheese): the theme's menu colors, both
            f"window.terminal popover > contents, window.terminal popover > arrow {{\n"
            f"  background-color: {t['menu_bg']};\n  color: {t['text']}; }}",
            # ...and the buttons in them (the zoom row of the main menu): the menu
            # opens from a header bar button, so the header bar's button rules (its
            # white text) reached them, white on white (xl_cheese)
            # (drawn as the theme's menu items: no face at rest, the menu's hover)
            ",\n".join(f"window.terminal headerbar popover > contents button:not(.osd){st}"
                       for st in ("", ":backdrop"))
            + f" {{\n  color: {t['text']};\n  background-color: transparent;\n  background-image: none;\n"
              f"  border-color: transparent;\n  box-shadow: none; }}",
            ",\n".join(f"window.terminal headerbar popover > contents button:not(.osd){st}"
                       for st in (":hover", ":hover:backdrop"))
            + f" {{\n  color: {t['text']};\n  background-color: {t['menu_hover']};\n  background-image: none;\n"
              f"  border-color: transparent;\n  box-shadow: none; }}",
            # joined buttons there (the style switch): no shared edge drawn on the
            # next one for a hovered or pressed neighbour, as they have no faces
            # (xl_cheese: a dark line beside the hovered one)
            ",\n".join(f"window.terminal headerbar popover > contents .linked:not(.vertical) > button:not(.osd){st} + button:not(.osd)"
                       for st in (":hover", ":active", ":checked"))
            + " {\n  border-color: transparent; }",
            ",\n".join(f"window.terminal headerbar popover > contents button:not(.osd){st}"
                       for st in (":active", ":checked"))
            + f" {{\n  color: {t['text']};\n  background-color: {t['pressed']};\n  background-image: none;\n"
              f"  border-color: transparent;\n  box-shadow: none; }}",
            # the tab overview keeps Velocitty's own look
            f"window.terminal toolbarview.overview headerbar {{\n  background-color: {pal.mix(bg, fg, 0.10)};\n"
            f"  color: {fg};\n  background-image: none; }}",
            # rounded top corners, as the theme's windows (not maximized or tiled)
            f"window.terminal.csd:not(.maximized):not(.tiled):not(.fullscreen) revealer.top-bar > windowhandle,\n"
            f"window.terminal.csd:not(.maximized):not(.tiled):not(.fullscreen) headerbar {{\n"
            f"  border-radius: {r}px {r}px 0 0; }}"]
    if not full:
        # without full styling the tabs are libadwaita's: the open one joins the terminal
        out += [f"window.terminal tabbar tab {{ color: {strip_fg}; background-color: transparent; }}",
                f"window.terminal tabbar tab:selected, window.terminal tabbar tab:selected:hover {{\n"
                f"  color: {fg};\n  background-color: {bg}; }}"]
    if titlebuttons:
        # the theme's window buttons, on Velocitty's windows only
        out.append(scope_to_velocitty(titlebuttons))
    # In a session color (root red, remote blue, a tab's color) the header bar's
    # buttons let it show through: their faces a see-through wash instead of
    # the theme's (xl_cheese: xl-Classic's blue faces on a pink header bar)
    states = [cls for cls, key in _STATE_KEYS.items() if key in p]
    if states:
        out.append(_state_buttons(t, p, states, titlebuttons or t.get("titlebuttons4.css", "")))
    return "\n".join(out) + "\n"


def running() -> bool:
    """A Velocitty window is open: it reads the GTK 4 file only when it starts,
    so after an Apply it needs reopening (the app says so)."""
    import os
    import subprocess
    try:
        # Velocitty renames its process to "velocitty" (setproctitle) once it
        # starts; before that it's /usr/bin/velocitty run by python3 (xl_cheese:
        # matching only the second missed an open Velocitty)
        out = subprocess.run(["pgrep", "-u", str(os.getuid()), "-f", r"(^|/)velocitty( |$)"],
                             capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.SubprocessError):
        return False
    return bool(out.strip())


_WASH = {"rest": "rgba(255, 255, 255, 0.16)", "backdrop": "rgba(255, 255, 255, 0.10)",
         "hover": "rgba(255, 255, 255, 0.28)", "pressed": "rgba(0, 0, 0, 0.18)"}
_WASH_EDGE = "rgba(0, 0, 0, 0.28)"


def _state_of(selector: str) -> str:
    if ":active" in selector or ":checked" in selector:
        return "pressed"
    if ":hover" in selector:
        return "hover"
    if ":backdrop" in selector:
        return "backdrop"
    return "rest"


def _clear(value: str) -> bool:
    """A color nobody sees: transparent, or rgba with alpha 0."""
    v = value.strip()
    return v in ("transparent", "none") or bool(__import__("re").search(r"rgba\([^)]*,\s*0(\.0+)?\)$", v))


def _state_buttons(t: dict[str, str], p: dict[str, str], states: list[str], titlebuttons: str) -> str:
    """The window buttons and header bar buttons of Velocitty's session colors:
    the face a white wash (darker when pressed) and the edge a dark see-through
    line, so the header bar's color shows through. A button the theme leaves
    clear at rest stays clear; the close button keeps its own hover; the window
    buttons' glyphs (the first background layer) stay."""
    import re
    out = ["/* Velocitty's session colors show through the header bar's buttons */"]
    # header bar buttons (the menu, new tab, custom tabs): icons, so the face is the background
    flat = _clear(t.get("w.toolbar_button.border", "transparent"))
    for cls in states:
        fg = _readable(p[_STATE_KEYS[cls]])
        base = f"window.{cls} headerbar button:not(.osd)"
        rest = "transparent" if flat else _WASH["rest"]
        out.append(f"{base}, {base}:backdrop {{\n  color: {fg};\n  background-color: {rest};\n"
                   f"  background-image: none;\n  border-color: {'transparent' if flat else _WASH_EDGE};\n"
                   f"  box-shadow: none; }}")
        out.append(f"{base}:hover {{\n  color: {fg};\n  background-color: {_WASH['hover']};\n"
                   f"  background-image: none;\n  border-color: {_WASH_EDGE};\n  box-shadow: none; }}")
        out.append(f"{base}:active, {base}:checked {{\n  color: {fg};\n  background-color: {_WASH['pressed']};\n"
                   f"  background-image: none;\n  border-color: {_WASH_EDGE};\n  box-shadow: none; }}")
    # window buttons: the theme's rules, their faces washed, for every session class at once
    scoped = scope_to_velocitty(titlebuttons)
    for m in re.finditer(r"(?s)([^{}]+?)\{([^{}]*)\}", scoped):
        selector, body = m.group(1).strip(), m.group(2)
        if "windowcontrols" not in selector or ("background" not in body and "border" not in body):
            continue
        sels = [x.strip() for x in selector.split(",")]
        every = [x.replace("window.terminal", f"window.{cls}", 1) for cls in states for x in sels]
        if ".close" in selector and _state_of(selector) in ("hover", "pressed"):
            # the close button's own warning hover, restated under the session
            # classes: their rest rule outranks the theme's plain :hover (xl_cheese)
            out.append(",\n".join(every) + " {" + body + "}")
            continue
        state = _state_of(selector)
        decl = []
        bg = re.search(r"background-color:\s*([^;]+);", body)
        if bg:
            # only where the theme paints a face: a style that draws its face
            # on the inner node leaves the button (its larger click area) clear,
            # and a wash there spread past the face's edge (xl_cheese)
            decl.append(f"background-color: {'transparent' if _clear(bg.group(1)) else _WASH[state]};")
        img = re.search(r"background-image:\s*([^;]+);", body)
        if img:
            layers = [x.strip() for x in re.split(r",(?![^(]*\))", img.group(1))]
            glyph = [x for x in layers if x.startswith("url(")]
            decl.append(f"background-image: {', '.join(glyph + ['image(transparent)'] * (len(layers) - len(glyph)))};")
        border = re.search(r"border:\s*(\d+px)\s+solid\s+([^;]+);", body)
        if border:
            decl.append(f"border: {border.group(1)} solid {'transparent' if _clear(border.group(2)) else _WASH_EDGE};")
        if "box-shadow" in body:
            decl.append("box-shadow: none;")
        if not decl:
            continue
        out.append(",\n".join(every) + " {\n  " + "\n  ".join(decl) + " }")
    return "\n".join(out) + "\n"
