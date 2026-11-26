"""Theme Roller: the app that makes the xl-Cheeselooks themes (GTK 3).

Themes: the Theme tab (first) lists the themes (built-in, yours, and
Custom). Picking one sets every tab to that theme. Changing anything makes it
"Custom", which keeps your latest changes; Save Theme… names Custom as a theme
of your own. Each tab's Reset button (Reset Style, Reset Panel & Menu...) puts
that tab back to the theme it started from; Global also has "Reset All to Theme
Defaults" for every tab. If nothing differs any more, the theme is no longer
Custom, and your latest changes stay in Custom, one click away.

Preview: every change regenerates the theme into a cache folder and loads its
GTK 3 stylesheet into this app only, so the app's own widgets and a sample
window show the result straight away, with a drawn panel. Nothing reaches the
desktop until Apply; after Apply a bar offers Revert, which puts the previous
desktop theme back and keeps your settings here.

Controls are generated from settings._RULES (the table that validates
settings.json). The on/off switches behind some settings ("own colors",
"customize", "follow Global") are not shown: changing one of those settings
turns its switch on (or Follow Global off) by itself.
"""

from __future__ import annotations

import copy
import json
import os
import re
import shutil
import threading
from pathlib import Path
from typing import Any

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import Gdk, GdkPixbuf, Gio, GLib, Gtk, Pango  # noqa: E402

from . import cli, editor, flatpak, imagecolors, palette as pal, panelmarker, paths, icons, qt, reload, render, settings, styles, themes, titlebuttons, tokens, watch  # noqa: E402
from . import shape  # noqa: E402
from .i18n import _, N_  # noqa: E402
from .shape import DEFAULT_PANEL_HEIGHT  # noqa: E402

APP_TITLE = "Theme Roller"      # the tool; the themes and styles it makes keep the xl-Cheeselooks name
PREVIEW_DELAY_MS = 120

TABS = [  # (settings section, tab title)
    ("theme", _("Theme")), ("global", _("Global")), ("style", _("Style")), ("panel", _("Panel & Menu")),
    ("window_borders", _("Window Borders")), ("terminal", _("Terminal")),
    ("details", _("Details")), ("icons", _("Icons")), ("integration", _("Integration")),
    ("share", _("Import & Export")), ("docs", _("Documentation")), ("about", _("About")),
]
# the Icons tab's note (a folder style may have its own: icons.STYLES[...]["note"])
ICON_NOTE = _("Folders recolored: the folder color (the front) follows your accent, and the second color "
              "(the back) a darker shade of it. Choose either and both keep their colors from then on; Reset "
              "Icons follows the theme again. Every other icon stays as in your current icon theme. Apply to "
              "use them.")
REPO_URL = "https://github.com/xlcheese/theme-roller"
DOCS_URL = REPO_URL + "/tree/HEAD/docs"     # HEAD: the default branch
TIP_URL = "https://www.paypal.com/donate/?hosted_button_id=SDDYDENKXPCWN"   # About: a tip for the author ("" hides it)
# Documentation tab: short notes on each part of the app (the full docs are online)
DOC_NOTES = [
    (_("Themes and styles"),
     _("A <b>theme</b> is your colors and settings: everything on these tabs. A <b>style</b> is how "
       "things are drawn: edges, hovers, tabs and panel buttons. Any theme can use any style. Everything "
       "shows in the preview first; nothing changes on your desktop until you click <b>Apply</b>, and "
       "<b>Revert</b> puts your previous theme back.")),
    (_("Theme"),
     _("Start from a built-in theme, one shared by someone else, or one of your own. Change anything and "
       "it becomes <b>Custom</b>; <b>Save Theme…</b> keeps your changes under a name. Your own themes "
       "can be duplicated, renamed and deleted.")),
    (_("Global"),
     _("Three colors make a complete light or dark theme: accent, background and text. Then the shape of "
       "everything: Size, Roundness, Gradient, and how hovers fade. <b>Colors from</b> picks an accent "
       "from your wallpaper or any picture.")),
    (_("Style"),
     _("Pick how things are drawn, and set its Depth (how strong edges and shadows are) and Unfocused "
       "depth (how much of that unfocused windows keep). You can also make your own: a style is one "
       "style.toml file, in ~/.local/share/theme-roller/styles/&lt;name&gt;/. <b>Create a starter "
       "style…</b> makes one with every option explained: the essentials are on, the rest switched off "
       "with a #, each with a short note. Edit it, then pick it on the Style tab. <b>Check a style "
       "sheet for issues…</b> tells you if anything in it needs fixing.")),
    (_("Panel &amp; Menu"),
     _("The Cinnamon panel and its menus: their own colors, label weight, height, roundness, gradient "
       "and see-through. Left alone, they follow Global.")),
    (_("Window Borders"),
     _("Title bars and window buttons: colors, height, gradient, border, roundness, and a choice of "
       "button styles and Minimize, Maximize and Close glyphs. When these change, Apply restarts "
       "Cinnamon by itself (your windows stay open), as window borders only reload then.")),
    (_("Terminal"),
     _("The terminal follows the theme, or pick one of the color sets, or your own colors.")),
    (_("Details"),
     _("Tooltips, scrollbars (overlay or classic, roundness, width), sliders, switches and the focus ring.")),
    (_("Icons"),
     _("Folder icons in your colors, in six styles. Only the folders change; other icons stay as they "
       "were. The folder color follows your accent unless you pick one; on xl-Big Baddy, the second "
       "color is its racing stripes. Off until you switch it on.")),
    (_("Integration"),
     _("Linux apps come in a few kinds, and each looks for its colors in its own place. These switches "
       "bring your colors to the hodgepodge that doesn't read the theme on its own: GNOME-style apps, "
       "Flatpak apps, Qt apps like VLC, and text editors. <b>Scan my apps</b> shows which of your apps "
       "are which kind; <b>Take colors out of apps</b> removes them until the next Apply. Pick another "
       "theme in Mint's settings and Theme Roller's colors leave your apps by themselves.")),
    (_("Import &amp; Export"),
     _("Share a theme as one <tt>.xltheme</tt> file, and add themes others shared with you.")),
]
LABELS = {
    "accent": _("Accent"), "bg": _("Background"), "text": _("Text"), "size": _("Size"),
    "roundness": _("Roundness"), "gradient": _("Gradient"), "hover_in_ms": _("Hover in (ms)"),
    "hover_out_ms": _("Hover out (ms)"), "hover_strength": _("Hover strength"), "depth": _("Depth"), "unfocused_depth": _("Unfocused depth"),
    "label_weight": _("Label weight"), "panel_opacity": _("Opacity"), "menu_opacity": _("Opacity"),
    "notification_opacity": _("Notification opacity"), "panel_height": _("Height"),
    "item_roundness": _("Menu-item roundness"),
    "title_bar": _("Title bar"), "title_text": _("Title text"), "border": _("Border"),
    "title_bar_height": _("Title bar height"), "border_width": _("Border width"), "window_roundness": _("Window roundness"), "round_bottom": _("Round bottom corners"),
    "title_gradient": _("Title bar gradient"), "button_layout": _("Buttons on the"),
    "button_style": _("Button style"), "button_roundness": _("Button roundness"), "button_spacing": _("Button spacing"), "button_glyphs": _("Glyphs"),
    "mode": _("Mode"), "color": _("Color"), "width": _("Width"), "style": _("Style"),
    "libadwaita": _("GNOME-style apps"),
    "enabled": _("Custom folder style"), "folder_color": _("Folder color"), "second_color": _("Second color"),
    "flatpak_access": _("Flatpak apps"), "qt_colors": _("Qt apps (VLC…)"), "editor_colors": _("Text editors (Xed…)"),
}
GROUPS = {"panel_shape": _("Panel style"), "menu_shape": _("Menu style"), "tooltips": _("Tooltips"),
          "scrollbars": _("Scrollbars"), "sliders": _("Sliders"), "switches": _("Switches"),
          "focus_ring": _("Focus ring")}
# Panel & Menu: the order shown, and the heading each setting sits under
# (Height and Opacity are kept outside the shape groups in the settings file,
# so changing them doesn't stop the shapes following Global)
PANEL_LAYOUT = [
    (("panel", "label_weight"), None), (("panel", "notification_opacity"), None),
    (("panel", "panel_height"), "panel_shape"), (("panel", "panel_shape", "roundness"), "panel_shape"),
    (("panel", "panel_shape", "gradient"), "panel_shape"), (("panel", "panel_opacity"), "panel_shape"),
    (("panel", "menu_shape", "roundness"), "menu_shape"),
    (("panel", "menu_shape", "item_roundness"), "menu_shape"), (("panel", "menu_opacity"), "menu_shape"),
]
SECTION_NOTES = {
    "panel": _("Colors left on “Follow theme” use the Global colors."),
    "window_borders": _("Colors left on “Follow theme” come from the Global colors."),
    "terminal": _("Left on “Follow theme”, the terminal uses the theme's content colors."),
}
GATES = {"separate_colors": True, "custom": True, "follow_global": False}  # value set when a sibling changes
HIDDEN = set(GATES) | ({"round_bottom"} if not tokens.ROUND_BOTTOM_READY else set())
def _integration_note(text: str) -> Gtk.Label:
    """The explanation under an Integration switch: indented under its title and
    as wide as the tab, so it takes a few lines rather than many."""
    note = Gtk.Label(label=text, xalign=0, wrap=True, max_width_chars=100, margin_start=16,
                     margin_bottom=4, hexpand=True)
    note.get_style_context().add_class("dim-label")
    return note


# the line under an Integration switch (a function: some depend on what's installed)
# The Integration tab (xl_cheese, 22 Nov): one intro explains why apps need
# help, so each row is just a name; what each does and when it shows is its
# tooltip; only something missing is said under it.
INTEGRATION_INTRO = _("Linux apps come in a few kinds, and each looks for its colors in its own place. "
                      "Theme Roller brings your theme to all of them. These are already set, so you only "
                      "need this tab if an app doesn't match.")
INTEGRATION_TIPS = {
    "libadwaita": _("GNOME apps such as Calculator and Text Editor (libadwaita). Colors: your colors, and "
                    "GNOME's accent to match. Full: also your buttons, title buttons and tabs; this "
                    "overrides apps' own styling, so some lose colors of their own (Flatpak ones need "
                    "Flatpak apps on). Reopen apps to see changes."),
    "flatpak_access": _("Lets Flatpak apps read your theme, so they get its colors. Reopen open apps to see them."),
    "qt_colors": lambda: qt.note(),
    "editor_colors": lambda: editor.NOTE,
}
INTEGRATION_MISSING = {
    "flatpak_access": lambda: "" if flatpak.available() else _("Flatpak isn't installed."),
    "qt_colors": lambda: qt.missing(),
}
SORTS = (("az", _("A–Z")), ("za", _("Z–A")), ("new", _("Newest")), ("old", _("Oldest")))
SORT_DEFAULTS = {"theme_sort": "new"}    # themes: yours first, then the built-in ones in their set order
# Linux Mint's Mint-Y accent colors (mint-themes' constants.py), Mint-Y's own
# green first: the accent chooser offers them as quick picks
MINT_ACCENTS = (("Green", "#35A854"), ("Aqua", "#1F9EDE"), ("Blue", "#0C75DE"), ("Teal", "#199CA8"),
                ("Grey", "#70737A"), ("Sand", "#C5A07C"), ("Orange", "#FF7139"), ("Red", "#E82127"),
                ("Pink", "#E54980"), ("Purple", "#8C5DD9"))
NAME_CHARS = 34            # list rows: longer names end in "…" (the full name is the tooltip)


def _prefs_file() -> Path:
    return paths.config_dir() / "app.json"


def _load_prefs() -> dict:
    try:
        return json.loads(_prefs_file().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _save_prefs(prefs: dict) -> None:
    try:
        _prefs_file().parent.mkdir(parents=True, exist_ok=True)
        _prefs_file().write_text(json.dumps(prefs, indent=2) + "\n", encoding="utf-8")
    except OSError:
        pass


def _natural(name: str) -> list:
    """A-Z key: case-insensitive, with numbers in order ("Theme 2" before "Theme 10")."""
    return [int(part) if part.isdigit() else part for part in re.split(r"(\d+)", name.casefold())]


def _theme_age(f: Path, builtin: bool) -> float:
    """For Newest and Oldest: your themes by when they were saved; the built-in
    ones in a set order, after yours, from the number their file starts with
    (01-xl-cheeselooks.json first: xl_cheese's order, 22 Nov). Their file dates
    can't hold it: a checkout or an install gives them all the same date."""
    if not builtin:
        return f.stat().st_mtime
    m = re.match(r"(\d+)", f.name)
    return -float(m.group(1)) if m else -1000.0


def _sorted(items: list, order: str) -> list:
    """items: (name, modified time, ...) tuples."""
    if order in ("new", "old"):
        return sorted(items, key=lambda it: (it[1], _natural(it[0])), reverse=(order == "new"))
    return sorted(items, key=lambda it: _natural(it[0]), reverse=(order == "za"))
CHOICE_LABELS = {"button_style": titlebuttons.STYLES,   # choices shown by name instead of id
                 "libadwaita": {"off": _("Off"), "colors": _("Colors"), "full": _("Full")},
                 "style": {k: v["name"] for k, v in icons.STYLES.items()}}


def _get(data: dict, path: tuple[str, ...]) -> Any:
    for k in path:
        data = data[k]
    return data


def _set(data: dict, path: tuple[str, ...], value: Any) -> None:
    for k in path[:-1]:
        data = data[k]
    data[path[-1]] = value


def _app_name(program: str) -> str:
    """The name an app has in the menu (xed: Text Editor), else its program name."""
    for info in Gio.AppInfo.get_all():
        exe = info.get_executable() or ""
        if os.path.basename(exe) == program:
            return info.get_display_name() or program
    return program


def _hex(rgba: Gdk.RGBA) -> str:
    return "#{:02X}{:02X}{:02X}".format(round(rgba.red * 255), round(rgba.green * 255), round(rgba.blue * 255))


def _rgba(hex_color: str) -> Gdk.RGBA:
    c = Gdk.RGBA()
    c.parse(hex_color)
    return c


def _same(a: dict, b: dict) -> bool:
    """Equal settings, ignoring which theme they're labelled with, and your
    per-user settings (Integration, the Icons switch and style: not part of a
    theme, so they'd make every theme look changed: "Custom")."""
    strip = lambda d: {k: v for k, v in d.items() if k not in ("theme", "based_on", "version")}  # noqa: E731
    return strip(a) == strip(settings.keep_per_user(b, a))


def _needs_apply(data: dict, applied: dict) -> bool:
    """Anything to Apply: another theme, a changed setting, or one of your
    per-user settings (Integration, the Icons switch and folder style: they
    don't make a theme Custom, but they still need an Apply)."""
    mine = settings.keep_per_user(applied, data) != applied
    return not _same(data, applied) or mine or data["theme"] != applied["theme"]


def _on_desktop() -> bool:
    """Is the desktop on our theme? (Without gsettings there's no telling: yes.)"""
    if not reload.available():
        return True
    return watch.is_ours(reload.get(*cli.THEME_KEY))


def _short_name(name: str, most: int = 24) -> str:
    """A file name for a one-line message: long ones (pictures saved from the
    web) keep their start and their end, e.g. "W1siZiIsIjQ…dXQ.jpg"."""
    if len(name) <= most:
        return name
    keep = most - 1
    return name[:keep - keep // 2] + "…" + name[-(keep // 2):]


class SettingsWindow(Gtk.ApplicationWindow):
    def __init__(self, app: Gtk.Application):
        super().__init__(application=app, title=APP_TITLE)
        # no default size: it opens at its smallest, which shows every settings tab whole
        self.applied = settings.load(paths.settings_file())
        self.data = copy.deepcopy(self.applied)
        if self.data["theme"] == themes.CUSTOM:
            self.base = themes.based_on() or settings.DEFAULTS["theme"]
        else:
            self.base = self.data["theme"]
        self.base_cache: dict[str, dict] = {}
        self.controls: dict[tuple[str, ...], tuple[Any, str]] = {}
        self.reset_btns: dict[str, Gtk.Button] = {}
        self.prefs = _load_prefs()          # app choices: list sort orders
        self.custom_sub: Gtk.Label | None = None
        self.cinnamon_panel_height: int | None = None   # read once, for the Panel height slider     # tooltips name the theme (see update_buttons)
        self.syncing = False
        self.pending = 0
        self.preview_dir = paths.cache_dir() / "preview"
        self.theme_css = Gtk.CssProvider()
        self.extra_css = Gtk.CssProvider()
        screen = Gdk.Screen.get_default()
        # Under the preview, nothing of the desktop's own theme: the preview is
        # the whole theme, so whatever it doesn't set must look as it will on
        # the desktop (GTK's defaults), not as the current theme draws it.
        # Adwaita underneath showed light borders on dark previews (slider
        # tracks, the tab box, color swatches; xl_cheese).
        self.reset_css = Gtk.CssProvider()
        self.reset_css.load_from_data(b"* { all: unset; }")
        Gtk.StyleContext.add_provider_for_screen(screen, self.reset_css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION - 1)
        Gtk.StyleContext.add_provider_for_screen(screen, self.theme_css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        Gtk.StyleContext.add_provider_for_screen(screen, self.extra_css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 1)

        header = Gtk.HeaderBar(show_close_button=True, title=APP_TITLE)
        header.set_subtitle(_("Preview: nothing changes on the desktop until Apply"))
        self.apply_btn = Gtk.Button(label=_("Apply"))
        self.apply_btn.get_style_context().add_class("suggested-action")
        self.apply_btn.connect("clicked", self.on_apply)
        header.pack_start(self.apply_btn)          # opposite the window buttons, at the outer edge
        # shown after Apply: puts the previous desktop theme back
        self.revert_btn = Gtk.Button(label=_("Revert"))
        self.revert_btn.get_style_context().add_class("xl-drawn")    # a drawn button, not flat
        self.revert_btn.set_tooltip_text(_("Put the previous theme back on the desktop (your settings here stay)"))
        self.revert_btn.connect("clicked", self.on_revert)
        self.revert_btn.set_no_show_all(True)
        header.pack_start(self.revert_btn)
        self.set_titlebar(header)

        self.stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.CROSSFADE)
        for section, title in TABS:
            self.stack.add_titled(self._tab(section), section, title)
        sidebar = Gtk.StackSidebar(stack=self.stack)
        sidebar.set_size_request(160, -1)
        self.sidebar = sidebar
        # wraps inside the window's width and never widens it: breaks inside long
        # words (file names, paths) too, and asks for almost no width of its own
        self.status = Gtk.Label(xalign=0, selectable=True, wrap=True, wrap_mode=Pango.WrapMode.WORD_CHAR,
                                max_width_chars=1)
        # the status line: an icon for the kind of message (done, needs your
        # attention, error, information), errors tinted in the theme's red and
        # attention in its accent; every new message glows briefly, then fades
        # (xl_cheese: the plain line at the bottom was easy to miss). One row:
        # the window doesn't grow.
        self.status_icon = Gtk.Image(valign=Gtk.Align.START)
        self.status_bar = Gtk.Box(spacing=6, margin_start=8, margin_end=8, margin_bottom=4)
        self.status_bar.get_style_context().add_class("xl-status")
        self.status_bar.pack_start(self.status_icon, False, False, 0)
        self.status_bar.pack_start(self.status, True, True, 0)
        self._status_kind: str | None = None
        self._status_glow = 0
        self.status.connect("notify::label", self._status_changed)
        pages = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        pages.pack_start(self.stack, True, True, 0)
        pages.pack_start(self.status_bar, False, False, 0)
        left = Gtk.Box()
        left.pack_start(sidebar, False, False, 0)
        left.pack_start(pages, True, True, 0)

        paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        paned.pack1(left, resize=True, shrink=False)
        paned.pack2(self._preview(), resize=False, shrink=False)
        # no set position: the preview opens at its own width (its button row),
        # the tabs take the rest
        main = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        main.pack_start(paned, True, True, 0)
        self.add(main)
        self.fill_theme_list()
        self.sync_controls()
        self.update_preview()
        self.update_buttons()
        self.show_all()
        self._styles_seen = self._style_files()
        self.connect("focus-in-event", self._on_focus_in)

    def _style_files(self) -> tuple:
        """Every style.toml in the style folders, with when it last changed."""
        found = []
        for base in paths.style_dirs():
            if base.is_dir():
                for f in sorted(base.glob("*/style.toml")):
                    try:
                        found.append((str(f), f.stat().st_mtime))
                    except OSError:
                        pass
        return tuple(found)

    def _on_focus_in(self, *_args) -> bool:
        """Back from Nemo or a text editor: a style added, renamed or edited
        there shows up without reopening Theme Roller, and the preview redraws
        with it."""
        now = self._style_files()
        if now != self._styles_seen:
            self._styles_seen = now
            self.fill_style_list()
            self.update_preview()
        self.update_buttons()          # another theme picked in Mint's settings meanwhile: Apply
        return False

    # ------------------------------------------------------------------ tabs
    def _page(self, grid: Gtk.Grid) -> Gtk.Widget:
        scroller = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER)
        scroller.add(grid)
        return scroller

    def _tab(self, section: str) -> Gtk.Widget:
        grid = Gtk.Grid(column_spacing=12, row_spacing=8, margin=14)
        row = 0
        if section == "share":
            return self._page(self._share_tab(grid))
        if section == "about":
            return self._page(self._about_tab(grid))
        if section == "docs":
            return self._page(self._docs_tab(grid))
        if section == "theme":
            return self._page(self._theme_tab(grid))
        if section == "style":
            row = self._style_rows(grid, row)
        if section == "terminal":
            row = self._terminal_picks(grid, row)
        if section in SECTION_NOTES:
            note = Gtk.Label(label=SECTION_NOTES[section], xalign=0, wrap=True)
            note.get_style_context().add_class("dim-label")
            grid.attach(note, 0, row, 2, 1)
            row += 1
        group = None
        rules = [r for r in settings._RULES if r[0][0] == section and r[0][-1] not in HIDDEN]
        heading = {}
        if section == "integration":
            intro = Gtk.Label(label=INTEGRATION_INTRO, xalign=0, wrap=True, max_width_chars=60, hexpand=True,
                              margin_bottom=6)
            grid.attach(intro, 0, row, 2, 1)
            scan = Gtk.Button(label=_("Scan my apps"), halign=Gtk.Align.START, margin_bottom=8)
            scan.set_tooltip_text(_("Lists the apps on this computer by kind, and whether Theme Roller "
                                    "reaches them: the answer to \u201cwhy doesn't this app match?\u201d"))
            scan.connect("clicked", lambda _b: self._scan_dialog())
            grid.attach(scan, 0, row + 1, 2, 1)
            row += 2
        if section == "panel":
            order = [p for p, _g in PANEL_LAYOUT]
            heading = dict(PANEL_LAYOUT)
            rules.sort(key=lambda r: order.index(r[0]) if r[0] in order else -1)   # colors first
        for path, kind, extra in rules:
            under = heading.get(path, path[1] if len(path) == 3 else None)
            if under and under != group:
                group = under
                head = Gtk.Label(xalign=0, margin_top=8)
                head.set_markup(f"<b>{GLib.markup_escape_text(GROUPS.get(group, group))}</b>")
                grid.attach(head, 0, row, 2, 1)
                row += 1
            label = Gtk.Label(label=LABELS.get(path[-1], _(path[-1].replace("_", " ").capitalize())), xalign=0)
            if path == ("icons", "style"):
                # pictures of each style, under the switch that names it
                grid.attach(self._folder_style_picker(path, extra), 0, row, 2, 1)
                row += 1
                continue
            if path == ("icons", "enabled"):
                self.icons_switch_label = label     # "Custom folder style", "Yaru folder style"
            if path == ("icons", "second_color"):
                self.second_color_label = label     # some styles call it something else
            grid.attach(label, 0, row, 1, 1)
            ctl = self._control(path, kind, extra)
            grid.attach(ctl, 1, row, 1, 1)
            row += 1
            if path[0] == "integration":
                tip = INTEGRATION_TIPS.get(path[-1], "")
                label.set_tooltip_text(tip() if callable(tip) else tip)
                ctl.set_tooltip_text(label.get_tooltip_text())      # on the switch too
                missing = INTEGRATION_MISSING.get(path[-1], lambda: "")()
                if missing:                                          # only what's missing shows
                    grid.attach(_integration_note(missing), 0, row, 2, 1)
                    row += 1
            if path == ("global", "text"):
                row = self._image_colors_row(grid, row)
        if section == "icons":
            row = self._icon_preview_row(grid, row)
        if section == "integration":
            row = self._set_aside_row(grid, row)
        if section not in ("integration", "about", "docs"):   # integration: Flatpak access is a system change
            box = Gtk.Box(spacing=8, halign=Gtk.Align.START, margin_top=14)
            reset = Gtk.Button(label=_("Reset {tab}").format(tab=dict(TABS)[section]))
            reset.connect("clicked", lambda _b, s=section: self.reset_section(s))
            box.pack_start(reset, False, False, 0)
            self.reset_btns[section] = reset
            if section == "global":
                every = Gtk.Button(label=_("Reset All to Theme Defaults"))
                every.connect("clicked", lambda _b: self.reset_all())
                box.pack_start(every, False, False, 0)
                self.reset_btns["all"] = every
            grid.attach(box, 0, row, 2, 1)
        return self._page(grid)

    def _control(self, path: tuple[str, ...], kind: str, extra: Any) -> Gtk.Widget:
        if path[-1] == "button_glyphs":
            return self._glyph_picker(path, extra)
        if kind in ("color", "color?"):
            box = Gtk.Box(spacing=10)
            button = Gtk.ColorButton(use_alpha=False, show_editor=True)   # straight to the editor
            if path[-1] == "accent":
                # accents open on Linux Mint's own Mint-Y colors (the Minted
                # themes' quick picks), with + for any other color
                button.set_property("show-editor", False)
                button.add_palette(Gtk.Orientation.HORIZONTAL, len(MINT_ACCENTS),
                                   [_rgba(c) for _n, c in MINT_ACCENTS])
            button.connect("color-set", lambda b: self.changed(path, _hex(b.get_rgba())))
            value = Gtk.Label(xalign=0, selectable=True)
            box.pack_start(button, False, False, 0)
            box.pack_start(value, False, False, 0)
            if path == ("icons", "second_color"):
                # xl-Big Baddy: takes the racing stripes off (shown while they're on)
                off = Gtk.Button(label=_("No stripes"))
                off.connect("clicked", lambda _b: self.changed(path, None))
                off.set_no_show_all(True)
                box.pack_start(off, False, False, 0)
                self.stripes_off = off
            self.controls[path] = ((button, value), kind)
            return box
        if kind in ("int", "int?"):    # int?: None shows the default (button roundness: the style's)
            lo, hi = extra
            step = 2 if path == ("global", "size") else 1      # Size: even heights only
            scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, lo, hi, step)
            scale.set_digits(0)
            scale.set_hexpand(True)
            scale.set_size_request(260, -1)
            if step == 2:
                scale.set_round_digits(0)
                scale.add_mark(shape.SIZE_DEFAULT, Gtk.PositionType.BOTTOM, None)
            scale.connect("value-changed", lambda s, st=step: self.changed(
                path, int(round(s.get_value() / st)) * st))
            self.controls[path] = (scale, kind)
            return scale
        if kind == "bool":
            switch = Gtk.Switch(halign=Gtk.Align.START)
            switch.connect("notify::active", lambda s, _p: self.changed(path, s.get_active()))
            self.controls[path] = (switch, kind)
            return switch
        if len(extra) <= 3:
            # a few choices: inline buttons, one pressed
            box = Gtk.Box(halign=Gtk.Align.START)
            box.get_style_context().add_class("linked")
            buttons = {}
            for choice in extra:
                b = Gtk.ToggleButton(label=_(choice.replace("_", " ").capitalize()))
                b.connect("toggled", lambda btn, c=choice: btn.get_active() and self.changed(path, c))
                box.pack_start(b, False, False, 0)
                buttons[choice] = b
            self.controls[path] = (buttons, "inline")
            return box
        combo = Gtk.ComboBoxText()
        names = CHOICE_LABELS.get(path[-1], {})
        for choice in extra:
            combo.append(choice, names.get(choice, _(choice.replace("_", " ").capitalize())))
        combo.connect("changed", lambda c: c.get_active_id() and self.changed(path, c.get_active_id()))
        self.controls[path] = (combo, kind)
        return combo

    GLYPHS_PER_ROW = 3

    def _glyph_picker(self, path: tuple[str, ...], sets: tuple[str, ...]) -> Gtk.Widget:
        """Joined buttons, each showing a glyph set's minimize, maximize and close
        glyphs (the icon theme's own for Icon Theme); the name is the tooltip."""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6, halign=Gtk.Align.START)
        buttons, self.glyph_images = {}, {}
        line = None
        for i, gid in enumerate(sets):
            if i % self.GLYPHS_PER_ROW == 0:          # two rows of joined buttons (3 + 2, then 3 + 3)
                line = Gtk.Box(halign=Gtk.Align.START)
                line.get_style_context().add_class("linked")
                box.pack_start(line, False, False, 0)
            b = Gtk.ToggleButton()
            b.set_tooltip_text(_(titlebuttons.GLYPH_SET_NAMES[gid]))
            row = Gtk.Box(spacing=3)
            imgs = []
            for fn in ("minimize", "maximize", "close"):
                img = (Gtk.Image.new_from_icon_name(titlebuttons.ICON_NAMES[fn], Gtk.IconSize.MENU)
                       if gid == "icons" else Gtk.Image())
                row.pack_start(img, False, False, 0)
                imgs.append((fn, img))
            self.glyph_images[gid] = imgs
            b.add(row)
            b.connect("toggled", lambda btn, g=gid: btn.get_active() and self.changed(path, g))
            line.pack_start(b, False, False, 0)
            buttons[gid] = b
        self.controls[path] = (buttons, "glyphs")
        return box

    FOLDER_STYLE_PX = 64          # the style pictures: three to a row (six styles: two rows)

    def _folder_style_picker(self, path: tuple[str, ...], choices: tuple[str, ...]) -> Gtk.Widget:
        """A picture of each folder style, in your colors, to click; more than
        a row's worth wrap onto a second row."""
        flow = Gtk.FlowBox(selection_mode=Gtk.SelectionMode.NONE, max_children_per_line=3,
                           min_children_per_line=1, homogeneous=True, halign=Gtk.Align.START,
                           column_spacing=10, row_spacing=10, margin_start=16, margin_top=6)
        buttons, self.folder_style_images = {}, {}
        for sid in choices:
            b = Gtk.ToggleButton(relief=Gtk.ReliefStyle.NONE)
            b.set_tooltip_text(icons.STYLES[sid]["name"])
            img = Gtk.Image()
            b.add(img)
            self.folder_style_images[sid] = img

            def toggled(btn: Gtk.ToggleButton, s=sid) -> None:
                if btn.get_active():
                    self.changed(path, s)
                elif not self.syncing and icons.style_of(self.data["icons"]) == s:
                    btn.set_active(True)            # the chosen one stays chosen
            b.connect("toggled", toggled)
            flow.add(b)
            buttons[sid] = b
        self.controls[path] = (buttons, "folderstyle")
        return flow

    def _draw_folder_style_images(self, t: dict[str, str]) -> None:
        """Each style's folder, in the folder colors now set (redrawn with the preview)."""
        px = self.FOLDER_STYLE_PX
        for sid, img in getattr(self, "folder_style_images", {}).items():
            spec = icons.STYLES[sid]
            size = min((s for s in spec["sizes"] if s >= px), default=max(spec["sizes"]))
            f = icons.source_dir(sid) / str(size) / "folder.svg"
            if not f.exists():
                continue
            c = icons.colours(t, {**self.data["icons"], "style": sid})
            loader = GdkPixbuf.PixbufLoader()
            loader.set_size(px, px)
            try:
                loader.write(icons.recolour(f.read_text(encoding="utf-8"), c, sid).encode())
                loader.close()
                img.set_from_pixbuf(loader.get_pixbuf())
            except GLib.Error:
                pass

    def _draw_glyph_images(self, color: str) -> None:
        """Our glyph sets in the text colour, for the picker (redrawn when it changes)."""
        folder = paths.cache_dir() / "glyphs"
        folder.mkdir(parents=True, exist_ok=True)
        for gid, imgs in getattr(self, "glyph_images", {}).items():
            if gid == "icons":
                continue
            for fn, img in imgs:
                f = folder / f"{gid}-{fn}-{color.lstrip('#')}.svg"
                if not f.exists():
                    f.write_text(titlebuttons.glyph_svg(titlebuttons.GLYPH_SETS[gid][fn], color, 16),
                                 encoding="utf-8")
                img.set_from_file(str(f))

    def _theme_tab(self, grid: Gtk.Grid) -> Gtk.Grid:
        """The Theme tab: your themes and the built-in ones, to pick, save and rename."""
        grid.set_vexpand(True)
        self._theme_rows(grid, 0)
        return grid

    def _theme_rows(self, grid: Gtk.Grid, row: int) -> int:
        head = Gtk.Label(xalign=0)
        head.set_markup("<b>{}</b>".format(GLib.markup_escape_text(_("Theme"))))
        grid.attach(head, 0, row, 1, 1)
        grid.attach(self._sort_combo("theme_sort", self.fill_theme_list), 1, row, 1, 1)
        self.theme_list = Gtk.ListBox(selection_mode=Gtk.SelectionMode.SINGLE)
        self.theme_list.connect("row-selected", self.on_theme_selected)
        # the tab's own: as tall as the other tabs leave room for
        scroller = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER, min_content_height=300,
                                      vexpand=True)
        scroller.get_style_context().add_class("frame")
        scroller.add(self.theme_list)
        grid.attach(scroller, 0, row + 1, 2, 1)
        buttons = Gtk.Box(spacing=6)
        self.save_btn = Gtk.Button(label=_("Save Theme…"))
        self.save_btn.set_tooltip_text(_("Keep your Custom settings as a theme with its own name"))
        self.save_btn.connect("clicked", self.on_save_theme)
        self.dup_btn = Gtk.Button(label=_("Duplicate"))
        self.dup_btn.set_tooltip_text(_("Save a copy of the selected theme as one of your themes"))
        self.dup_btn.connect("clicked", self.on_duplicate_theme)
        self.rename_btn = Gtk.Button(label=_("Rename"))
        self.rename_btn.set_tooltip_text(_("Rename one of your themes (built-in themes keep their names)"))
        self.rename_btn.connect("clicked", self.on_rename_theme)
        self.delete_btn = Gtk.Button(label=_("Delete"))
        self.delete_btn.connect("clicked", self.on_delete_theme)
        buttons.pack_start(self.save_btn, False, False, 0)
        buttons.pack_start(self.dup_btn, False, False, 0)
        buttons.pack_start(self.rename_btn, False, False, 0)
        buttons.pack_start(self.delete_btn, False, False, 0)
        grid.attach(buttons, 0, row + 2, 2, 1)
        return row + 3

    def _row(self, title: str, subtitle: str = "", tag: str = "") -> Gtk.ListBoxRow:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, margin=8)
        top = Gtk.Box(spacing=8)
        name = Gtk.Label(xalign=0, ellipsize=Pango.EllipsizeMode.END, max_width_chars=NAME_CHARS)
        name.set_markup(f"<b>{GLib.markup_escape_text(title)}</b>")
        if len(title) > NAME_CHARS:
            name.set_tooltip_text(title)
        top.pack_start(name, False, False, 0)
        if tag:
            t = Gtk.Label(label=tag)
            t.get_style_context().add_class("dim-label")
            top.pack_start(t, False, False, 0)
        box.pack_start(top, False, False, 0)
        if subtitle:
            sub = Gtk.Label(label=subtitle, xalign=0, wrap=True, max_width_chars=50)
            sub.get_style_context().add_class("dim-label")
            box.pack_start(sub, False, False, 0)
        r = Gtk.ListBoxRow()
        r.add(box)
        r.subtitle_label = box.get_children()[-1] if subtitle else None
        return r

    def _sort_combo(self, key: str, refill) -> Gtk.Widget:
        """"Sort: A-Z" dropdown for a list; the choice is remembered."""
        box = Gtk.Box(spacing=6, halign=Gtk.Align.END)
        box.pack_start(Gtk.Label(label=_("Sort:")), False, False, 0)
        combo = Gtk.ComboBoxText()
        for sid, label in SORTS:
            combo.append(sid, label)
        combo.set_active_id(self.prefs.get(key, SORT_DEFAULTS.get(key, "az")))

        def changed(c: Gtk.ComboBoxText) -> None:
            self.prefs[key] = c.get_active_id()
            _save_prefs(self.prefs)
            refill()
        combo.connect("changed", changed)
        box.pack_start(combo, False, False, 0)
        return box

    def fill_theme_list(self) -> None:
        self.syncing = True
        for r in self.theme_list.get_children():
            self.theme_list.remove(r)
        items = [(name, _theme_age(f, builtin), f, builtin) for name, f, builtin in themes.list_themes()]
        for name, _m, _f, builtin in _sorted(items, self.prefs.get("theme_sort", SORT_DEFAULTS["theme_sort"])):
            r = self._row(name, tag="" if builtin else _("Your theme"))
            r.theme_name, r.builtin = name, builtin
            self.theme_list.add(r)
        r = self._row(_(themes.CUSTOM), self._custom_subtitle())      # always last
        r.theme_name, r.builtin = themes.CUSTOM, False
        self.custom_sub = r.subtitle_label
        self.theme_list.add(r)
        self.theme_list.show_all()
        for r in self.theme_list.get_children():
            if r.theme_name == self.data["theme"]:
                self.theme_list.select_row(r)
        self.syncing = False

    def _custom_subtitle(self) -> str:
        base = themes.based_on()
        return _("Your latest changes, based on {theme}").format(theme=base) if base else _("Your latest changes")

    def refresh_custom_subtitle(self) -> None:
        if self.custom_sub is not None:
            self.custom_sub.set_text(self._custom_subtitle())

    def _style_rows(self, grid: Gtk.Grid, row: int) -> int:
        head = Gtk.Label(xalign=0)
        head.set_markup("<b>{}</b>".format(GLib.markup_escape_text(_("Style"))))
        grid.attach(head, 0, row, 1, 1)
        grid.attach(self._sort_combo("style_sort", self.fill_style_list), 1, row, 1, 1)
        self.style_list = Gtk.ListBox(selection_mode=Gtk.SelectionMode.SINGLE)
        self.style_list.connect("row-selected", self.on_style_selected)
        scroller = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER, min_content_height=260,
                                      vexpand=True)   # fills the tab, as the Theme list
        scroller.get_style_context().add_class("frame")
        scroller.add(self.style_list)
        grid.attach(scroller, 0, row + 1, 2, 1)
        self.fill_style_list()
        return row + 2

    def fill_style_list(self) -> None:
        """Every style (yours first if a name is in both), sorted as chosen."""
        self.syncing = True
        for r in self.style_list.get_children():
            self.style_list.remove(r)
        builtin_dir = (paths.data_dir() / "styles").resolve()
        seen, items = set(), []
        for base in paths.style_dirs():
            if not base.is_dir():
                continue
            for d in sorted(base.iterdir()):
                try:
                    st = styles.load(d)
                except (styles.StyleError, OSError):
                    continue
                if st.name in seen:
                    continue
                seen.add(st.name)
                yours = builtin_dir not in d.resolve().parents and d.resolve().parent != builtin_dir
                items.append((st.name, (d / "style.toml").stat().st_mtime, st, yours))
        for name, _m, st, yours in _sorted(items, self.prefs.get("style_sort", "az")):
            r = self._row(name, st.description or "", _("Your style") if yours else "")
            r.style_name = name
            self.style_list.add(r)
        self.style_list.show_all()
        for r in self.style_list.get_children():
            if r.style_name == self.data["style"]["name"]:
                self.style_list.select_row(r)
        self.syncing = False

    def _terminal_picks(self, grid: Gtk.Grid, row: int) -> int:
        combo = Gtk.ComboBoxText()
        combo.append("default", _("Theme default"))
        for f in sorted((paths.builtin_presets_dir() / "terminal").glob("*.json")):
            combo.append(str(f), json.loads(f.read_text(encoding="utf-8")).get("name", f.stem))
        self.term_combo = combo

        def picked(c: Gtk.ComboBoxText) -> None:
            if self.syncing or not c.get_active_id():
                return
            if c.get_active_id() == "default":
                self.reset_section("terminal")
            else:
                preset = json.loads(Path(c.get_active_id()).read_text(encoding="utf-8"))
                for key in ("bg", "text"):
                    _set(self.data, ("terminal", key), preset["terminal"][key])
                self.data["terminal"]["separate_colors"] = True
                self.after_change()
        combo.connect("changed", picked)
        grid.attach(Gtk.Label(label=_("Colors"), xalign=0), 0, row, 1, 1)
        grid.attach(combo, 1, row, 1, 1)
        return row + 1

    ICON_PREVIEW = ("folder", "user-home", "folder-documents", "folder-download", "folder-music",
                    "folder-pictures", "folder-videos", "folder-drag-accept")

    def _icon_preview_row(self, grid: Gtk.Grid, row: int) -> int:
        """The folders in the chosen colors, at 48 and 24px (drawn here, before Apply)."""
        note = Gtk.Label(label=ICON_NOTE, xalign=0, wrap=True, max_width_chars=60, margin_start=16, hexpand=True)
        self.icon_note = note
        note.get_style_context().add_class("dim-label")
        grid.attach(note, 0, row, 2, 1)
        self.icon_images = []
        # 48px in two rows of four; 24px in one row, without the plain folder
        lines = [(48, self.ICON_PREVIEW[:4]), (48, self.ICON_PREVIEW[4:]), (24, self.ICON_PREVIEW[1:])]
        for i, (size, names) in enumerate(lines):
            box = Gtk.Box(spacing=10, margin_top=10 if i != 1 else 0, margin_start=16)
            for name in names:
                img = Gtk.Image()
                img.set_tooltip_text(name)
                box.pack_start(img, False, False, 0)
                self.icon_images.append((img, name, size))
            grid.attach(box, 0, row + 1 + i, 2, 1)
        return row + 1 + len(lines)

    def _update_icon_preview(self, t: dict[str, str]) -> None:
        if not getattr(self, "icon_images", None):
            return
        self._draw_folder_style_images(t)
        c = icons.colours(t, self.data["icons"])
        style = icons.style_of(self.data["icons"])
        for img, name, size in self.icon_images:
            f = icons.source_dir(style) / str(size) / f"{icons.aliases(style).get(name, name) if not (icons.source_dir(style) / str(size) / f'{name}.svg').exists() else name}.svg"
            if not f.exists():
                img.clear()
                continue
            loader = GdkPixbuf.PixbufLoader()
            try:
                loader.write(icons.recolour(f.read_text(encoding="utf-8"), c, style).encode())
                loader.close()
                img.set_from_pixbuf(loader.get_pixbuf())
            except GLib.Error:
                pass

    def _scan_dialog(self) -> None:
        """Scan my apps: the apps in the menu by kind, and whether Theme Roller
        reaches each kind with the switches as they are now (appscan.py)."""
        from . import appscan
        result = appscan.scan()
        integ = self.data["integration"]
        adw = integ.get("libadwaita", "colors")
        on = lambda v: _("On") if v else _("Off: switch it on in the Integration tab")  # noqa: E731
        groups = [
            (appscan.GTK3, _("Follow the theme on their own"), _("Nothing to do: they always match.")),
            (appscan.GNOME, _("GNOME-style apps"),
             {"off": _("Off: set GNOME-style apps to Colors in the Integration tab"), "colors": _("Colors on"),
              "full": _("Colors and full styling on")}[adw]),
            (appscan.FLATPAK, _("Flatpak apps"),
             on(integ.get("flatpak_access")) + ("" if adw != "off" else
                                                 _(". GNOME-style ones also need GNOME-style apps set to Colors"))),
            (appscan.QT, _("Qt apps"), on(integ.get("qt_colors")) + (f". {qt.missing()}" if qt.missing() else "")),
            (appscan.EDITOR, _("Text editors"), on(integ.get("editor_colors"))),
            (appscan.TERMINAL, _("Run in a terminal"), _("They use the terminal's colors (Terminal tab).")),
            (appscan.WEB, _("Web-based apps"), _("They draw their own look; no theme reaches them.")),
            (appscan.UNKNOWN, _("Couldn't tell"), _("Many of these draw their own look.")),
        ]
        dialog = Gtk.Dialog(title=_("Your apps"), transient_for=self, modal=True)
        dialog.add_button(_("Close"), Gtk.ResponseType.CLOSE)
        dialog.set_default_size(520, 520)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4, margin=14)
        total = len(result.apps)
        head = Gtk.Label(xalign=0, wrap=True, max_width_chars=60)
        head.set_text(_("{count} apps in your menu, by kind. Changes show after Apply, in apps opened "
                        "afterwards.").format(count=total))
        box.pack_start(head, False, False, 6)
        for kind, title, status in groups:
            apps = result.by_kind(kind)
            if not apps:
                continue
            t = Gtk.Label(xalign=0, margin_top=8)
            t.set_markup(f"<b>{GLib.markup_escape_text(title)}</b>  ({len(apps)})")
            box.pack_start(t, False, False, 0)
            st = Gtk.Label(label=status, xalign=0, wrap=True, max_width_chars=60)
            box.pack_start(st, False, False, 0)
            names = ", ".join(a.name + (f" ({_(a.detail)})" if a.detail else "") for a in apps)
            lst = Gtk.Label(label=names, xalign=0, wrap=True, max_width_chars=60, selectable=True)
            lst.get_style_context().add_class("dim-label")
            box.pack_start(lst, False, False, 0)
        scroller = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER, vexpand=True)
        scroller.add(box)
        dialog.get_content_area().pack_start(scroller, True, True, 0)
        dialog.show_all()
        dialog.run()
        dialog.destroy()

    def _set_aside_row(self, grid: Gtk.Grid, row: int) -> int:
        """Take our extra colors out of apps now, without changing any setting."""
        button = Gtk.Button(label=_("Take colors out of apps"), halign=Gtk.Align.START, margin_top=8)

        def clicked(_b: Gtk.Button) -> None:
            watch.set_aside()
            self.status.set_text(_("Theme Roller's colors are out of your apps. Reopen open apps. "
                                   "The next Apply puts them back."))
        button.connect("clicked", clicked)
        button.set_tooltip_text(_("Removes Theme Roller's colors from all apps now. Your settings and the "
                                  "theme stay; the next Apply puts the colors back."))
        grid.attach(button, 0, row, 2, 1)
        return row + 1

    def _image_colors_row(self, grid: Gtk.Grid, row: int) -> int:
        """Colors from a picture: the wallpaper or any image. Its main colors
        show as swatches, the best one becomes the accent; any swatch can be
        clicked instead. Background and text stay as they are."""
        label = Gtk.Label(label=_("Colors from"), xalign=0)
        holder = Gtk.Box(valign=Gtk.Align.START)          # as tall as the buttons, so it lines up
        holder.pack_start(label, False, False, 0)
        grid.attach(holder, 0, row, 1, 1)
        box = Gtk.Box(spacing=6)
        column = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        column.pack_start(box, False, False, 0)
        wall = Gtk.Button(label=_("Wallpaper"))
        wall.set_tooltip_text(_("Take an accent from your desktop wallpaper"))
        wall.connect("clicked", lambda _b: self._colors_from(imagecolors.wallpaper()))
        pick = Gtk.Button(label=_("Image…"))
        pick.set_tooltip_text(_("Take an accent from any picture"))
        pick.connect("clicked", self.on_pick_image)
        box.pack_start(wall, False, False, 0)
        box.pack_start(pick, False, False, 0)
        # the picture's colors go under the buttons (beside them they widened the
        # window); hidden until there are some
        self.image_swatches = Gtk.Box(spacing=3, halign=Gtk.Align.START)
        self.image_swatches.get_style_context().add_class("linked")
        self.image_swatches.set_no_show_all(True)
        column.pack_start(self.image_swatches, False, False, 0)
        same = Gtk.SizeGroup(mode=Gtk.SizeGroupMode.VERTICAL)
        same.add_widget(holder)
        same.add_widget(box)
        self._colors_from_group = same
        grid.attach(column, 1, row, 1, 1)
        return row + 1

    def on_pick_image(self, _button: Gtk.Button) -> None:
        chooser = Gtk.FileChooserNative.new(_("Take colors from a picture"), self, Gtk.FileChooserAction.OPEN,
                                            _("Use"), _("Cancel"))
        images = Gtk.FileFilter()
        images.set_name(_("Pictures"))
        images.add_pixbuf_formats()
        chooser.add_filter(images)
        pictures = GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_PICTURES)
        if pictures:
            chooser.set_current_folder(pictures)
        if chooser.run() == Gtk.ResponseType.ACCEPT:
            self._colors_from(Path(chooser.get_filename()))
        chooser.destroy()

    def _colors_from(self, path: Path | None) -> None:
        if path is None:
            self.status.set_text(_("Couldn't find your wallpaper (Cinnamon's background setting has no picture)."))
            return
        try:
            found = imagecolors.colors(path)
        except GLib.Error as exc:
            self.say(_("Couldn't read {file}: {problem}").format(file=_short_name(path.name), problem=exc.message), "error")
            return
        for child in self.image_swatches.get_children():
            self.image_swatches.remove(child)
        for color in found:
            b = Gtk.Button()
            b.set_tooltip_text(_("Use {color} as the accent").format(color=color))
            swatch = Gtk.DrawingArea()
            swatch.set_size_request(22, 16)
            rgba = Gdk.RGBA()
            rgba.parse(color)
            swatch.connect("draw", lambda _w, cr, c=rgba: (Gdk.cairo_set_source_rgba(cr, c), cr.paint()))
            b.add(swatch)
            b.connect("clicked", lambda _b, c=color: self._use_accent(c))
            self.image_swatches.pack_start(b, False, False, 0)
        for child in self.image_swatches.get_children():
            child.show_all()
        self.image_swatches.set_visible(bool(found))
        best = imagecolors.accent(found)
        if best:
            self._use_accent(best)
            self.status.set_text(_("Accent from {file}. Or click another color.").format(file=_short_name(path.name)))
        else:
            self.status.set_text(_("{file} has no colors vivid enough for an accent.").format(file=_short_name(path.name)))

    def _use_accent(self, color: str) -> None:
        self.changed(("global", "accent"), color)
        self.sync_controls()          # the Accent button shows the new color

    def _about_tab(self, grid: Gtk.Grid) -> Gtk.Grid:
        """As the About boxes of xl_cheese's other apps: centred, name, version,
        what it does, the website, copyright and licence."""
        from . import __version__
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10, hexpand=True,
                      halign=Gtk.Align.CENTER, margin_top=12)
        icon = paths.data_dir() / "data" / "icons" / "xl-cheeselooks-256.png"
        if icon.exists():
            pix = GdkPixbuf.Pixbuf.new_from_file_at_scale(str(icon), 128, 128, True)
            box.pack_start(Gtk.Image.new_from_pixbuf(pix), False, False, 0)

        def line(markup: str, dim: bool = False, top: int = 0) -> None:
            label = Gtk.Label(justify=Gtk.Justification.CENTER, wrap=True, max_width_chars=60,
                              margin_top=top)
            label.set_markup(markup)
            if dim:
                label.get_style_context().add_class("dim-label")
            box.pack_start(label, False, False, 0)
        line(f"<span size='large' weight='bold'>{APP_TITLE}</span>")
        line(GLib.markup_escape_text(__version__))
        line(GLib.markup_escape_text(_(
            "The xl-Cheeselooks theme maker for Linux Mint and the Cinnamon desktop: your colors and shapes, "
            "drawn by a style, for GTK 3 and GTK 4 apps, libadwaita apps, the Cinnamon panel and menus, and "
            "the window borders.")))
        box.pack_start(Gtk.LinkButton(uri=REPO_URL, label=_("Website"), halign=Gtk.Align.CENTER),
                       False, False, 0)
        if TIP_URL:
            line("<small>{}</small>".format(GLib.markup_escape_text(
                _("Enjoying {app}? It's free and always will be.").format(app=APP_TITLE))), dim=True, top=2)
            tip = Gtk.Button(label=_("Leave a tip ☕"), halign=Gtk.Align.CENTER, tooltip_text=TIP_URL)
            tip.get_style_context().add_class("suggested-action")     # an accent button, in your theme
            tip.connect("clicked", lambda b: Gtk.show_uri_on_window(self, TIP_URL, Gtk.get_current_event_time()))
            box.pack_start(tip, False, False, 0)
        line("<small>Copyright © 2026 Wesley Hayslip\n{}</small>".format(GLib.markup_escape_text(
            _("Developed with the help of Claude, an AI assistant by Anthropic"))))
        line("<small>{}</small>".format(_(
            "This program comes with absolutely no warranty.\n"
            "See the <a href='https://www.gnu.org/licenses/gpl-3.0.html'>GNU General Public License, "
            "version 3 or later</a> for details.")), top=4)
        # before uninstalling: a package can't tidy your home folder, so this does
        remove = Gtk.Button(label=_("Remove from my desktop…"), halign=Gtk.Align.CENTER, margin_top=10)
        remove.set_tooltip_text(_("Before uninstalling Theme Roller: puts Mint's default theme back and "
                                  "takes Theme Roller's colors out of your apps"))
        remove.connect("clicked", self.on_remove)
        box.pack_start(remove, False, False, 0)
        grid.attach(box, 0, 0, 1, 1)
        return grid

    def on_remove(self, _button: Gtk.Button) -> None:
        """Theme Roller off the desktop (remove.py), after asking."""
        d = Gtk.MessageDialog(transient_for=self, modal=True, message_type=Gtk.MessageType.QUESTION,
                              buttons=Gtk.ButtonsType.OK_CANCEL,
                              text=_("Remove Theme Roller from your desktop?"))
        d.format_secondary_text(_(
            "Mint's default theme comes back, Theme Roller's colors leave your apps, and the theme "
            "watcher stops starting at login. Your settings and your own themes stay, so you can pick "
            "up where you left off. Do this before uninstalling Theme Roller."))
        answer = d.run()
        d.destroy()
        if answer != Gtk.ResponseType.OK:
            return
        self.status.set_text(_("Removing… the desktop flickers once while it reloads."))

        def work() -> None:
            from . import remove
            try:
                remove.remove()
                GLib.idle_add(self.status.set_text, _(
                    "Theme Roller is off your desktop. You can uninstall it now; Apply puts it back."))
            except Exception as exc:  # report anything to the user
                GLib.idle_add(self.say, _("Remove failed: {problem}").format(problem=exc), "error")
        threading.Thread(target=work, daemon=True).start()

    def _docs_tab(self, grid: Gtk.Grid) -> Gtk.Grid:
        row = 0
        for title, body in DOC_NOTES:
            head = Gtk.Label(xalign=0, margin_top=0 if row == 0 else 6)
            head.set_markup(f"<b>{title}</b>")
            grid.attach(head, 0, row, 1, 1)
            text = Gtk.Label(xalign=0, wrap=True, max_width_chars=64)
            text.set_markup(body)
            grid.attach(text, 0, row + 1, 1, 1)
            row += 2
            if title == _("Style"):    # the starter style sheet and the check, with what they're about (xl_cheese)
                buttons = Gtk.Box(spacing=8, halign=Gtk.Align.START, margin_top=4)
                starter = Gtk.Button(label=_("Create a starter style…"))
                starter.connect("clicked", self.on_starter_style)
                check = Gtk.Button(label=_("Check a style sheet for issues…"))
                check.set_tooltip_text(_("Pick a style.toml: it's checked as Theme Roller reads it, and any "
                                         "problems are listed with what to fix"))
                check.connect("clicked", self.on_check_style)
                buttons.pack_start(starter, False, False, 0)
                buttons.pack_start(check, False, False, 0)
                grid.attach(buttons, 0, row, 1, 1)
                row += 1
        link = Gtk.LinkButton(uri=DOCS_URL, label=_("Full documentation (online)"), halign=Gtk.Align.START,
                              margin_top=12)
        grid.attach(link, 0, row, 1, 1)
        return grid

    def on_check_style(self, _button: Gtk.Button) -> None:
        """Check a style sheet: the same check as `theme-roller check-style`,
        its result in a window (xl_cheese: most people won't use a terminal)."""
        chooser = Gtk.FileChooserDialog(title=_("Check a style sheet"), transient_for=self,
                                        action=Gtk.FileChooserAction.OPEN)
        chooser.add_buttons(_("Cancel"), Gtk.ResponseType.CANCEL, _("Check"), Gtk.ResponseType.ACCEPT)
        sheets = Gtk.FileFilter()
        sheets.set_name(_("Style sheets (style.toml)"))
        sheets.add_pattern("*.toml")
        chooser.add_filter(sheets)
        yours = paths.style_dirs()[0]
        if yours.is_dir():
            chooser.set_current_folder(str(yours))
        picked = chooser.get_filename() if chooser.run() == Gtk.ResponseType.ACCEPT else None
        chooser.destroy()
        if not picked:
            return
        kind = Gtk.MessageType.INFO
        try:
            style = styles.load(Path(picked))
            title = _("“{style}” looks good").format(style=style.name)
            lines = [_("Warning: {problem}").format(problem=w) for w in style.warnings]
            if not lines:
                lines = [_("No problems found. Pick it on the Style tab to use it.")]
        except styles.StyleError as exc:
            title, kind = _("Problems to fix: {count}").format(count=len(exc.problems)), Gtk.MessageType.WARNING
            lines = list(exc.problems) + [_("Fix these in the file, then check it again.")]
        dialog = Gtk.MessageDialog(transient_for=self, modal=True, message_type=kind,
                                   buttons=Gtk.ButtonsType.CLOSE, text=title)
        dialog.format_secondary_text(f"{picked}\n\n" + "\n".join(lines))
        dialog.run()
        dialog.destroy()

    def on_starter_style(self, _button: Gtk.Button) -> None:
        """A new style of yours from the starter style sheet, then picked."""
        def check(name: str) -> str:
            name = name.strip()
            if not name:
                raise themes.ThemeError(_("the style needs a name"))
            if len(name) > themes.MAX_NAME:
                raise themes.ThemeError(_("names can be up to {count} characters").format(count=themes.MAX_NAME))
            if "/" in name or name.startswith("."):
                raise themes.ThemeError(_("names can't contain / or start with a dot"))
            try:
                styles.find(name, paths.style_dirs())
            except styles.StyleError:
                return name
            raise themes.ThemeError(_("there's already a style called {name}").format(name=name))
        name = self._ask_name(_("Create Style"), _("Give your new style a good name."), _("My Style"),
                              check, button=_("Create"))
        if not name:
            return
        folder = paths.style_dirs()[0] / name
        folder.mkdir(parents=True, exist_ok=True)
        template = (paths.data_dir() / "data" / "style-template.toml").read_text(encoding="utf-8")
        (folder / "style.toml").write_text(template.replace("{{name}}", name), encoding="utf-8")
        self.fill_style_list()
        self.status.set_text(_("Created {file}. Edit it, then pick it on the Style tab.").format(file=folder / "style.toml"))
        try:
            Gtk.show_uri_on_window(self, folder.as_uri(), Gdk.CURRENT_TIME)   # opens the folder
        except GLib.Error:
            pass

    def _share_tab(self, grid: Gtk.Grid) -> Gtk.Grid:
        text = Gtk.Label(xalign=0, wrap=True, max_width_chars=60)
        text.set_text(_("Share a theme as one file (.xltheme). It holds every setting, the theme's name, "
                        "the version of Theme Roller it was made with, and your style when the theme "
                        "uses one of your own, so the person importing it gets exactly your look."))
        grid.attach(text, 0, 0, 2, 1)
        export = Gtk.Button(label=_("Export the current theme…"), halign=Gtk.Align.START)
        export.connect("clicked", self.on_export)
        imp = Gtk.Button(label=_("Import a theme…"), halign=Gtk.Align.START)
        imp.connect("clicked", self.on_import)
        grid.attach(export, 0, 1, 2, 1)
        grid.attach(imp, 0, 2, 2, 1)
        return grid

    # --------------------------------------------------------------- preview
    def _preview(self) -> Gtk.Widget:
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10, margin=10)
        # as wide as its widest row (the buttons up to Toggled): no wider
        frame = Gtk.Frame()
        frame.get_style_context().add_class("xl-prev-window")
        win = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        hb = Gtk.HeaderBar(show_close_button=True, title=_("Preview"))
        self.prev_hb = hb
        hb.get_style_context().add_class("titlebar")
        win.pack_start(hb, False, False, 0)
        menubar = Gtk.MenuBar()
        for name in (_("File"), _("Edit"), _("View")):
            item = Gtk.MenuItem(label=name)
            sub = Gtk.Menu()
            for entry in (_("Open"), _("Save"), _("Quit")):
                sub.append(Gtk.MenuItem(label=entry))
            item.set_submenu(sub)
            menubar.append(item)
        win.pack_start(menubar, False, False, 0)
        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8, margin=10)
        buttons = Gtk.Box(spacing=6)
        for label, cls in ((_("Button"), None), (_("Suggested"), "suggested-action"),
                           (_("Delete"), "destructive-action")):
            b = Gtk.Button(label=label)
            b.set_tooltip_text(_("A tooltip on {button}").format(button=label))   # hover for the real thing
            if cls:
                b.get_style_context().add_class(cls)
            buttons.pack_start(b, False, False, 0)
        toggled = Gtk.ToggleButton(label=_("Toggled"), active=True)
        toggled.set_tooltip_text(_("A tooltip on {button}").format(button=_("Toggled")))
        buttons.pack_start(toggled, False, False, 0)
        body.pack_start(buttons, False, False, 0)
        linked = Gtk.Box()
        linked.get_style_context().add_class("linked")
        for i, label in enumerate((_("Left"), _("Center"), _("Right"))):
            linked.pack_start(Gtk.ToggleButton(label=label, active=(i == 1)), False, False, 0)
        row = Gtk.Box(spacing=10)
        row.pack_start(linked, False, False, 0)
        row.pack_start(Gtk.Entry(text=_("Some text"), width_chars=8), True, True, 0)   # fills, never widens
        body.pack_start(row, False, False, 0)
        # a drawn tooltip, always visible, in the Details tab's tooltip colours
        row = Gtk.Box(spacing=10)
        tip = Gtk.Label(label=_("Tooltip"), valign=Gtk.Align.CENTER)
        tip.get_style_context().add_class("xl-prev-tooltip")
        row.pack_start(tip, False, False, 0)
        row.pack_start(Gtk.Switch(active=True, valign=Gtk.Align.CENTER), False, False, 0)
        row.pack_start(Gtk.CheckButton(label=_("Check"), active=True), False, False, 0)
        row.pack_start(Gtk.RadioButton(label=_("Radio")), False, False, 0)
        body.pack_start(row, False, False, 0)
        scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        scale.set_value(60)
        scale.set_draw_value(False)
        # beside the slider, a spin button (the style's spin_gap); at its lowest,
        # so its − shows the disabled look too
        row = Gtk.Box(spacing=10)
        row.pack_start(scale, True, True, 0)
        spin = Gtk.SpinButton.new_with_range(0, 99, 1)
        spin.set_width_chars(2)
        spin.set_valign(Gtk.Align.CENTER)
        row.pack_start(spin, False, False, 0)
        body.pack_start(row, False, False, 0)
        notebook = Gtk.Notebook()
        for name in (_("General"), _("Colors"), _("Advanced")):
            lb = Gtk.ListBox()
            for text in (_("First row"), _("Selected row"), _("Third row"), _("Fourth row"), _("Fifth row"),
                         _("Sixth row"), _("Seventh row"), _("Eighth row")):
                lb.add(Gtk.Label(label=text, xalign=0, margin=6))
            lb.select_row(lb.get_row_at_index(1))
            # a few rows more than fit, so the scrollbar shows (Details: Scrollbars)
            rows = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER, min_content_height=104)
            rows.add(lb)
            notebook.append_page(rows, Gtk.Label(label=name))
        body.pack_start(notebook, False, False, 0)
        term = Gtk.Label(label="user@mint:~$ ls\n" + _("Desktop  Documents  Music"), xalign=0, margin=6)
        term.get_style_context().add_class("xl-prev-terminal")
        body.pack_start(term, False, False, 0)
        win.pack_start(body, False, False, 0)
        frame.add(win)
        outer.pack_start(frame, False, False, 0)
        # Cinnamon's main menu, open above its panel button (Menu style)
        menu = Gtk.Box(spacing=6, halign=Gtk.Align.START, margin_start=4)
        menu.get_style_context().add_class("xl-prev-menu")
        favs = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        favs.get_style_context().add_class("xl-prev-favs")
        for icon in ("web-browser-symbolic", "folder-symbolic", "utilities-terminal-symbolic"):
            fb = Gtk.Label()
            fb.set_markup("●")
            fb.get_style_context().add_class("xl-prev-fav")
            favs.pack_start(fb, False, False, 0)
        menu.pack_start(favs, False, False, 0)
        for column in ((N_("Favorites"), N_("Accessories"), N_("Graphics")),
                       (N_("Calculator"), N_("Files"), N_("Terminal"))):
            col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
            for name in column:
                item = Gtk.Label(label=_(name), xalign=0)
                item.get_style_context().add_class("xl-prev-mitem")
                if name == "Favorites":
                    item.get_style_context().add_class("selected")
                if name == "Files":
                    item.get_style_context().add_class("hover")
                col.pack_start(item, False, False, 0)
            menu.pack_start(col, False, False, 0)
        caption = Gtk.Label(label=_("Panel and menu (drawn preview)"), xalign=0)
        caption.get_style_context().add_class("dim-label")
        outer.pack_start(caption, False, False, 0)
        desk = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)     # the menu sits on the panel
        desk.pack_start(menu, False, False, 0)
        outer.pack_start(desk, False, False, 0)
        panel = Gtk.Box(spacing=2)
        panel.get_style_context().add_class("xl-prev-panel")
        mbtn = Gtk.ToggleButton(label=_("Menu"))
        mbtn.get_style_context().add_class("xl-prev-pb")
        panel.pack_start(mbtn, False, False, 0)
        for i, name in enumerate((_("Terminal"), _("Files"), _("Browser"))):
            b = Gtk.ToggleButton(label=name)
            b.get_style_context().add_class("xl-prev-pb")
            if i == 1:
                b.get_style_context().add_class("focused")
            panel.pack_start(b, False, False, 0)
        panel.pack_end(Gtk.Label(label="12:00", margin_end=8), False, False, 0)
        desk.pack_start(panel, False, False, 0)
        scroller = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER)
        scroller.add(outer)
        return scroller

    STATUS_ICONS = {"info": "dialog-information-symbolic", "done": "object-select-symbolic",
                    "attention": "dialog-warning-symbolic", "error": "dialog-error-symbolic"}

    def say(self, text: str, kind: str = "info") -> bool:
        """Show a message on the status line: kind is info, done, attention or error."""
        self._status_kind = kind
        if self.status.get_text() == text:
            self._status_changed()          # the same words again: still show it as new
        self.status.set_text(text)
        return False

    def _status_changed(self, *_args) -> None:
        kind, self._status_kind = self._status_kind or "info", None
        ctx = self.status_bar.get_style_context()
        for k in self.STATUS_ICONS:
            ctx.remove_class(k)
        shown = bool(self.status.get_text())
        self.status_icon.set_visible(shown)
        if not shown:
            return
        ctx.add_class(kind)
        self.status_icon.set_from_icon_name(self.STATUS_ICONS[kind], Gtk.IconSize.MENU)
        # the glow: on at once, then off so it fades out (the CSS transition)
        ctx.add_class("fresh")
        self._status_glow += 1
        glow = self._status_glow

        def fade() -> bool:
            if glow == self._status_glow:
                ctx.remove_class("fresh")
            return False
        GLib.timeout_add(700, fade)

    def _extra_css(self, t: dict[str, str]) -> str:
        """The drawn panel and the terminal sample, from the same tokens."""
        pb = "panel.w.panel_button."
        kind = t.get(pb + "active_marker", "none")
        marker = "none"
        if kind != "none":     # the focused window's marker, as the real panel draws it
            color = t["panel.accent_press"] if t[pb + "selected_color"] == t["panel.accent"] else t["panel.accent"]
            marker = panelmarker.shadow(kind, color, 28)
        return f"""
.xl-status {{ padding: 3px 8px; border-radius: {t['r']}px;
  transition: background-color 1200ms ease-out; }}
.xl-status label {{ color: {pal.mix(t['text'], t['bg'], 0.25)}; }}
.xl-status.fresh {{ background-color: {pal.rgba(t['accent'], 0.20)}; transition: none; }}
.xl-status.attention {{ background-color: {pal.rgba(t['accent'], 0.13)}; }}
.xl-status.attention label {{ color: {t['text']}; }}
.xl-status.attention image, .xl-status.done image {{ color: {t['accent']}; }}
.xl-status.error {{ background-color: {pal.rgba(t['destructive'], 0.15)}; }}
.xl-status.error label {{ color: {t['text']}; }}
.xl-status.error image {{ color: {t['destructive']}; }}
.xl-prev-panel {{ background-color: rgba({t['panel.panel_rgb']}, {t['panel.opacity']});
  background-image: linear-gradient(to bottom, rgba({t['panel.panel_top_rgb']}, {t['panel.opacity']}),
  rgba({t['panel.panel_bottom_rgb']}, {t['panel.opacity']}));
  border-top: 1px solid {t['panel.border']}; padding: 3px 4px; color: {t['panel.text']}; }}
.xl-prev-panel label {{ color: {t['panel.text']}; font-weight: {t['panel.label_weight']}; }}
.xl-prev-menu {{ color: {t['menu.text']}; background-color: rgba({t['menu.menu_bg_rgb']}, {t['menu.opacity']});
  border: 1px solid {pal.rgba(t['menu.border'], 0.9)}; border-radius: {t['menu.r2']}px {t['menu.r2']}px 0 0;
  border-bottom-width: 0; padding: 8px; }}
.xl-prev-menu label {{ color: {t['menu.text']}; }}
.xl-prev-favs {{ background-color: {t['menu.fav_bg']}; border-radius: {t['menu.r2']}px; padding: 4px; }}
.xl-prev-fav {{ min-width: 22px; min-height: 22px; color: {pal.rgba(t['menu.text'], 0.55)}; }}
.xl-prev-mitem {{ padding: 4px 10px; min-width: 96px; border-radius: {t['menu.item_r']}px; }}
.xl-prev-mitem.hover {{ background-color: {t['menu.main_hover']};
  background-image: linear-gradient(to bottom, {t['menu.main_hover_top']}, {t['menu.main_hover_bottom']});
  box-shadow: {t['menu.main_hover_ring']}; }}
.xl-prev-mitem.hover label, label.xl-prev-mitem.hover {{ color: {t['menu.main_hover_fg']}; }}
.xl-prev-mitem.selected {{ color: {t['menu.category_fg']}; background-color: {t['menu.category']};
  background-image: linear-gradient(to bottom, {t['menu.category_top']}, {t['menu.category_bottom']});
  box-shadow: {t['menu.category_ring']}; }}
.xl-prev-mitem.selected label, label.xl-prev-mitem.selected {{ color: {t['menu.category_fg']}; }}
button.xl-prev-pb {{ min-height: {max(14, int(t['panel.height']) - 14)}px; padding: 0 {t[pb + 'padding']}px; margin-right: {t[pb + 'spacing']}px;
  border: 1px solid {t[pb + 'border']}; border-radius: {t['panel.r']}px;
  background-color: {t[pb + 'color']};
  background-image: linear-gradient(to bottom, {t[pb + 'color_top']}, {t[pb + 'color_bottom']});
  box-shadow: none; }}
button.xl-prev-pb:hover {{ border-color: {t[pb + 'hover_border']}; background-color: {t[pb + 'hover_color']};
  background-image: linear-gradient(to bottom, {t[pb + 'hover_top']}, {t[pb + 'hover_bottom']}); }}
button.xl-prev-pb.focused {{ border-color: {t[pb + 'selected_border']}; background-color: {t[pb + 'selected_color']};
  background-image: linear-gradient(to bottom, {t[pb + 'selected_top']}, {t[pb + 'selected_bottom']});
  box-shadow: {marker}; }}
button.xl-prev-pb.focused label {{ color: {t[pb + 'selected_fg']}; font-weight: {t['panel.label_weight_focus']}; }}
headerbar button.xl-drawn, headerbar button.xl-drawn label {{ color: {t['wbp.text']}; }}
headerbar button.xl-drawn:backdrop label {{ color: {pal.mix(t['wbp.text'], t['wbp.button'], 0.4)}; }}
headerbar button.xl-drawn:disabled label {{ color: {pal.mix(t['wbp.text'], t['wbp.button'], 0.5)}; }}
headerbar button.xl-drawn {{ border-color: {t['wbp.w.button.border']}; background-color: {t['wbp.button']};
  background-image: {t['wbp.button_grad']}; box-shadow: {t['wbp.w.button.shadow']}; }}
headerbar button.xl-drawn:hover {{ border-color: {t['wbp.w.button.hover_border']};
  background-color: {t['wbp.w.button.hover_color']}; background-image: {t['wbp.w.button.hover_grad']};
  box-shadow: {t['wbp.w.button.hover_shadow']}; }}
headerbar button.xl-drawn:active {{ border-color: {t['wbp.w.button.pressed_border']};
  background-color: {t['wbp.pressed']}; background-image: image({t['wbp.pressed']});
  box-shadow: {t['wbp.w.button.pressed_shadow']}; }}
label.xl-prev-tooltip {{ color: {t['tooltip.text']}; background-color: {t['tooltip.bg']};
  border: 1px solid {pal.mix(t['tooltip.bg'], t['tooltip.text'], 0.2)}; border-radius: {t['r2']}px;
  padding: 4px 8px; margin: 0 4px;
  box-shadow: 0 1px 3px 1px rgba(0, 0, 0, 0.23); }}     /* the theme's tooltip shadow (Mint-Y base) */
frame.xl-prev-window > border {{ border: {t['wb.border_width']}px solid {t['wb.border']};
  border-radius: {t['wb.r']}px {t['wb.r']}px 0 0; }}
.xl-prev-terminal {{ font-family: monospace; color: {t['term.text']}; background-color: {t['term.bg']}; padding: 6px; }}
"""

    def _style(self, data: dict) -> tuple[styles.Style, str]:
        return cli.style_or_stand_in(data)

    def update_preview(self) -> bool:
        self.pending = 0
        try:
            style, missing = self._style(self.data)
            ph = self.data["panel"]["panel_height"] or self._int_default(("panel", "panel_height"))
            t = tokens.build(self.data, style, panel_height=ph)
        except (styles.StyleError, settings.SettingsError, KeyError) as exc:
            self.say(_("Can't preview: {problem}").format(problem=exc), "error")
            return False
        if self.preview_dir.exists():
            shutil.rmtree(self.preview_dir)
        render.render_tree(paths.templates_dir(), self.preview_dir, t)
        # the preview's title bar shows all three buttons, on your side
        left = self.data["window_borders"]["button_layout"] == "left"
        self.prev_hb.set_decoration_layout("close,minimize,maximize:" if left else ":minimize,maximize,close")
        try:
            self.theme_css.load_from_path(str(self.preview_dir / "gtk-3.0" / "gtk.css"))
            self.extra_css.load_from_data(self._extra_css(t).encode())
            self._update_icon_preview(t)
            # make every widget re-read its style and size: without this GTK 3
            # sometimes kept a property the new CSS no longer sets (a Linked
            # shadow after switching back) or didn't re-measure resized title
            # buttons (Gargantuan's could vanish until the window was reopened)
            Gtk.StyleContext.reset_widgets(Gdk.Screen.get_default())
            self._scrollbar_mode(t["scrollbar.mode"] == "overlay")
            self.queue_resize()
            GLib.idle_add(self._fit_pages)          # measured in the new sizes
            GLib.timeout_add(250, self._fit_pages)  # again once restyled (the sidebar's rows lag a moment)
        except GLib.Error as exc:
            self.say(_("Preview CSS problem: {problem}").format(problem=exc.message), "error")
        if missing:
            self.status.set_text(missing)
        if self.data["theme"] == themes.CUSTOM:
            themes.save_custom(self.data, self.base)
            self.refresh_custom_subtitle()
        return False

    # tabs that may scroll: long reading, or many switches (no sliders to catch the wheel)
    SCROLLING_TABS = ("integration", "docs", "about")

    def _fit_pages(self) -> bool:
        """The window's least height: the tallest settings tab, whole. Their
        sliders take the mouse wheel, so a tab that scrolled would fight it.
        Measured again after each preview (Size changes every control's height)."""
        # at the width they get (the folder style pictures wrap at a narrow
        # one); before the window is shown, the widest tab's least width
        pages = [self.stack.get_child_by_name(n).get_child() for n, _t in TABS if n not in self.SCROLLING_TABS]
        width = self.stack.get_allocated_width()
        if width <= 1:
            width = max(p.get_preferred_width()[0] for p in pages)
        tallest = max(p.get_preferred_height_for_width(width)[1] for p in pages)
        if tallest and tallest != getattr(self, "page_height", 0):
            self.page_height = tallest
            for name, _title in TABS:
                self.stack.get_child_by_name(name).set_min_content_height(tallest)
        # ...and the sidebar's tabs, whole: above roundness 30 they're rounded,
        # spaced out, and twelve of them can outgrow the tallest tab (xl_cheese:
        # a scrollbar over them). Its scroller asks for all of its list.
        scroller = next((c for c in self.sidebar.get_children() if isinstance(c, Gtk.ScrolledWindow)), None)
        if scroller is not None and scroller.get_child() is not None:
            need = scroller.get_child().get_preferred_height()[1]
            if need != scroller.get_min_content_height():
                scroller.set_min_content_height(need)
        return False

    def _scrollbar_mode(self, overlay: bool) -> None:
        """Overlay or classic scrollbars in every scrolled window here, as the
        Scrollbars mode sets them on the desktop (GTK takes overlay scrolling
        from each scrolled window, not from CSS)."""
        def walk(widget: Gtk.Widget) -> None:
            if isinstance(widget, Gtk.ScrolledWindow):
                widget.set_overlay_scrolling(overlay)
            if isinstance(widget, Gtk.Container):
                widget.foreach(walk)
        walk(self)

    # ---------------------------------------------------------------- state
    def base_settings(self) -> dict:
        if self.base not in self.base_cache:
            try:
                self.base_cache[self.base] = themes.load(self.base)
            except themes.ThemeError:
                self.base_cache[self.base] = themes.load(settings.DEFAULTS["theme"])
        return self.base_cache[self.base]

    def changed(self, path: tuple[str, ...], value: Any) -> None:
        if self.syncing:
            return
        optional = icons.STYLES[icons.style_of(self.data["icons"])].get("second_optional")
        if path in (("icons", "folder_color"), ("icons", "second_color")) and value and not optional:
            # touch either folder color and both stop following the theme: the
            # other keeps the color it showed (xl_cheese: pick a blue front and
            # the back stays the dark red it was)
            other = "second_color" if path[-1] == "folder_color" else "folder_color"
            if not self.data["icons"].get(other):
                g = self.data["global"]
                shown = icons.colours(pal.derive(g["accent"], g["bg"], g["text"]), self.data["icons"])
                self.data["icons"][other] = shown["backfolder" if other == "second_color" else "folder"]
        _set(self.data, path, value)
        if path == ("window_borders", "button_style"):
            # a new style starts at its own roundness
            self.data["window_borders"]["button_roundness"] = None
            self.data["window_borders"]["button_spacing"] = None
        parent = _get(self.data, path[:-1])
        for gate, on in GATES.items():       # changing a setting turns its hidden switch on
            if gate in parent and path[-1] != gate:
                parent[gate] = on
        self.after_change()

    def after_change(self) -> None:
        try:
            self.data = settings.from_dict(self.data)
        except settings.SettingsError as exc:
            self.say("; ".join(exc.problems), "error")
            return
        # unchanged from the theme it started from: still that theme; else Custom
        self.data["theme"] = self.base if _same(self.data, self.base_settings()) else themes.CUSTOM
        self.sync_controls()
        self.update_buttons()
        if self.pending:
            GLib.source_remove(self.pending)
        self.pending = GLib.timeout_add(PREVIEW_DELAY_MS, self.update_preview)

    def sync_controls(self) -> None:
        """Show self.data in every control (without triggering changes)."""
        self.syncing = True
        try:
            g = self.data["global"]
            theme = pal.derive(g["accent"], g["bg"], g["text"])
            for path, (widget, kind) in self.controls.items():
                value = _get(self.data, path)
                if kind in ("color", "color?"):
                    button, label = widget
                    shown = value or self._effective_color(path, theme)
                    button.set_rgba(_rgba(shown))
                    if value is None and kind == "color?":
                        label.set_text(self._unset_label(path))
                    elif path == ("icons", "second_color") and \
                            icons.STYLES[icons.style_of(self.data["icons"])].get("second_optional"):
                        label.set_text(shown)              # room for No stripes beside it
                    else:
                        r, gg, b = pal.to_rgb(shown)
                        label.set_text(f"{shown}   rgb({r}, {gg}, {b})")
                elif kind == "int":
                    widget.set_value(value)
                elif kind == "int?":   # None shows the default in use
                    widget.set_value(self._int_default(path) if value is None else value)
                    if path[-1] == "button_spacing":     # these styles' buttons touch
                        widget.set_sensitive(self.data["window_borders"]["button_style"]
                                             not in titlebuttons.SPACING_LOCKED)
                elif kind == "bool":
                    widget.set_active(value)
                elif kind == "glyphs":
                    wb = self.data["window_borders"]
                    shown = titlebuttons.glyph_set(wb["button_style"], value)
                    for gid, b in widget.items():
                        b.set_active(gid == shown)
                    self._draw_glyph_images(self.data["global"]["text"])
                elif kind == "inline":
                    for choice, b in widget.items():
                        b.set_active(choice == value)
                elif kind == "folderstyle":
                    shown = icons.style_of(self.data["icons"])
                    for sid, b in widget.items():
                        b.set_active(sid == shown)
                else:
                    widget.set_active_id(value)
            self._update_icon_labels()
            for r in self.theme_list.get_children():
                if r.theme_name == self.data["theme"]:
                    self.theme_list.select_row(r)
            for r in self.style_list.get_children():
                if r.style_name == self.data["style"]["name"]:
                    self.style_list.select_row(r)
            if not self.data["terminal"]["separate_colors"]:
                self.term_combo.set_active_id("default")
        finally:
            self.syncing = False

    def _unset_label(self, path: tuple[str, ...]) -> str:
        """What an unset color says: "Follow theme", or for a style whose second
        color is optional (xl-Big Baddy's racing stripes), "None"."""
        if path == ("icons", "second_color") and \
                icons.STYLES[icons.style_of(self.data["icons"])].get("second_optional"):
            return _("None")
        return _("Follow theme")

    def _update_icon_labels(self) -> None:
        """The Icons switch names what it does: "Custom folder style" while
        off, the chosen style's name ("Yaru folder style") while on; the
        second color takes the style's own name for it."""
        if not hasattr(self, "icons_switch_label"):
            return
        spec = icons.STYLES[icons.style_of(self.data["icons"])]
        name = spec["name"] if self.data["icons"].get("enabled") else _("Custom")
        self.icons_switch_label.set_markup(
            _("<b>{name}</b> folder style").format(name=GLib.markup_escape_text(name)))
        self.second_color_label.set_text(_(spec["second_label"]) if spec.get("second_label") else LABELS["second_color"])
        if hasattr(self, "icon_note"):
            self.icon_note.set_text(_(spec["note"]) if spec.get("note") else ICON_NOTE)
        self.stripes_off.set_visible(bool(spec.get("second_optional") and self.data["icons"].get("second_color")))

    def _int_default(self, path: tuple[str, ...]) -> int:
        """What an unset number setting shows: button roundness, the style's own;
        panel height, Cinnamon's current height."""
        if path[-1] == "button_roundness":
            wb = self.data["window_borders"]
            return titlebuttons.roundness(wb["button_style"], None, self.data["global"]["roundness"])
        if path[:2] == ("details", "scrollbars") and path[-1] == "width":
            return 6 if self.data["details"]["scrollbars"]["mode"] == "overlay" else 10
        if path[-1] == "button_spacing":
            return titlebuttons.spacing(self.data["window_borders"]["button_style"])
        if path[-1] == "window_roundness":
            return int(self.data["global"]["roundness"])
        if path[-1] == "panel_height":
            if self.cinnamon_panel_height is None:
                self.cinnamon_panel_height = reload.panel_height(DEFAULT_PANEL_HEIGHT)
            return self.cinnamon_panel_height
        return 0

    def _effective_color(self, path: tuple[str, ...], theme: dict[str, str]) -> str:
        name = path[-1]
        if name == "title_bar":
            return theme["header"]
        if name == "bg":
            return theme["base"] if path[0] == "terminal" else theme["bg"]
        if name in ("text", "title_text"):
            return theme["text"]
        if name == "border":
            return theme["border_strong"]
        if path[:2] == ("details", "tooltips"):
            return theme["menu_bg"] if name == "bg" else theme["text"]
        if path[:2] == ("details", "focus_ring"):
            return pal.mix(theme["bg"], theme["text"], 0.25)     # the default: text at 25%
        if path == ("icons", "second_color"):                    # the default: a shade darker than the folder
            return icons.colours(theme, self.data["icons"])["backfolder"]
        return theme["accent"]

    def update_buttons(self) -> None:
        # tooltips name the theme a reset goes back to (not the labels: names can be long)
        for section, b in self.reset_btns.items():
            if section == "all":
                b.set_tooltip_text(_("Put every tab back to {theme}. Your latest changes stay in Custom.")
                                   .format(theme=self.base))
            elif section == "global":
                b.set_tooltip_text(_("Put Global back to {theme}. Other tabs keep what you set there, "
                                     "but colors on “Follow theme” and shapes that follow Global change with it.")
                                   .format(theme=self.base))
            else:
                b.set_tooltip_text(_("Put {tab} back to {theme} (other tabs stay as they are)")
                                   .format(tab=dict(TABS)[section], theme=self.base))
        # also when the desktop isn't on our theme: a new user's first open, after
        # Revert to Mint-Y, or another theme picked in Mint's settings (xl_cheese:
        # Apply was greyed out, though nothing of ours was on the desktop)
        self.apply_btn.set_sensitive(_needs_apply(self.data, self.applied) or not _on_desktop())
        self.save_btn.set_sensitive(self.data["theme"] == themes.CUSTOM)
        row = self.theme_list.get_selected_row()
        yours = bool(row) and not row.builtin and row.theme_name != themes.CUSTOM
        self.delete_btn.set_sensitive(yours)
        self.rename_btn.set_sensitive(yours)
        self.dup_btn.set_sensitive(bool(row) and row.theme_name != themes.CUSTOM)

    # -------------------------------------------------------------- actions
    def on_theme_selected(self, _list: Gtk.ListBox, row: Gtk.ListBoxRow | None) -> None:
        if self.syncing or row is None or row.theme_name == self.data["theme"]:
            self.update_buttons()
            return
        try:
            data = themes.load(row.theme_name)
        except themes.ThemeError as exc:
            self.say(str(exc), "error")
            self.sync_controls()
            return
        if row.theme_name == themes.CUSTOM:
            self.base = themes.based_on() or self.base
        else:
            self.base = row.theme_name
            self.base_cache.pop(self.base, None)
        self.data = settings.keep_per_user(data, self.data)   # your Integration switches stay
        self.status.set_text(_("Theme: {theme}").format(
            theme=_(themes.CUSTOM) if row.theme_name == themes.CUSTOM else row.theme_name))
        self.after_change()

    def on_style_selected(self, _list: Gtk.ListBox, row: Gtk.ListBoxRow | None) -> None:
        if self.syncing or row is None or row.style_name == self.data["style"]["name"]:
            return
        self.changed(("style", "name"), row.style_name)

    def reset_all(self) -> None:
        """Every tab back to the theme you started from; Custom keeps your changes."""
        self.data = settings.keep_per_user(self.base_settings(), self.data)
        self.status.set_text(_("Every tab reset to {theme}. Your latest changes are still in Custom.").format(theme=self.base))
        self.after_change()

    def reset_section(self, section: str) -> None:
        if section in ("share",):
            return
        self.data[section] = copy.deepcopy(self.base_settings()[section])
        self.status.set_text(_("{tab} reset to {theme}.").format(tab=dict(TABS)[section], theme=self.base))
        self.after_change()

    def on_save_theme(self, _button: Gtk.Button) -> None:
        dialog = Gtk.Dialog(title=_("Save Theme"), transient_for=self, modal=True)
        dialog.add_buttons(_("Cancel"), Gtk.ResponseType.CANCEL, _("Save"), Gtk.ResponseType.OK)
        dialog.set_default_response(Gtk.ResponseType.OK)
        area = dialog.get_content_area()
        area.set_spacing(8)
        area.set_border_width(12)
        area.add(Gtk.Label(label=_("Name your theme. It uses the style “{style}” and all your current "
                                   "settings.").format(style=self.data["style"]["name"]),
                           xalign=0, wrap=True, max_width_chars=50))
        # a name box with a dropdown of your themes (pick one to save over it),
        # filled in with the theme you started from: Save again keeps the name
        combo = Gtk.ComboBoxText.new_with_entry()
        for name, _f, builtin in themes.list_themes():
            if not builtin:
                combo.append_text(name)
        entry = combo.get_child()
        entry.set_activates_default(True)
        entry.set_max_length(themes.MAX_NAME)
        entry.set_placeholder_text(_("My theme"))
        start = self.base if self.data["theme"] == themes.CUSTOM else self.data["theme"]
        try:
            _f, builtin = themes.find(start)
        except themes.ThemeError:
            builtin = True
        suggested = start if not builtin else _("{theme} copy").format(theme=start)
        entry.set_text(suggested[:themes.MAX_NAME])
        area.add(combo)
        hint = Gtk.Label(label=_("Up to {count} characters. Built-in themes can't be replaced; your own "
                                 "can.").format(count=themes.MAX_NAME), xalign=0, wrap=True, max_width_chars=50)
        hint.get_style_context().add_class("dim-label")
        area.add(hint)
        dialog.show_all()
        entry.grab_focus()
        entry.select_region(0, -1)           # type to replace, or press Enter to keep the name
        while dialog.run() == Gtk.ResponseType.OK:
            name = entry.get_text().strip()
            try:
                themes.save(name, self.data)
            except themes.ThemeError as exc:
                if getattr(exc, "exists", False) and \
                        self._confirm(_("Replace your theme “{theme}”?").format(theme=name)):
                    themes.save(name, self.data, overwrite=True)
                else:
                    self.say(str(exc), "error")
                    continue
            self.base = name
            self.base_cache.pop(name, None)
            self.data["theme"] = name
            self.fill_theme_list()
            self.after_change()
            self.status.set_text(_("Saved the theme “{theme}”.").format(theme=name))
            break
        dialog.destroy()

    def _ask_name(self, title: str, text: str, name: str, check=themes.check_new_name,
                  button: str = "") -> str | None:
        """A small dialog with a name box (filled in and selected); None if cancelled.
        Problems with the name show in the dialog, which stays open."""
        dialog = Gtk.Dialog(title=title, transient_for=self, modal=True)
        dialog.add_buttons(_("Cancel"), Gtk.ResponseType.CANCEL, button or _("OK"), Gtk.ResponseType.OK)
        dialog.set_default_response(Gtk.ResponseType.OK)
        area = dialog.get_content_area()
        area.set_spacing(8)
        area.set_border_width(12)
        area.add(Gtk.Label(label=text, xalign=0, wrap=True, max_width_chars=50))
        entry = Gtk.Entry(activates_default=True, text=name, max_length=themes.MAX_NAME)
        area.add(entry)
        problem = Gtk.Label(xalign=0, wrap=True, max_width_chars=50)
        problem.get_style_context().add_class("dim-label")
        area.add(problem)
        dialog.show_all()
        entry.grab_focus()
        entry.select_region(0, -1)
        result = None
        while dialog.run() == Gtk.ResponseType.OK:
            try:
                result = check(entry.get_text())
                break
            except themes.ThemeError as exc:
                msg = str(exc)
                problem.set_text(msg[:1].upper() + msg[1:] + ".")     # keep the name's own capitals
        dialog.destroy()
        return result

    def on_duplicate_theme(self, _button: Gtk.Button) -> None:
        row = self.theme_list.get_selected_row()
        if not row or row.theme_name == themes.CUSTOM:
            return
        name = self._ask_name(_("Duplicate Theme"),
                              _("A copy of “{theme}”, as one of your themes:").format(theme=row.theme_name),
                              themes.copy_name(row.theme_name), button=_("Duplicate"))
        if name is None:
            return
        try:
            themes.duplicate(row.theme_name, name)
        except themes.ThemeError as exc:
            self.say(str(exc), "error")
            return
        self.fill_theme_list()
        self.status.set_text(_("Duplicated “{theme}” as “{copy}”.").format(theme=row.theme_name, copy=name))
        for r in self.theme_list.get_children():
            if r.theme_name == name:
                self.theme_list.select_row(r)      # switch to the copy, ready to edit

    def on_rename_theme(self, _button: Gtk.Button) -> None:
        row = self.theme_list.get_selected_row()
        if not row or row.builtin or row.theme_name == themes.CUSTOM:
            return
        old = row.theme_name
        name = self._ask_name(_("Rename Theme"), _("A new name for “{theme}”:").format(theme=old), old,
                              button=_("Rename"))
        if name is None or name == old:
            return
        try:
            themes.rename(old, name)
        except themes.ThemeError as exc:
            self.say(str(exc), "error")
            return
        if self.base == old:
            self.base = name
        self.base_cache.pop(old, None)
        if self.data["theme"] == old:
            self.data["theme"] = name
        if self.applied.get("theme") == old:
            self.applied["theme"] = name
        self.fill_theme_list()
        self.refresh_custom_subtitle()
        self.update_buttons()
        self.status.set_text(_("Renamed “{old}” to “{new}”.").format(old=old, new=name))

    def on_delete_theme(self, _button: Gtk.Button) -> None:
        row = self.theme_list.get_selected_row()
        if not row or row.builtin or row.theme_name == themes.CUSTOM:
            return
        if self._confirm(_("Delete your theme “{theme}”? Its style stays installed.").format(theme=row.theme_name)):
            themes.delete(row.theme_name)
            if self.data["theme"] == row.theme_name:
                self.data["theme"] = themes.CUSTOM
            self.fill_theme_list()
            self.sync_controls()
            self.update_buttons()

    def _confirm(self, question: str) -> bool:
        d = Gtk.MessageDialog(transient_for=self, modal=True, message_type=Gtk.MessageType.QUESTION,
                              buttons=Gtk.ButtonsType.OK_CANCEL, text=question)
        answer = d.run()
        d.destroy()
        return answer == Gtk.ResponseType.OK

    def on_export(self, _button: Gtk.Button) -> None:
        mine = _("My theme")
        name = self.data["theme"] if self.data["theme"] != themes.CUSTOM else mine
        chooser = Gtk.FileChooserNative(title=_("Export theme"), transient_for=self,
                                        action=Gtk.FileChooserAction.SAVE)
        chooser.set_current_name(f"{themes.slug(name)}{themes.EXTENSION}")
        chooser.set_do_overwrite_confirmation(True)
        if chooser.run() == Gtk.ResponseType.ACCEPT:
            dest = Path(chooser.get_filename())
            label = name if name != mine else dest.stem.replace("-", " ").title()
            try:
                out = themes.export(label, self.data, dest)
                self.status.set_text(_("Exported “{theme}” to {file}").format(theme=label, file=out))
            except (themes.ThemeError, styles.StyleError, OSError) as exc:
                self.say(_("Export failed: {problem}").format(problem=exc), "error")
        chooser.destroy()

    def on_import(self, _button: Gtk.Button) -> None:
        chooser = Gtk.FileChooserNative(title=_("Import theme"), transient_for=self,
                                        action=Gtk.FileChooserAction.OPEN)
        f = Gtk.FileFilter()
        f.set_name(_("Theme Roller themes"))
        f.add_pattern(f"*{themes.EXTENSION}")
        chooser.add_filter(f)
        if chooser.run() == Gtk.ResponseType.ACCEPT:
            try:
                name, notes = themes.import_file(Path(chooser.get_filename()))
                self.fill_theme_list()
                for r in self.theme_list.get_children():
                    if r.theme_name == name:
                        self.theme_list.select_row(r)       # loads it into the preview
                self.status.set_text(_("Imported “{theme}”.").format(theme=name) +
                                     ("\n" + "\n".join(notes) if notes else ""))
            except (themes.ThemeError, OSError, ValueError) as exc:
                self.say(_("Import failed: {problem}").format(problem=exc), "error")
        chooser.destroy()

    def on_apply(self, _button: Gtk.Button) -> None:
        self.apply_btn.set_sensitive(False)
        self.status.set_text(_("Applying… the desktop flickers once while it reloads."))
        data = copy.deepcopy(self.data)

        def work() -> None:
            try:
                style, _missing = self._style(data)
                # Apply means "use this theme": also switch to it if it isn't active yet
                # restarts Cinnamon by itself when window borders changed
                log = cli.apply_to_desktop(data, style, activate=True)
                GLib.idle_add(self.applied_ok, data, log)
            except Exception as exc:  # report anything to the user
                GLib.idle_add(self.applied_failed, _("Apply failed: {problem}").format(problem=exc))
        threading.Thread(target=work, daemon=True).start()

    def _come_back(self) -> None:
        """Back to the front after Apply or Revert: reloading the desktop (and a
        Cinnamon restart) can minimise this window or send it behind others.
        Twice: once the theme has reloaded, again after a restart settles."""
        def present() -> bool:
            self.deiconify()
            self.present()
            return False
        GLib.timeout_add(600, present)
        GLib.timeout_add(3000, present)

    def applied_ok(self, data: dict, log: list[str]) -> bool:
        self._come_back()
        self.applied = data
        note, apps = self._login_note(log)
        self.say(_("“{theme}” is on the desktop. Revert puts the previous theme back.")
                 .format(theme=_(data["theme"]) if data["theme"] == themes.CUSTOM else data["theme"])
                 + note, "attention" if note else "done")
        self.status.set_tooltip_text(apps)
        self.revert_btn.set_sensitive(True)
        self.revert_btn.show()
        self.update_buttons()
        notice = qt.pending_notice()     # once: our Qt colours took the place of a setup of yours
        if notice:
            qt.notice_shown()
            GLib.timeout_add(3200, self._qt_notice, notice)   # after the window comes back
        return False

    def _login_note(self, log: list[str]) -> tuple[str, str | None]:
        """On Wayland, the title bars Cinnamon draws (older apps, through
        Xwayland) wait for the next login: name the ones open now, if any (no
        note when there are none). Also the full list, for the tooltip."""
        if reload.LOGIN_NEEDED not in log:
            return "", None
        progs = reload.xwayland_apps()
        if progs is None:            # can't tell: the general note
            return " " + _("Some older apps' title bars change at your next login."), None
        if not progs:
            return "", None
        names = [_app_name(p) for p in progs]
        shown = ", ".join(names[:3]) + (f" +{len(names) - 3}" if len(names) > 3 else "")
        return (" " + _("These title bars change at your next login: {apps}").format(apps=shown),
                ", ".join(names))

    def _qt_notice(self, text: str) -> bool:
        d = Gtk.MessageDialog(transient_for=self, modal=True, message_type=Gtk.MessageType.INFO,
                              buttons=Gtk.ButtonsType.OK, text=_("Qt apps now match your theme"))
        d.format_secondary_text(text)
        d.run()
        d.destroy()
        return False

    def applied_failed(self, message: str) -> bool:
        self.say(message, "error")
        self.update_buttons()
        return False

    def on_revert(self, _button: Gtk.Button) -> None:
        self.revert_btn.set_sensitive(False)
        self.status.set_text(_("Reverting… the desktop flickers once while it reloads."))

        def work() -> None:
            try:
                restored, log = cli.revert_desktop()
                GLib.idle_add(self.reverted, restored, log)
            except Exception as exc:
                GLib.idle_add(self.applied_failed, _("Revert failed: {problem}").format(problem=exc))
        threading.Thread(target=work, daemon=True).start()

    def reverted(self, restored: dict | None, log: list[str]) -> bool:
        self._come_back()
        if restored:
            self.applied = restored
        self.revert_btn.hide()
        note, apps = self._login_note(log)
        self.say(_("The previous theme is back on the desktop. Your settings here are unchanged.")
                 + note, "attention" if note else "done")
        self.status.set_tooltip_text(apps)
        self.update_buttons()
        return False


class SettingsApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="io.github.xlcheese.ThemeRoller")

    def do_activate(self) -> None:
        win = self.props.active_window or SettingsWindow(self)
        win.present()


def main() -> int:
    return SettingsApp().run([])
