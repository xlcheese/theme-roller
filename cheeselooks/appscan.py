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
# (VLC and NVIDIA Settings load theirs as a plugin: Qt, GTK 3)
KNOWN = {"libreoffice": GTK3, "soffice": GTK3, "firefox": GTK3, "thunderbird": GTK3,
         "vlc": QT, "nvidia-settings": GTK3}
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


ALSO = "_also"    # an entry's other copies, further down the search path (as the menu, yours first)


def menu_apps() -> list[tuple[str, dict[str, str]]]:
    """(id, entry) for each app the menu shows; an earlier directory wins, as the
    menu's. Later copies of the same app are kept in entry[ALSO]: a copy in your
    home folder may start the app through another program (Buffet Menu's)."""
    found: dict[str, dict] = {}
    for d in desktop_dirs():
        for f in sorted(d.rglob("*.desktop")):
            app_id = f.relative_to(d).as_posix().replace("/", "-")
            e = read_desktop(f)
            if app_id in found:
                found[app_id].setdefault(ALSO, []).append(e)
                continue
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
        refs = [Path(r) for r in re.findall(r"(/(?:usr|opt)/[\w./+-]+)", text)]
        refs += [Path(w) for w in (shutil.which(n) for n in re.findall(r"\b(?:exec|pkexec)\s+([\w.+-]+)", text)) if w]
        for p in refs:
            if p.is_file() and p != f:
                k = kind_of_file(p, follow - 1)
                if k:
                    return k
    # a Python launcher: the app's code is an installed package (blueman, onboard,
    # pdfarranger, mintstick...): its toolkit is imported somewhere in there
    if follow and text.startswith("#!") and "python" in text.split("\n", 1)[0]:
        for module in dict.fromkeys(re.findall(r"^\s*(?:from|import)\s+([A-Za-z_]\w*)", text, re.M)):
            for pkg in python_package(module):
                k = kind_of_package(pkg)
                if k:
                    return k
    if f.suffix == ".py":   # a Python app may import its toolkit in another file of its package
        for other in sorted(f.parent.rglob("*.py"))[:80]:
            if other != f:
                try:
                    t = other.read_text(encoding="utf-8", errors="replace")[:100_000]
                except OSError:
                    continue
                for pattern, kind in SCRIPT_KINDS:
                    if pattern.search(t):
                        return kind
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


PY_SITES = sorted(set(Path(p) for pattern in ("/usr/lib/python3/dist-packages", "/usr/lib/python3*/site-packages",
                                               "/usr/local/lib/python3*/dist-packages",
                                               "/usr/lib/python3*/dist-packages")
                     for p in __import__("glob").glob(pattern)))
STDLIB = {"os", "sys", "re", "gi", "json", "subprocess", "time", "gettext", "locale", "signal", "argparse",
          "threading", "pathlib", "shutil", "setproctitle", "dbus", "traceback", "logging", "typing"}


def python_package(module: str) -> list[Path]:
    """An installed package's folder (or module file), if `module` is one."""
    if module in STDLIB:
        return []
    out = []
    for site in PY_SITES:
        for p in (site / module, site / f"{module}.py"):
            if p.exists():
                out.append(p)
    return out


def kind_of_package(pkg: Path) -> str | None:
    files = [pkg] if pkg.is_file() else sorted(pkg.rglob("*.py"))[:150]
    for f in files:
        try:
            t = f.read_text(encoding="utf-8", errors="replace")[:100_000]
        except OSError:
            continue
        for pattern, kind in SCRIPT_KINDS:
            if pattern.search(t):
                return kind
    return None


def kind_of_file(f: Path, follow: int = 1) -> str | None:
    if f.name in KNOWN:
        return KNOWN[f.name]
    if any((f.resolve().parent / m).exists() for m in WEB_MARKERS):
        return WEB                                 # Electron or Chrome, started by a program or a script
    libs = elf_libraries(f)
    if libs is not None:
        return kind_of_elf(f, libs)
    return kind_of_script(f, follow)


WRAPPERS = {"env", "pkexec", "sh", "bash", "dash", "gksu", "gksudo", "sudo", "nice", "ionice", "python3",
            "python", "perl", "java", "exec"}


def programs(exec_line: str) -> list[Path]:
    """Every program or script an Exec= line names, in order: the first may only
    start another (pkexec, python3, a launcher such as Buffet Menu's)."""
    try:
        words = shlex.split(exec_line)
    except ValueError:
        words = exec_line.split()
    out = []
    for w in words:
        if w.startswith(("%", "-")) or ("=" in w and not w.startswith("/")):
            continue
        found = w if w.startswith("/") else shutil.which(w)
        if found and Path(found).is_file() and Path(found) not in out:
            out.append(Path(found))
    return out


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
    # this entry, then its other copies (yours may start it through another program)
    for entry in [e] + e.get(ALSO, []):
        progs = programs(entry.get("Exec", ""))
        if any(p.name in EDITORS for p in progs):
            return App(name, EDITOR)
        for p in progs:
            if p.name in WRAPPERS:
                continue
            kind = kind_of_file(p)
            if kind:
                return App(name, kind)
    return App(name, UNKNOWN)


def why(app_id: str, e: dict) -> list[str]:
    """For `theme-roller scan --why`: how an app starts, and what each part is."""
    out = []
    for entry in [e] + e.get(ALSO, []):
        out.append(f"  Exec={entry.get('Exec', '')}")
        for p in programs(entry.get("Exec", "")):
            try:
                with open(p, "rb") as fh:
                    head = fh.read(120)
            except OSError:
                head = b""
            what = ("program" if head[:4] == b"\x7fELF" else
                    "script: " + head.split(b"\n", 1)[0].decode("latin-1", "replace") if head[:2] == b"#!" else "file")
            out.append(f"    {p} ({what}) -> {kind_of_file(p) or 'nothing found'}")
    return out


def scan() -> Scan:
    return Scan([classify(app_id, e) for app_id, e in menu_apps()])
