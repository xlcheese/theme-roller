#!/usr/bin/env python3
"""Build the Theme Roller .deb package.

    tools/build-deb.py                 writes dist/theme-roller_<version>_all.deb

The version comes from cheeselooks/__init__.py. The maintainer is your git
name and email (git config user.name / user.email), or MAINTAINER="Name
<email>" in the environment. Needs dpkg-deb (Mint has it).

What goes where:

  /usr/bin/theme-roller                         the command (opens the app)
  /usr/share/theme-roller/                      the program and everything it reads:
      cheeselooks/ templates/ styles/ presets/ po/ data/
  /usr/share/applications/io.github.xlcheese.ThemeRoller.desktop     the menu entry
  /usr/share/icons/hicolor/*/apps/io.github.xlcheese.ThemeRoller.*   its icon
  /usr/share/metainfo/io.github.xlcheese.ThemeRoller.metainfo.xml    for Software Manager
  /etc/xdg/autostart/theme-roller-watch.desktop the theme watcher, at login (it does
                                                nothing for people who never applied; not a
                                                conffile, so uninstalling removes it, not only purging)
  /usr/share/doc/theme-roller/                  copyright, README

Uninstalling removes all of these. What Theme Roller wrote in a home folder
(the theme, colors in apps) is taken off with "theme-roller remove", or
About → Remove from my desktop…, before uninstalling.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP_ID = "io.github.xlcheese.ThemeRoller"
PACKAGE = "theme-roller"
SHARE = Path("usr/share") / PACKAGE
DEPENDS = "python3 (>= 3.11), python3-gi, gir1.2-gtk-3.0, gir1.2-pango-1.0, libglib2.0-bin, procps"
RECOMMENDS = "qt5ct"
SUGGESTS = "flatpak"

DESCRIPTION = """\
Style your Linux Mint Cinnamon desktop
 Theme Roller makes a complete theme for Linux Mint's Cinnamon desktop from
 your own colors and a few sliders: GTK 3 and GTK 4 apps, libadwaita apps, the
 Cinnamon panel and menus, and the window borders. Pick a style for how
 things are drawn (edges, shadows, tabs, window buttons), see it in a live
 preview, and click Apply.
 .
 It also brings your colors to apps that don't read the theme on their own
 (GNOME-style apps, Flatpak apps, Qt apps like VLC, text editors), recolors
 your folder icons in one of six styles, and shares themes as a single file.
"""

DESKTOP = f"""\
[Desktop Entry]
Type=Application
Name=Theme Roller
GenericName=Theme Maker
GenericName[de]=Themen-Ersteller
GenericName[es]=Creador de temas
GenericName[fr]=Créateur de thèmes
GenericName[it]=Creatore di temi
GenericName[nl]=Themamaker
GenericName[pt_BR]=Criador de temas
GenericName[ru]=Создание тем
Comment=Style your desktop: colors, shapes, panel and window borders
Comment[de]=Gestalte deinen Desktop: Farben, Formen, Leiste und Fensterrahmen
Comment[es]=Dale estilo a tu escritorio: colores, formas, panel y bordes de ventana
Comment[fr]=Personnalisez votre bureau : couleurs, formes, panneau et bordures de fenêtre
Comment[it]=Dai stile al tuo desktop: colori, forme, pannello e bordi delle finestre
Comment[nl]=Geef je bureaublad stijl: kleuren, vormen, paneel en vensterranden
Comment[pt_BR]=Dê estilo à sua área de trabalho: cores, formas, painel e bordas de janela
Comment[ru]=Оформите свой рабочий стол: цвета, формы, панель и рамки окон
Exec=theme-roller
Icon={APP_ID}
Terminal=false
StartupNotify=true
Categories=Settings;DesktopSettings;GTK;
Keywords=theme;colour;color;accent;appearance;cinnamon;gtk;style;icons;
"""

AUTOSTART = """\
[Desktop Entry]
Type=Application
Name=Theme Roller theme watcher
Comment=Takes Theme Roller's colors out of apps when you pick another theme
Exec=theme-roller watch
NoDisplay=true
X-GNOME-Autostart-enabled=true
"""

METAINFO = f"""\
<?xml version="1.0" encoding="UTF-8"?>
<component type="desktop-application">
  <id>{APP_ID}</id>
  <name>Theme Roller</name>
  <summary>Style your Linux Mint Cinnamon desktop</summary>
  <metadata_license>CC0-1.0</metadata_license>
  <project_license>GPL-3.0-or-later</project_license>
  <developer id="io.github.xlcheese"><name>Wesley Hayslip</name></developer>
  <description>
    <p>Theme Roller makes a complete theme for Linux Mint's Cinnamon desktop from your own
    colors and a few sliders: GTK 3 and GTK 4 apps, libadwaita apps, the Cinnamon panel and
    menus, and the window borders. Pick a style for how things are drawn, see it in a live
    preview, and click Apply.</p>
    <p>It also brings your colors to apps that don't read the theme on their own, recolors your
    folder icons, and shares themes as a single file.</p>
  </description>
  <launchable type="desktop-id">{APP_ID}.desktop</launchable>
  <url type="homepage">https://github.com/xlcheese/theme-roller</url>
  <url type="bugtracker">https://github.com/xlcheese/theme-roller/issues</url>
  <content_rating type="oars-1.1"/>
</component>
"""

LAUNCHER = f"""\
#!/usr/bin/python3
\"\"\"Theme Roller: no arguments opens the app; otherwise the command line
(theme-roller --help).\"\"\"
import sys

sys.path.insert(0, "/{SHARE}")
if len(sys.argv) > 1:
    from cheeselooks.cli import main
else:
    from cheeselooks.app import main
sys.exit(main())
"""

POSTINST = f"""\
#!/bin/sh
set -e
# faster starts: compile the program once, here
python3 -m compileall -q /{SHARE}/cheeselooks >/dev/null 2>&1 || true
"""

PRERM = f"""\
#!/bin/sh
set -e
rm -rf /{SHARE}/cheeselooks/__pycache__
"""


def version() -> str:
    text = (ROOT / "cheeselooks" / "__init__.py").read_text(encoding="utf-8")
    v = re.search(r'__version__\s*=\s*"([^"]+)"', text).group(1)
    return re.sub(r"\.?(dev|a|b|rc)(\d*)$", r"~\1\2", v)       # 0.1.0.dev0 -> 0.1.0~dev0 (sorts before 0.1.0)


def maintainer() -> str:
    if os.environ.get("MAINTAINER"):
        return os.environ["MAINTAINER"]
    def git(key: str) -> str:
        try:
            return subprocess.run(["git", "config", key], capture_output=True, text=True,
                                  cwd=ROOT).stdout.strip()
        except OSError:
            return ""
    name, email = git("user.name"), git("user.email")
    if not (name and email):
        sys.exit('No maintainer: set git config user.name and user.email, or MAINTAINER="Name <email>"')
    return f"{name} <{email}>"


def copy_tree(src: Path, dest: Path, keep=lambda p: True) -> None:
    for f in sorted(src.rglob("*")):
        if f.is_dir() or "__pycache__" in f.parts or not keep(f):
            continue
        out = dest / f.relative_to(src)
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, out)


def write(path: Path, text: str, mode: int = 0o644) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    path.chmod(mode)


def copyright_file() -> str:
    gpl = "/usr/share/common-licenses/GPL-3"
    return ("Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/\n"
            "Upstream-Name: Theme Roller\n"
            "Source: https://github.com/xlcheese/theme-roller\n\n"
            "Files: *\n"
            "Copyright: 2026 Wesley Hayslip\n"
            "License: GPL-3.0-or-later\n"
            f" On Debian systems, the full text is in {gpl}.\n\n"
            "Files: data/icons/mint-y/* data/icons/yaru/*\n"
            "Copyright: Sam Hewitt, Alexey Varfolomeev (Mint-Y); Canonical and the Yaru contributors\n"
            "License: CC-BY-SA-4.0\n"
            " https://creativecommons.org/licenses/by-sa/4.0/\n\n"
            "Files: data/icons/breeze/*\n"
            "Copyright: the KDE contributors\n"
            "License: LGPL-3.0-or-later\n"
            " On Debian systems, the full text is in /usr/share/common-licenses/LGPL-3.\n\n"
            "Files: templates/*\n"
            "Copyright: the Linux Mint team (Mint-Y theme, which the templates are built on)\n"
            "License: GPL-3.0-or-later\n")


def build(out_dir: Path) -> Path:
    ver = version()
    with tempfile.TemporaryDirectory() as tmp:
        pkg = Path(tmp) / f"{PACKAGE}_{ver}_all"
        share = pkg / SHARE
        # the program and what it reads (no tests, tools, mockups or reference)
        copy_tree(ROOT / "cheeselooks", share / "cheeselooks", lambda p: p.suffix == ".py")
        for d in ("templates", "styles", "presets"):
            copy_tree(ROOT / d, share / d)
        copy_tree(ROOT / "po", share / "po", lambda p: p.suffix == ".po")
        copy_tree(ROOT / "data", share / "data",
                  lambda p: p.suffix != ".desktop" and p.name != "comet-source.webp")
        write(pkg / "usr/bin/theme-roller", LAUNCHER, 0o755)
        write(pkg / "usr/share/applications" / f"{APP_ID}.desktop", DESKTOP)
        write(pkg / "usr/share/metainfo" / f"{APP_ID}.metainfo.xml", METAINFO)
        write(pkg / "etc/xdg/autostart/theme-roller-watch.desktop", AUTOSTART)
        icons = pkg / "usr/share/icons/hicolor"
        (icons / "256x256/apps").mkdir(parents=True)
        shutil.copy2(ROOT / "data/icons/xl-cheeselooks-256.png", icons / f"256x256/apps/{APP_ID}.png")
        (icons / "scalable/apps").mkdir(parents=True)
        shutil.copy2(ROOT / "data/icons/xl-cheeselooks.svg", icons / f"scalable/apps/{APP_ID}.svg")
        doc = pkg / "usr/share/doc" / PACKAGE
        write(doc / "copyright", copyright_file())
        shutil.copy2(ROOT / "README.md", doc / "README.md")
        # control
        size = sum(f.stat().st_size for f in pkg.rglob("*") if f.is_file()) // 1024
        control = (f"Package: {PACKAGE}\n"
                   f"Version: {ver}\n"
                   "Architecture: all\n"
                   f"Maintainer: {maintainer()}\n"
                   f"Installed-Size: {size}\n"
                   f"Depends: {DEPENDS}\n"
                   f"Recommends: {RECOMMENDS}\n"
                   f"Suggests: {SUGGESTS}\n"
                   "Section: x11\n"
                   "Priority: optional\n"
                   "Homepage: https://github.com/xlcheese/theme-roller\n"
                   f"Description: {DESCRIPTION}")
        write(pkg / "DEBIAN/control", control)
        write(pkg / "DEBIAN/postinst", POSTINST, 0o755)
        write(pkg / "DEBIAN/prerm", PRERM, 0o755)
        for d in [p for p in pkg.rglob("*") if p.is_dir()] + [pkg]:
            d.chmod(0o755)
        out_dir.mkdir(parents=True, exist_ok=True)
        deb = out_dir / f"{PACKAGE}_{ver}_all.deb"
        subprocess.run(["dpkg-deb", "--root-owner-group", "-Zxz", "--build", str(pkg), str(deb)],
                       check=True, stdout=subprocess.DEVNULL)
    return deb


if __name__ == "__main__":
    deb = build(ROOT / "dist")
    print(f"Built {deb} ({deb.stat().st_size // 1024} KB)")
