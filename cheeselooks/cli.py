"""The `cheeselooks` command."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

from . import __version__, editor, velocitty, palette, flatpak, gtk4, icons, install, paths, qt, reload, watch, settings, styles, themes, tokens
from .shape import DEFAULT_PANEL_HEIGHT


def _err(msg: str) -> None:
    print(f"cheeselooks: {msg}", file=sys.stderr)


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


# --------------------------------------------------------------------------
# Presets
# --------------------------------------------------------------------------

def preset_files() -> list[Path]:
    files: list[Path] = []
    for base in (paths.user_presets_dir(), paths.builtin_presets_dir()):
        if base.is_dir():
            files.extend(sorted(base.rglob("*.json")))
    return files


def find_preset(name: str) -> dict:
    p = Path(name)
    if p.suffix == ".json" and p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    for f in preset_files():
        data = json.loads(f.read_text(encoding="utf-8"))
        if name in (data.get("name"), f.stem) or _slug(name) == f.stem:
            return data
    raise KeyError(name)


# --------------------------------------------------------------------------
# Commands
# --------------------------------------------------------------------------

def _load_settings(args: argparse.Namespace) -> dict:
    path = Path(args.settings) if args.settings else paths.settings_file()
    fresh = not path.exists()
    data = settings.load(path)
    if getattr(args, "theme", None):
        try:
            # the whole theme: every tab, but your Integration switches stay
            data = settings.keep_per_user(themes.load(args.theme), data)
        except themes.ThemeError as exc:
            raise settings.SettingsError([str(exc)])
        fresh = False
    new_style = getattr(args, "style", None)
    if new_style:
        data["style"]["name"] = new_style
    if fresh or new_style or getattr(args, "style_defaults", False):
        # fresh install, a newly picked style, or "reset to style defaults":
        # start from the style's suggested [defaults]
        style = _load_style(data["style"]["name"], getattr(args, "style_dir", None))
        data = settings.apply_style_defaults(data, style.defaults)
    for name in args.preset or []:
        try:
            data = settings.apply_preset(data, find_preset(name))
        except KeyError:
            raise settings.SettingsError([f"no preset called '{name}' (see: cheeselooks presets)"])
    return data


def _load_style(name: str, extra_dir: str | None) -> styles.Style:
    dirs = ([Path(extra_dir)] if extra_dir else []) + paths.style_dirs()
    return styles.find(name, dirs)


def style_or_stand_in(data: dict) -> tuple[styles.Style, str]:
    """The theme's style, or, if it's gone (renamed or removed), the default
    style for light or dark colors, with a note saying so. Without this a
    theme whose style was renamed couldn't preview or Apply, and the app's
    window opened squashed."""
    name = data["style"]["name"]
    try:
        return _load_style(name, None), ""
    except styles.StyleError:
        g = data["global"]
        dark = palette.luminance(g["bg"]) < palette.luminance(g["text"])
        stand_in = _load_style("xl-Cheeselooks-Dark" if dark else "xl-Cheeselooks", None)
        return stand_in, (f"Style “{name}” wasn't found (renamed or removed?), so {stand_in.name} "
                          "stands in. Pick a style on the Style tab.")


def _where(style: styles.Style) -> str:
    """The style's file, and whether it replaces a built-in style of the same name."""
    if style.path is None:
        return "(built in)"
    folder = style.path.parent
    builtin = paths.data_dir() / "styles"
    try:
        folder.relative_to(builtin)
        return str(style.path)
    except ValueError:
        pass
    try:
        styles.find(style.name, [builtin])
    except styles.StyleError:
        return str(style.path)
    return f"{style.path} (your copy, used instead of the built-in {style.name})"


def _libadwaita(data: dict, table: dict) -> list[str]:
    """GTK 4 / libadwaita: the colour block in ~/.config/gtk-4.0/gtk.css and
    GNOME's accent key, each only if switched on in Integration."""
    log = []
    integ = data["integration"]
    # CSS variables for libadwaita 1.6+ always: Flatpak apps bring their own,
    # newer libadwaita, and GTK 4.14 accepts the variables without warnings
    colors = integ.get("libadwaita", "colors") != "off"
    full = integ.get("libadwaita") == "full"
    new = (gtk4.block(paths.templates_dir(), table, css_variables=True, full=full)
           if colors else None)
    log.append(gtk4.write(paths.gtk4_css(), new))
    if full:
        gtk4.copy_assets(new, paths.theme_dir(), paths.gtk4_css())
        log.append("libadwaita apps: full styling (buttons, title buttons, tabs) in "
                   f"{paths.gtk4_css()}; reopen open ones")
    else:
        gtk4.remove_assets(paths.gtk4_css())
    if colors:                     # GNOME's own accent setting, to match (part of colors)
        log.append(reload.set_adw_accent(table["adw.accent_name"]) or "")
    log += _flatpak_access(integ.get("flatpak_access", False))
    # Qt apps: rewritten at each Apply while on; switched off, removed once
    if integ.get("qt_colors"):
        log += qt.enable(table)
    elif qt.active():
        log += qt.disable()
    # text editors (Xed, gedit, Meld): likewise
    if integ.get("editor_colors"):
        log += editor.enable(table)
    elif editor.active():
        log += editor.disable()
    # Velocitty (Mint 23's terminal): a palette from the theme, while it's installed
    log += velocitty.enable(table)
    return [line for line in log if line]


def _icons(data: dict, table: dict) -> list[str]:
    """Icons tab: folders in your colors when on; switched off, your icon theme back."""
    if data["icons"].get("enabled"):
        return icons.enable(table, data["icons"])
    if icons.active():
        return icons.disable()
    return []


def _flatpak_access(on: bool) -> list[str]:
    """Flatpak apps: read-only access to the theme (a user-wide override),
    granted while the switch is on; switched off, just our entries removed."""
    if not flatpak.available():
        return []
    if on:
        if len(flatpak.granted()) == len(flatpak.FILESYSTEMS):
            return []
        try:
            flatpak.enable()
            return ["Flatpak apps can see the theme (reopen any open ones)"]
        except RuntimeError as exc:
            return [f"Flatpak: {exc}"]
    if flatpak.added_file().exists() and flatpak.disable():
        return ["Flatpak apps: xl-Cheeselooks' access removed"]
    return []


PANEL_HEIGHT_FILE = "panels-height"   # in the last-good folder: Cinnamon's height before Apply


def _panel_height(data: dict, live: bool = True) -> int:
    """The height to build for: yours, else Cinnamon's current one."""
    chosen = data["panel"]["panel_height"]
    if chosen is not None:
        return chosen
    return reload.panel_height(DEFAULT_PANEL_HEIGHT) if live else DEFAULT_PANEL_HEIGHT


def _apply_panel_height(data: dict, last_good: Path) -> list[str]:
    """Set Cinnamon's panel height when you chose one, keeping the old value
    in the last-good folder for Revert."""
    chosen = data["panel"]["panel_height"]
    raw = reload.panel_heights_raw()
    if chosen is None or raw is None or reload.panel_height(DEFAULT_PANEL_HEIGHT) == chosen \
            and "," not in raw:
        return []
    last_good.mkdir(parents=True, exist_ok=True)     # the first Apply: nothing saved there yet
    (last_good / PANEL_HEIGHT_FILE).write_text(raw + "\n", encoding="utf-8")
    line = reload.set_panel_height(chosen, raw)
    return [line] if line else []


def _restore_panel_height(last_good: Path) -> list[str]:
    f = last_good / PANEL_HEIGHT_FILE
    if not f.exists():
        return []
    line = reload.restore_panel_heights(f.read_text(encoding="utf-8").strip())
    f.unlink()
    return [line] if line else []


def apply_to_desktop(data: dict, style: styles.Style, activate: bool = False,
                     save: bool = True, restart: bool = False) -> list[str]:
    """Write the theme to ~/.themes, save the settings, update the libadwaita
    colours and reload the desktop: everything `cheeselooks apply` does.
    Returns the log lines. Used by the settings app's Apply button."""
    with watch.applying():
        log = _apply_to_desktop(data, style, activate, save, restart)
    log += _watcher(data)
    return log


def _watcher(data: dict) -> list[str]:
    """The theme watcher, at login (and now): always on since 22 Nov (xl_cheese:
    nobody wants Theme Roller's colors stuck on another theme)."""
    return watch.enable()


def _apply_to_desktop(data: dict, style: styles.Style, activate: bool,
                      save: bool, restart: bool) -> list[str]:
    log = []
    height = _panel_height(data)
    table = tokens.build(data, style, panel_height=height,
                         overlay_scrollbars=reload.overlay_scrollbars())
    theme_dir = paths.theme_dir()
    _adopt_old_theme(theme_dir)            # 0.9.0's xl-Cheeselooks: Revert's previous theme
    written = install.install(paths.templates_dir(), table, theme_dir, paths.last_good_dir(), data)
    log += _apply_panel_height(data, paths.last_good_dir())
    if save:
        settings.save(data, paths.settings_file())
    log.append(f"Wrote {len(written)} files to {theme_dir}")
    log.append(f"style: {style.name} from {_where(style)}")
    log += [f"note: {n}" for n in tokens.warnings(data)]
    log += _libadwaita(data, table)
    log += _icons(data, table)
    layout = table["wb.button_layout"] if (theme_dir / "metacity-1").is_dir() else None
    sb = data["details"]["scrollbars"]
    if sb["custom"]:
        line = reload.set_overlay_scrollbars(sb["mode"] == "overlay")
        if line:
            log.append(line)
    was_ours = reload.available() and watch.is_ours(reload.get(*THEME_KEY))
    if activate and reload.available() and not was_ours:
        _remember_desktop(paths.last_good_dir())    # Revert goes back to it (Mint-Y, say)
    log += _to_new_name()
    log += reload.apply(tokens.THEME_NAME, layout, activate=activate, theme_dir=theme_dir)
    log += _remove_old_theme()
    log += _window_borders(table, was_ours, force=restart)
    return log


# ------------------------------------------------------------------ window borders
# Cinnamon's window manager (Muffin) draws window borders from the GTK theme's
# stylesheet, but keeps the copy it loaded by name: Apply's reload refreshes
# apps, not the borders (xl_cheese tested: only a Cinnamon restart did). So
# Apply restarts Cinnamon itself, only when something Muffin draws changed:
# a fingerprint of the title bar, border and title button values, remembered.
THEME_KEY = ("org.cinnamon.desktop.interface", "gtk-theme")
WINDOW_BORDER_KEYS = ("wb.", "tbtn.", "titlebuttons.", "file:gtk-3")


def window_border_fingerprint(table: dict[str, str]) -> str:
    h = hashlib.sha256()
    for key in sorted(table):
        if key.startswith(WINDOW_BORDER_KEYS) or key == "titlebuttons":
            h.update(f"{key}={table[key]}\n".encode())
    return h.hexdigest()


def _window_borders(table: dict[str, str], was_ours: bool, force: bool = False) -> list[str]:
    """Restart Cinnamon if its window borders need it: what they draw changed
    since the last Apply (or, the first time, our theme was already in use, so
    an old copy may be loaded). Switching to the theme from another needs no
    restart: Muffin loads it fresh."""
    if not reload.available():
        return []
    f = paths.config_dir() / "window-borders"
    try:
        old = f.read_text(encoding="utf-8").strip()
    except OSError:
        old = None
    new = window_border_fingerprint(table)
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(new + "\n", encoding="utf-8")
    if force or (old is not None and old != new) or (old is None and was_ours):
        return [reload.restart_cinnamon()]
    return []


def cmd_apply(args: argparse.Namespace) -> int:
    if args.theme_dir:
        return _cmd_apply(args)
    with watch.applying():
        code = _cmd_apply(args)
    if not args.no_reload:
        data = settings.load(paths.settings_file())
        for line in _watcher(data):
            print(f"  {line}")
    return code


def cmd_scan(args: argparse.Namespace) -> int:
    """Scan my apps, on the command line; --why shows what the scan saw for
    apps it couldn't tell (to improve it)."""
    from . import appscan
    entries = appscan.menu_apps()
    apps = [(appscan.classify(i, e), i, e) for i, e in entries]
    for kind in (appscan.GTK3, appscan.GNOME, appscan.FLATPAK, appscan.QT, appscan.EDITOR,
                 appscan.TERMINAL, appscan.WEB, appscan.UNKNOWN):
        group = sorted((a for a in apps if a[0].kind == kind), key=lambda a: a[0].name.lower())
        if group:
            print(f"{kind} ({len(group)}): " + ", ".join(a[0].name for a in group))
    if args.why:
        print()
        for app, app_id, e in sorted(apps, key=lambda a: a[0].name.lower()):
            if app.kind == appscan.UNKNOWN:
                print(f"{app.name}  [{app_id}]")
                for line in appscan.why(app_id, e):
                    print(line)
    return 0


def cmd_watch(_args: argparse.Namespace) -> int:
    return watch.run()


def cmd_set_aside(_args: argparse.Namespace) -> int:
    for line in watch.set_aside():
        print(line)
    print("Done. Reopen open apps. The next Apply puts xl-Cheeselooks' colors back.")
    return 0


def _cmd_apply(args: argparse.Namespace) -> int:
    data = _load_settings(args)
    style = _load_style(data["style"]["name"], args.style_dir)
    for w in style.warnings:
        _err(f"style warning: {w}")
    live = not args.no_reload
    height = _panel_height(data, live)
    table = tokens.build(data, style, panel_height=height,
                         overlay_scrollbars=reload.overlay_scrollbars() if live else None)
    if args.theme_dir:
        theme_dir = Path(args.theme_dir)
        last_good = theme_dir.with_name(f".{theme_dir.name}.last-good")
    else:
        theme_dir, last_good = paths.theme_dir(), paths.last_good_dir()
    written = install.install(paths.templates_dir(), table, theme_dir, last_good, data)
    if not args.no_save and not args.settings:
        settings.save(data, paths.settings_file())
    print(f"Wrote {len(written)} files to {theme_dir}")
    print(f"  style: {style.name} from {_where(style)}")
    for note in tokens.warnings(data):
        print(f"  note: {note}")
    if not args.theme_dir:
        for line in _libadwaita(data, table):
            print(f"  {line}")
        for line in _icons(data, table):
            print(f"  {line}")
        qt.notice_shown()          # its "previous Qt setup is saved" line was just printed
    if not args.no_reload and not args.theme_dir:
        for line in _apply_panel_height(data, last_good):
            print(f"  {line}")
        layout = table["wb.button_layout"] if (theme_dir / "metacity-1").is_dir() else None
        sb = data["details"]["scrollbars"]
        if sb["custom"]:
            line = reload.set_overlay_scrollbars(sb["mode"] == "overlay")
            if line:
                print(f"  {line}")
        was_ours = reload.available() and reload.get(*THEME_KEY) == tokens.THEME_NAME
        for line in reload.apply(tokens.THEME_NAME, layout, activate=args.activate, theme_dir=theme_dir):
            print(f"  {line}")
        for line in _window_borders(table, was_ours, force=getattr(args, "restart", False)):
            print(f"  {line}")
    return 0


def _adopt_old_theme(theme_dir: Path) -> None:
    """The theme under its 0.9.0 name (xl-Cheeselooks) and none under the new
    one yet: copied across first, so this Apply keeps it as the theme Revert
    goes back to, as it would have under one name."""
    if theme_dir.exists():
        return
    for old in paths.old_theme_dirs():
        if old.is_dir():
            shutil.copytree(old, theme_dir, symlinks=True)
            saved = old.parent / f".{old.name}.settings.json"
            if saved.exists():
                shutil.copy2(saved, theme_dir.parent / f".{theme_dir.name}.settings.json")
            return


def _to_new_name() -> list[str]:
    """Cinnamon's theme settings still on an earlier name of ours: to the new one
    (Mint's Themes settings then lists it as Theme Roller)."""
    if not reload.available():
        return []
    log = []
    for schema, key, _f, _p in reload.THEME_KEYS:
        if reload.get(schema, key) in tokens.OLD_THEME_NAMES:
            reload.set_value(schema, key, tokens.THEME_NAME)
            log.append(f"{schema} {key}: now {tokens.THEME_NAME} (was {', '.join(tokens.OLD_THEME_NAMES)})")
    return log


def _remove_old_theme() -> list[str]:
    """The theme's folders under earlier names, once nothing uses them."""
    if reload.available() and any(reload.get(s, k) in tokens.OLD_THEME_NAMES
                                  for s, k, _f, _p in reload.THEME_KEYS):
        return []
    log = []
    for old in paths.old_theme_dirs():
        saved = old.parent / f".{old.name}.settings.json"
        if old.exists():
            shutil.rmtree(old, ignore_errors=True)
            log.append(f"removed {old} (now {paths.theme_dir()})")
        if saved.exists():
            saved.unlink()
    return log


DESKTOP_FILE = "desktop.json"      # in the last-good folder: the theme the desktop had before ours


def _desktop_keys() -> list[tuple[str, str]]:
    return [(schema, key) for schema, key, _f, _p in reload.THEME_KEYS] + [icons.KEY]


def _remember_desktop(last_good: Path) -> None:
    """The desktop's theme settings just before an Apply switches them to ours
    (xl_cheese, 23 Nov: Revert after the first Apply should bring Mint-Y back,
    not an earlier Theme Roller theme)."""
    before = {f"{schema} {key}": reload.get(schema, key) for schema, key in _desktop_keys()}
    before = {k: v for k, v in before.items() if v and not watch.is_ours(v)}
    if before:
        last_good.mkdir(parents=True, exist_ok=True)
        (last_good / DESKTOP_FILE).write_text(json.dumps(before, indent=2) + "\n", encoding="utf-8")


def _back_to_desktop(last_good: Path) -> list[str] | None:
    """Revert after an Apply that switched to our theme: the desktop's own theme
    back, our colors out of apps (as picking it in Mint's settings does). None
    if the theme before was ours (then the files are restored instead)."""
    f = last_good / DESKTOP_FILE
    if not f.exists():
        return None
    before = json.loads(f.read_text(encoding="utf-8"))
    log = _restore_panel_height(last_good)
    if reload.available():
        with watch.applying():
            for name, value in before.items():
                schema, key = name.split(" ", 1)
                if watch.is_ours(reload.get(schema, key)) and reload.set_value(schema, key, value):
                    log.append(f"{schema} {key}: back to {value}")
    log += watch.set_aside()
    f.unlink()
    return log


def revert_desktop() -> tuple[dict | None, list[str]]:
    """Put the previous theme back on the desktop (the one before the last
    Apply): the desktop's own (Mint-Y...) if that Apply switched to ours, else
    the previous Theme Roller theme. Returns the restored settings (None for
    the desktop's own) and the log lines; the settings app keeps its own
    settings as they are."""
    back = _back_to_desktop(paths.last_good_dir())
    if back is not None:
        return None, back
    log = _restore_panel_height(paths.last_good_dir())
    data = install.revert(paths.theme_dir(), paths.last_good_dir())
    table = None
    if data:
        data = settings.from_dict(data)
        settings.save(data, paths.settings_file())
        try:
            style = _load_style(data["style"]["name"], None)
            table = tokens.build(data, style, panel_height=_panel_height(data))
            log += _libadwaita(data, table)
        except styles.StyleError as exc:
            log.append(f"libadwaita colors left as they were: {exc}")
    with watch.applying():
        log += reload.apply(tokens.THEME_NAME, theme_dir=paths.theme_dir())
    # window borders: Muffin keeps the copy it loaded, so a restart when they differ
    # (xl_cheese: Dark back to light kept dark title bars, and glyphs went missing);
    # without the restored settings to compare, restart to be sure
    if table is not None:
        log += _window_borders(table, True)
    elif reload.available():
        log.append(reload.restart_cinnamon())
    return data, log


def cmd_revert(args: argparse.Namespace) -> int:
    if args.no_reload:            # the files only (scripts, tests)
        data = install.revert(paths.theme_dir(), paths.last_good_dir())
        if data:
            settings.save(settings.from_dict(data), paths.settings_file())
        print("Restored the previous theme's files.")
        return 0
    try:
        data, log = revert_desktop()       # as the app's Revert: the desktop's own theme, or ours
    except install.InstallError as exc:
        _err(str(exc))
        return 1
    print("Restored the previous theme." if data is not None else "Back to the desktop's previous theme.")
    for line in log:
        print(f"  {line}")
    return 0


def cmd_remove(args: argparse.Namespace) -> int:
    """Theme Roller off your desktop, before uninstalling it (see remove.py)."""
    from . import remove
    if not args.yes:
        print("This takes Theme Roller off your desktop: Mint's default theme comes back, its colors\n"
              "leave your apps, and the theme watcher stops starting at login. Your settings and\n"
              "your own themes stay. Run it before uninstalling Theme Roller.")
        try:
            if input("Go ahead? [y/N] ").strip().lower() not in ("y", "yes"):
                print("Nothing changed.")
                return 1
        except EOFError:
            return 1
    for line in remove.remove():
        print(line)
    kept = remove.leftovers()
    print("Done. Theme Roller is off your desktop; you can uninstall it now.")
    if kept:
        print("Kept (delete them too to remove every trace): " + ", ".join(str(p) for p in kept))
    return 0


def cmd_tokens(args: argparse.Namespace) -> int:
    data = _load_settings(args)
    style = _load_style(data["style"]["name"], args.style_dir)
    table = tokens.build(data, style)
    for key in sorted(table):
        if args.filter and args.filter not in key:
            continue
        value = table[key].replace("\n", "\\n")
        print(f"{key:40} {value[:120]}")
    return 0


def cmd_check_style(args: argparse.Namespace) -> int:
    try:
        style = styles.load(Path(args.path))
    except styles.StyleError as exc:
        print(f"{args.path}: {len(exc.problems)} problem(s)")
        for p in exc.problems:
            print(f"  error: {p}")
        return 1
    print(f"{style.name}: OK")
    for w in style.warnings:
        print(f"  warning: {w}")
    return 0


def cmd_flatpak(args: argparse.Namespace) -> int:
    if not flatpak.available():
        print("Flatpak isn't installed: nothing to do.")
        return 0
    command = " ".join(flatpak.COMMAND)
    have = flatpak.granted()
    if args.enable:
        if len(have) == len(flatpak.FILESYSTEMS):
            print("Flatpak apps can already see the theme.")
            return 0
        print("This gives every Flatpak app read-only access to your themes folder and")
        print("your GTK 4 colors, so they can use xl-Cheeselooks. It runs:\n")
        print(f"  {command}\n")
        if not args.yes and input("Go ahead? [y/N] ").strip().lower() not in ("y", "yes"):
            print("Nothing changed.")
            return 0
        flatpak.enable()
        _set_flatpak_setting(True)
        print("Done. Restart any open Flatpak apps. Undo with: cheeselooks flatpak --disable")
        return 0
    if args.disable:
        if flatpak.disable():
            print(f"Removed xl-Cheeselooks' access from {flatpak.overrides_file()} "
                  "(your other Flatpak overrides are kept).")
        else:
            print("Flatpak apps had no access from xl-Cheeselooks: nothing to remove.")
        _set_flatpak_setting(False)
        return 0
    if len(have) == len(flatpak.FILESYSTEMS):
        print("Flatpak apps can see the theme. Undo with: cheeselooks flatpak --disable")
    else:
        print("Flatpak apps can't see the theme yet. To allow it (read-only, undoable):")
        print("  cheeselooks flatpak --enable")
        print(f"which runs: {command}")
    return 0


def _set_flatpak_setting(on: bool) -> None:
    path = paths.settings_file()
    if path.exists():
        data = settings.load(path)
        data["integration"]["flatpak_access"] = on
        settings.save(data, path)


def cmd_themes(args: argparse.Namespace) -> int:
    for name, f, builtin in themes.list_themes():
        print(f"{name:28} {'built-in' if builtin else 'yours':9} {f}")
    if themes.custom_file().exists():
        print(f"{themes.CUSTOM:28} {'yours':9} {themes.custom_file()}")
    return 0


def cmd_export_theme(args: argparse.Namespace) -> int:
    if args.name == themes.CUSTOM or not args.name:
        data, name = settings.load(paths.settings_file()), args.save_as or "My theme"
    else:
        data, name = themes.load(args.name), args.save_as or args.name
    dest = Path(args.file) if args.file else Path.cwd() / themes.slug(name)
    try:
        out = themes.export(name, data, dest)
    except (themes.ThemeError, styles.StyleError) as exc:
        _err(str(exc))
        return 1
    print(f"Exported '{name}' to {out}")
    return 0


def cmd_import_theme(args: argparse.Namespace) -> int:
    try:
        name, notes = themes.import_file(Path(args.file))
    except (themes.ThemeError, OSError, ValueError) as exc:
        _err(str(exc))
        return 1
    print(f"Imported theme '{name}'. Use it with: cheeselooks apply --theme \"{name}\"")
    for n in notes:
        print(f"  note: {n}")
    return 0


def cmd_presets(args: argparse.Namespace) -> int:
    for f in preset_files():
        data = json.loads(f.read_text(encoding="utf-8"))
        sections = [k for k in data if k not in ("name", "version")]
        print(f"{data.get('name', f.stem):28} {'/'.join(sections):10} {f}")
    return 0


def cmd_export_preset(args: argparse.Namespace) -> int:
    data = settings.load(paths.settings_file())
    section = args.section
    preset = {"name": args.name, section: data[section]}
    out = paths.user_presets_dir() / section / f"{_slug(args.name)}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(preset, indent=2) + "\n", encoding="utf-8")
    print(f"Saved {out}")
    return 0


def main(argv: list[str] | None = None) -> int:
    from . import i18n
    i18n.use_english()          # the command line stays English (its messages are shared with the app)
    parser = argparse.ArgumentParser(prog="theme-roller",
                                     description="Generate and apply the xl-Cheeselooks theme.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    def common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--settings", help="use this settings file instead of your saved settings")
        p.add_argument("--preset", action="append",
                       help="apply a preset on top (name or .json file; can repeat)")
        p.add_argument("--style-dir", help="extra folder to look for styles in")
        p.add_argument("--theme", help="use this theme (every setting; see: cheeselooks themes)")

    p = sub.add_parser("apply", help="generate the theme and reload the desktop")
    common(p)
    p.add_argument("--theme-dir", help="write the theme here instead of ~/.themes (no reload)")
    p.add_argument("--style", help="switch to this style and start from its suggested defaults")
    p.add_argument("--style-defaults", action="store_true",
                   help="reset roundness, gradient, depth and panel/menu shape to the style's defaults")
    p.add_argument("--activate", action="store_true", help="also switch Cinnamon to this theme")
    p.add_argument("--restart", action="store_true",
                   help="restart Cinnamon afterwards even if window borders didn't change "
                        "(Apply restarts it by itself when they did)")
    p.add_argument("--no-reload", action="store_true", help="write files only")
    p.add_argument("--no-save", action="store_true", help="don't save the settings used")
    p.set_defaults(func=cmd_apply)

    p = sub.add_parser("revert", help="go back to the previously applied theme")
    p.add_argument("--no-reload", action="store_true")
    p.set_defaults(func=cmd_revert)

    p = sub.add_parser("remove", help="take Theme Roller off your desktop (run before uninstalling)")
    p.add_argument("--yes", action="store_true", help="don't ask first")
    p.set_defaults(func=cmd_remove)

    p = sub.add_parser("tokens", help="list every computed value (for template and style authors)")
    common(p)
    p.add_argument("filter", nargs="?", help="only show tokens containing this text")
    p.set_defaults(func=cmd_tokens)

    p = sub.add_parser("check-style", help="check a style file for problems")
    p.add_argument("path")
    p.set_defaults(func=cmd_check_style)

    p = sub.add_parser("scan", help="list your apps by kind (Integration: Scan my apps)")
    p.add_argument("--why", action="store_true", help="show what the scan saw for apps it couldn't tell")
    p.set_defaults(func=cmd_scan)
    p = sub.add_parser("watch", help="run the theme watcher (started at login; see Integration)")
    p.set_defaults(func=cmd_watch)
    p = sub.add_parser("set-aside", help="take xl-Cheeselooks' colors out of GTK 4, Qt and editor apps")
    p.set_defaults(func=cmd_set_aside)
    p = sub.add_parser("flatpak", help="let Flatpak apps see the theme (or undo it)")
    group = p.add_mutually_exclusive_group()
    group.add_argument("--enable", action="store_true", help="grant read-only access (asks first)")
    group.add_argument("--disable", action="store_true", help="remove that access again")
    p.add_argument("--yes", action="store_true", help="don't ask before enabling")
    p.set_defaults(func=cmd_flatpak)

    p = sub.add_parser("themes", help="list the themes (built-in and yours)")
    p.set_defaults(func=cmd_themes)

    p = sub.add_parser("export-theme", help="pack a theme into one file to share (.xltheme)")
    p.add_argument("name", help="theme name, or Custom for your current settings")
    p.add_argument("file", nargs="?", help="where to write it (default: <name>.xltheme here)")
    p.add_argument("--save-as", help="the name the theme gets in the file")
    p.set_defaults(func=cmd_export_theme)

    p = sub.add_parser("import-theme", help="install a theme from a .xltheme file")
    p.add_argument("file")
    p.set_defaults(func=cmd_import_theme)

    p = sub.add_parser("presets", help="list available presets")
    p.set_defaults(func=cmd_presets)

    p = sub.add_parser("export-preset", help="save part of your current settings as a preset")
    p.add_argument("name")
    p.add_argument("--section", choices=("global", "panel", "terminal"), default="global")
    p.set_defaults(func=cmd_export_preset)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except BrokenPipeError:  # output piped into e.g. `head`
        sys.stderr.close()
        return 0
    except (settings.SettingsError, styles.StyleError) as exc:
        for problem in exc.problems:
            _err(problem)
        return 2
    except (install.InstallError, OSError) as exc:
        _err(str(exc))
        return 1
    except Exception as exc:  # template problems and anything unexpected
        problems = getattr(exc, "problems", None)
        for problem in problems or [str(exc)]:
            _err(problem)
        return 1
