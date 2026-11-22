"""Scan my apps (Integration tab): which of your apps are which kind.

New users can't know that their apps come from different toolkits, each
looking for its colors somewhere else (xl_cheese, 22 Nov). This lists the
apps in your menu by kind, so "why doesn't app X match?" has an answer.

How an app's kind is found, without running anything:
  - the menu's apps: their .desktop files, as the menu reads them (Flatpak
    apps' exported ones too), hidden ones skipped;
  - Flatpak apps: the runtime in their metadata (GNOME's or KDE's);
  - programs: the libraries they ask for, read from the file itself (the ELF
    file's .dynstr table: libadwaita, GTK 4, Qt, GTK 3);
  - scripts (many Mint tools are Python): the toolkit they import, following
    one launcher step to the script it runs;
  - web-based apps (Electron, Chrome apps): they draw their own look.
Anything else is "couldn't tell", never guessed.
"""
from __future__ import annotations

import os
import re
import shlex
import shutil
import struct
from dataclasses import dataclass, field
from pathlib import Path

from . import paths

# the kinds, in the order the scan lists them
GTK3, GNOME, FLATPAK, QT, EDITOR, TERMINAL, WEB, UNKNOWN = (
    "gtk3", "gnome", "flatpak", "qt", "editor", "terminal", "web", "unknown")
EDITORS = {"xed", "gedit", "meld"}        # the Text editors switch (editor.py)
# apps that choose their toolkit at runtime, whose look on Mint is known
KNOWN = {"libreoffice": GTK3, "soffice": GTK3, "firefox": GTK3, "thunderbird": GTK3}
LIB_DIRS = [Path(p) for p in ("/usr/lib/x86_64-linux-gnu", "/usr/lib/aarch64-linux-gnu", "/usr/lib64",
                              "/usr/lib", "/lib/x86_64-linux-gnu", "/lib")]
WEB_MARKERS = ("chrome_100_percent.pak", "resources.pak", "app.asar", "snapshot_blob.bin")


@dataclass
class App:
    name: str
    kind: str
    detail: str = ""          # "KDE runtime", "script"...


@dataclass
class Scan:
    apps: list[App] = field(default_factory=list)

    def by_kind(self, kind: str) -> list[App]:
        return sorted((a for a in self.apps if a.kind == kind), key=lambda a: a.name.lower())


# ------------------------------------------------------------------ the menu's apps

def desktop_dirs() -> list[Path]:
    data_home = paths._xdg("XDG_DATA_HOME", paths.HOME / ".local" / "share")
    dirs = [data_home / "applications", data_home / "flatpak" / "exports" / "share" / "applications",
            Path("/var/lib/flatpak/exports/share/applications")]
    for d in os.environ.get("XDG_DATA_DIRS", "/usr/local/share:/usr/share").split(":"):
        if d:
            dirs.append(Path(d) / "applications")
    seen, out = set(), []
    for d in dirs:
        if d not in seen and d.is_dir():
            seen.add(d)
            out.append(d)
    return out


def read_desktop(f: Path) -> dict[str, str]:
    """The [Desktop Entry] keys we need (untranslated)."""
    out, inside = {}, False
    try:
        lines = f.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return out
    for line in lines:
        line = line.strip()
        if line.startswith("["):
            inside = line == "[Desktop Entry]"
            continue
        if inside and "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            if "[" not in k:
                out.setdefault(k.strip(), v.strip())
    return out


def menu_apps() -> list[tuple[str, dict[str, str]]]:
    """(id, entry) for each app the menu shows; an earlier directory wins, as the menu's."""
    found: dict[str, dict[str, str]] = {}
    for d in desktop_dirs():
        for f in sorted(d.rglob("*.desktop")):
            app_id = f.relative_to(d).as_posix().replace("/", "-")
            if app_id in found:
                continue
            e = read_desktop(f)
            found[app_id] = e
    out = []
    for app_id, e in found.items():
        if e.get("Type", "Application") != "Application" or not e.get("Name"):
            continue
        if e.get("NoDisplay", "").lower() == "true" or e.get("Hidden", "").lower() == "true":
            continue
        not_in = e.get("NotShowIn", "").split(";")
        only_in = [x for x in e.get("OnlyShowIn", "").split(";") if x]
        if "X-Cinnamon" in not_in or (only_in and "X-Cinnamon" not in only_in and "GNOME" not in only_in):
            continue
        out.append((app_id, e))
    return out


# ------------------------------------------------------------------ an app's kind

def elf_libraries(f: Path) -> list[str] | None:
    """The libraries an ELF program asks for (its .dynstr strings), or None if
    it isn't one. Read from the file; nothing is run."""
    try:
        with open(f, "rb") as fh:
            head = fh.read(64)
            if head[:4] != b"\x7fELF":
                return None
            is64, little = head[4] == 2, head[5] == 1
            end = "<" if little else ">"
            if is64:
                shoff, = struct.unpack(end + "Q", head[0x28:0x30])
                shentsize, shnum, shstrndx = struct.unpack(end + "HHH", head[0x3A:0x40])
            else:
                shoff, = struct.unpack(end + "I", head[0x20:0x24])
                shentsize, shnum, shstrndx = struct.unpack(end + "HHH", head[0x2E:0x34])
            if not shoff or not shnum or shnum > 4096:
                return []

            def section(i):
                fh.seek(shoff + i * shentsize)
                raw = fh.read(shentsize)
                if is64:
                    name, typ, _fl, _addr, off, size = struct.unpack(end + "IIQQQQ", raw[:40])
                else:
                    name, typ, _fl, _addr, off, size = struct.unpack(end + "IIIIII", raw[:24])
                return name, typ, off, size
            _n, _t, stroff, strsize = section(shstrndx)
            fh.seek(stroff)
            names = fh.read(min(strsize, 1 << 20))
            for i in range(shnum):
                n, typ, off, size = section(i)
                label = names[n:names.find(b"\0", n)]
                if label == b".dynstr" and size < (8 << 20):
                    fh.seek(off)
                    return [s.decode("latin-1") for s in fh.read(size).split(b"\0") if s]
    except (OSError, struct.error):
        return None
    return []


def kind_of_libraries(libs: list[str]) -> str | None:
    text = " ".join(libs)
    if "libadwaita-1.so" in text or "libgtk-4.so" in text:
        return GNOME
    if re.search(r"libQt[56](Core|Widgets|Gui)\.so", text):
        return QT
    if "libgtk-3.so" in text:
        return GTK3
    return None


SCRIPT_KINDS = ((re.compile(r"""require_version\(\s*['"]Adw['"]|from gi\.repository import [^\n]*\bAdw\b|"""
                            r"""require_version\(\s*['"]Gtk['"]\s*,\s*['"]4\.0"""), GNOME),
                (re.compile(r"\bPyQt[56]\b|\bPySide[26]?\b"), QT),
                (re.compile(r"""require_version\(\s*['"]Gtk['"]\s*,\s*['"]3\.0|from gi\.repository import [^\n]*\bGtk\b"""), GTK3))


def kind_of_script(f: Path, follow: int = 1) -> str | None:
    try:
        text = f.read_text(encoding="utf-8", errors="replace")[:200_000]
    except OSError:
        return None
    for pattern, kind in SCRIPT_KINDS:
        if pattern.search(text):
            return kind
    if follow:      # a launcher: the script or program it runs (Mint's tools: /usr/lib/linuxmint/...)
        for ref in re.findall(r"(/usr/(?:lib|share|bin)/[\w./+-]+)", text):
            p = Path(ref)
            if p.is_file() and p != f:
                k = kind_of_file(p, follow - 1)
                if k:
                    return k
    return None


def library_path(name: str, origin: Path, libs: list[str]) -> Path | None:
    """Where a library an ELF file asks for lives: its RUNPATH, then the usual places."""
    dirs = []
    for entry in libs:
        if "/" in entry and not entry.endswith((".so",)) and ".so." not in entry:
            for part in entry.split(":"):
                dirs.append(Path(part.replace("$ORIGIN", str(origin)).replace("${ORIGIN}", str(origin))))
    for d in dirs + LIB_DIRS:
        p = d / name
        if p.exists():
            return p
    return None


def kind_of_elf(f: Path, libs: list[str], depth: int = 2) -> str | None:
    """Its toolkit, from its libraries, and theirs (Inkscape's program leaves
    GTK to its own library): two steps, standard libraries skipped."""
    kind = kind_of_libraries(libs)
    if kind or depth == 0:
        return kind
    origin = f.resolve().parent
    for name in libs:
        if not name.startswith("lib") or ".so" not in name or name.startswith(("libc.", "libm.", "libstdc++",
                                                                              "libgcc", "libpthread", "libdl.")):
            continue
        p = library_path(name, origin, libs)
        sub = elf_libraries(p) if p else None
        if sub:
            kind = kind_of_elf(p, sub, depth - 1)
            if kind:
                return kind
    return None


def kind_of_file(f: Path, follow: int = 1) -> str | None:
    if f.name in KNOWN:
        return KNOWN[f.name]
    libs = elf_libraries(f)
    if libs is not None:
        if any((f.resolve().parent / m).exists() for m in WEB_MARKERS):
            return WEB
        return kind_of_elf(f, libs)
    return kind_of_script(f, follow)


def program(exec_line: str) -> Path | None:
    """The program an Exec= line runs (env and its settings skipped)."""
    try:
        words = shlex.split(exec_line)
    except ValueError:
        words = exec_line.split()
    words = [w for w in words if not w.startswith("%")]
    while words and (words[0] == "env" or "=" in words[0] and not words[0].startswith("/")):
        words = words[1:]
    if not words:
        return None
    found = shutil.which(words[0]) if not words[0].startswith("/") else words[0]
    return Path(found) if found and Path(found).exists() else None


def flatpak_runtime(app_id: str) -> str:
    for base in (paths._xdg("XDG_DATA_HOME", paths.HOME / ".local" / "share") / "flatpak", Path("/var/lib/flatpak")):
        meta = base / "app" / app_id / "current" / "active" / "metadata"
        try:
            for line in meta.read_text(encoding="utf-8").splitlines():
                if line.startswith("runtime="):
                    return line.split("=", 1)[1].split("/")[0]
        except OSError:
            continue
    return ""


def classify(app_id: str, e: dict[str, str]) -> App:
    name = e["Name"]
    flat = e.get("X-Flatpak") or (re.search(r"flatpak\s+run\b.*?\s([\w.-]+\.[\w.-]+)", e.get("Exec", "")) or [None, None])[1]
    if flat:
        runtime = flatpak_runtime(flat)
        detail = ("GNOME runtime" if "gnome" in runtime.lower() else
                  "KDE runtime" if "kde" in runtime.lower() else "")
        return App(name, FLATPAK, detail)
    if e.get("Terminal", "").lower() == "true":
        return App(name, TERMINAL)
    prog = program(e.get("Exec", ""))
    if prog is not None and prog.name in EDITORS:
        return App(name, EDITOR)
    kind = kind_of_file(prog) if prog is not None else None
    return App(name, kind or UNKNOWN)


def scan() -> Scan:
    return Scan([classify(app_id, e) for app_id, e in menu_apps()])
