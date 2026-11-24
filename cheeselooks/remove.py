"""Take Theme Roller off your desktop, before uninstalling it (or to start over).

    theme-roller remove        (the app: About → Remove from my desktop…)

A package can't tidy what Theme Roller put in your home folder, so this does,
for you:

- the desktop: any of Cinnamon's theme settings still on xl-Cheeselooks go
  back to Mint's default (gsettings reset), and a folder icon theme of ours
  back to your previous icons;
- your apps: our colors out of GNOME-style (GTK 4), Qt and text editor apps,
  your own Qt setup and editor schemes put back, Flatpak's access to the
  theme taken away again;
- the theme watcher: no longer started at login, and stopped now;
- the files it made: ~/.themes/xl-Cheeselooks, ~/.icons/xl-Cheeselooks, the
  copy of the previous theme Revert keeps, and its cache.

Your settings and your own themes and styles stay (~/.config/theme-roller,
~/.local/share/theme-roller), so installing it again picks up where you left
off. Delete those two folders too to remove every trace.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from . import editor, flatpak, gtk4, icons, paths, qt, reload, watch


def _ours(value: str | None) -> bool:
    return watch.is_ours(value)


def remove() -> list[str]:
    log: list[str] = []
    # 1. the watcher first, so it doesn't react to the theme changing below
    log += watch.disable()
    # 2. Cinnamon's theme settings that are ours: back to Mint's defaults
    if reload.available():
        for schema, key, _fallback, _part in reload.THEME_KEYS:
            current = reload.get(schema, key)
            if _ours(current):
                reload._run("reset", schema, key)
                log.append(f"{schema} {key}: back to {reload.get(schema, key) or 'the default'}")
    # 3. our colors and files out of apps (and yours back)
    line = gtk4.write(paths.gtk4_css(), None)
    if line:
        log.append(line)
    gtk4.remove_assets(paths.gtk4_css())
    if qt.active():
        log += qt.disable()
    if editor.active():
        log += editor.disable()
    if flatpak.disable():
        log.append("Flatpak apps no longer read the theme")
    if icons.active() or icons.theme_dir().exists():
        log += icons.disable()
    # 4. the files Theme Roller made (not your settings or your own themes)
    for d in [paths.theme_dir(), paths.last_good_dir(), paths.cache_dir()] + paths.old_theme_dirs():
        if d.exists():
            shutil.rmtree(d, ignore_errors=True)
            log.append(f"removed {d}")
    saved = [d.parent / f".{d.name}.settings.json"               # beside the theme
             for d in [paths.theme_dir()] + paths.old_theme_dirs()]
    for f in [watch.set_aside_file()] + saved:
        if f.exists():
            f.unlink()
    # files Theme Roller created and has now emptied (a real ~/.profile has more in it)
    for f in (paths.gtk4_css(), paths.HOME / ".profile"):
        if f.exists() and f.stat().st_size == 0:
            f.unlink()
    for f in editor.scheme_files():          # the editors' style folders it made, if empty
        for d in (f.parent, f.parent.parent):
            try:
                d.rmdir()
            except OSError:
                pass
    return log


def leftovers() -> list[Path]:
    """What remove() keeps: your settings, themes and styles."""
    data = paths._xdg("XDG_DATA_HOME", paths.HOME / ".local" / "share") / paths.APP_DIR
    return [p for p in (paths.config_dir(), data) if p.exists()]

