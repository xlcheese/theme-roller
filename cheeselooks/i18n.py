"""Translations of the app's on-screen text.

Strings are marked with _("...") and translated from po/<language>.po, the
standard gettext format that Poedit and Weblate edit. The .po files are read
directly, so nothing needs compiling and a checkout of the repository is
translated as it is. A missing file or string shows the English.

The language is the first of LANGUAGE (a colon-separated list), LC_ALL,
LC_MESSAGES and LANG that has a file: "pt_BR.UTF-8" tries pt_BR.po, then pt.po.
THEME_ROLLER_LANG overrides them all (e.g. THEME_ROLLER_LANG=de to try German).

Only the app's own text is translated. Theme, style and command names, the
command line, and the files Theme Roller writes stay in English.

Adding a language: copy po/theme-roller.pot to po/<code>.po, translate the
msgstr lines, and run tools/update-po.py to check it. See po/README.md.
"""

from __future__ import annotations

import ast
import os
from pathlib import Path

DOMAIN = "theme-roller"


def po_dir() -> Path:
    from . import paths          # here: paths imports modules that import this one
    return paths.data_dir() / "po"


def _unquote(text: str) -> str:
    return ast.literal_eval(text) if text.startswith('"') else ""


def read_po(path: Path) -> dict[str, str]:
    """msgid -> msgstr for every translated, non-fuzzy entry of a .po file."""
    table: dict[str, str] = {}
    msgid = msgstr = None
    field = None
    fuzzy = False

    def done() -> None:
        if msgid and msgstr and not fuzzy:
            table[msgid] = msgstr

    for raw in path.read_text(encoding="utf-8").splitlines() + [""]:
        line = raw.strip()
        if not line:
            done()
            msgid = msgstr = field = None
            fuzzy = False
        elif line.startswith("#,"):
            fuzzy = "fuzzy" in line
        elif line.startswith("#"):
            continue
        elif line.startswith("msgid "):
            if msgid is not None:            # no blank line between entries
                done()
                msgstr, fuzzy = None, False
            msgid, field = _unquote(line[6:]), "id"
        elif line.startswith("msgstr "):
            msgstr, field = _unquote(line[7:]), "str"
        elif line.startswith('"'):
            if field == "id":
                msgid += _unquote(line)
            elif field == "str":
                msgstr += _unquote(line)
    return table


def read_po_ids(path: Path) -> list[str]:
    """Every msgid in a .po or .pot file, in the file's order (translated or not)."""
    ids: list[str] = []
    cur = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.startswith("msgid "):
            cur = _unquote(line[6:])
        elif line.startswith('"') and cur is not None:
            cur += _unquote(line)
        elif line.startswith("msgstr "):
            if cur:
                ids.append(cur)
            cur = None
    return ids


def _candidates() -> list[str]:
    forced = os.environ.get("THEME_ROLLER_LANG")
    if forced:
        values = [forced]
    else:
        values = os.environ.get("LANGUAGE", "").split(":")
        values += [os.environ.get(v, "") for v in ("LC_ALL", "LC_MESSAGES", "LANG")]
    out: list[str] = []
    for v in values:
        v = v.split(".")[0].split("@")[0]
        if not v or v in ("C", "POSIX"):
            continue
        for code in (v, v.split("_")[0]):
            if code not in out:
                out.append(code)
    return out


def language() -> str:
    """The language code in use ("en" when the English is shown)."""
    for code in _candidates():
        if code == "en" or code.startswith("en_"):
            return "en"
        if (po_dir() / f"{code}.po").is_file():
            return code
    return "en"


def _load() -> dict[str, str]:
    code = language()
    if code == "en":
        return {}
    try:
        return read_po(po_dir() / f"{code}.po")
    except (OSError, ValueError, SyntaxError):
        return {}


_TABLE: dict[str, str] | None = None     # loaded at the first translation (importing this
                                          # module stays free of the paths/tokens imports)


def use_english() -> None:
    """Show the English from now on (the command line: it stays English)."""
    global _TABLE
    _TABLE = {}


def _(text: str) -> str:
    """The translation of text, or text itself."""
    global _TABLE
    if _TABLE is None:
        _TABLE = _load()
    return _TABLE.get(text, text) if text else text


def N_(text: str) -> str:
    """Marks text for translation without translating it here (it's
    translated where it's shown, with _())."""
    return text
