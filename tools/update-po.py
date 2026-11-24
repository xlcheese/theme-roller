#!/usr/bin/env python3
"""Update the translation files: po/theme-roller.pot and every po/<lang>.po.

    tools/update-po.py            update them, and list what each language still needs
    tools/update-po.py --check    change nothing; exit 1 if a translation is missing
                                  or breaks a {placeholder} or <markup>

The template lists every string the app marks with _("...") or N_("..."),
found by reading the code (no gettext tools needed), plus the labels the app
builds from setting names (choices such as "Bold", "Overlay"). Each language
file keeps its translations; new strings are added untranslated, and strings
the app no longer uses are dropped.

To add a language: tools/update-po.py --new <code>   (e.g. --new pl)
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cheeselooks import i18n  # noqa: E402

PO = ROOT / "po"
POT = PO / "theme-roller.pot"
SOURCES = sorted((ROOT / "cheeselooks").glob("*.py"))
LANG_NAMES = {"de": "German", "es": "Spanish", "fr": "French", "it": "Italian", "nl": "Dutch",
              "pt_BR": "Portuguese (Brazil)", "ru": "Russian"}
# who revised each language (the file's header says so)
REVIEWERS = {"es": "axrusar (Linux Mint forums)"}
PLURAL_FORMS = {"ru": "nplurals=3; plural=(n%10==1 && n%100!=11 ? 0 : n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2);",
                "fr": "nplurals=2; plural=(n > 1);", "pt_BR": "nplurals=2; plural=(n > 1);"}


def marked() -> dict[str, list[str]]:
    """msgid -> ["cheeselooks/app.py:123", ...] for every _() and N_() call."""
    found: dict[str, list[str]] = {}
    for f in SOURCES:
        tree = ast.parse(f.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                    and node.func.id in ("_", "N_") and node.args
                    and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str)):
                found.setdefault(node.args[0].value, []).append(f"{f.relative_to(ROOT)}:{node.lineno}")
    return found


def built_labels() -> dict[str, list[str]]:
    """Labels the app makes from setting names at run time, then translates:
    a setting's name with no entry in LABELS, and the choices shown as buttons."""
    from cheeselooks import settings
    from cheeselooks.app import CHOICE_LABELS, LABELS          # noqa: WPS433 (needs GTK)
    out: dict[str, list[str]] = {}
    for path, kind, extra in settings._RULES:
        if path[-1] not in LABELS:
            out.setdefault(path[-1].replace("_", " ").capitalize(), []).append("settings._RULES")
        # as app._control shows them: up to three as buttons, labels built from
        # the choice; more in a list, by CHOICE_LABELS' names where it has them
        if kind.startswith("choice") and path[-1] != "button_glyphs":
            names = CHOICE_LABELS.get(path[-1], {}) if len(extra) > 3 else {}
            for choice in extra:
                if choice not in names:
                    out.setdefault(choice.replace("_", " ").capitalize(), []).append("settings._RULES")
    return out


def _quote(text: str) -> str:
    """A .po string: one line, or several split after each \\n."""
    def q(t: str) -> str:
        return '"' + t.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\t", "\\t") + '"'
    if "\n" not in text[:-1] and len(text) < 70:
        return q(text)
    parts = re.split(r"(?<=\n)", text)
    return '""\n' + "\n".join(q(p) for p in parts if p)


def write_po(path: Path, entries: dict[str, list[str]], translations: dict[str, str], header: str) -> None:
    lines = [header.rstrip("\n"), ""]
    for msgid in sorted(entries, key=lambda m: (entries[m][0].split(":")[0], int(entries[m][0].split(":")[1])
                                                 if entries[m][0].count(":") else 0, m)):
        refs = " ".join(dict.fromkeys(entries[msgid]))
        lines.append(f"#: {refs}")
        if re.search(r"\{\w+\}", msgid):
            lines.append("#, python-brace-format")
        lines.append(f"msgid {_quote(msgid)}")
        lines.append(f"msgstr {_quote(translations.get(msgid, ''))}")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def header(lang: str | None) -> str:
    name = LANG_NAMES.get(lang, lang) if lang else "LANGUAGE"
    plural = PLURAL_FORMS.get(lang or "", "nplurals=2; plural=(n != 1);")
    return (f"# {name} translation of Theme Roller.\n"
            "# This file is distributed under the same license as Theme Roller (GPL-3.0-or-later).\n"
            + (f"# Revised by {REVIEWERS[lang]}.\n" if lang in REVIEWERS else "")
            + "#\n"
            'msgid ""\n'
            'msgstr ""\n'
            '"Project-Id-Version: theme-roller\\n"\n'
            '"Report-Msgid-Bugs-To: https://github.com/xlcheese/theme-roller/issues\\n"\n'
            f'"Language: {lang or ""}\\n"\n'
            '"MIME-Version: 1.0\\n"\n'
            '"Content-Type: text/plain; charset=UTF-8\\n"\n'
            '"Content-Transfer-Encoding: 8bit\\n"\n'
            f'"Plural-Forms: {plural}\\n"\n')


PLACEHOLDER = re.compile(r"\{\w+\}")
TAG = re.compile(r"</?\w+[^>]*>")


def problems(msgid: str, msgstr: str) -> list[str]:
    """What a translation breaks: its {placeholders} and <markup> must match the English."""
    out = []
    if sorted(PLACEHOLDER.findall(msgid)) != sorted(PLACEHOLDER.findall(msgstr)):
        out.append(f"placeholders {sorted(set(PLACEHOLDER.findall(msgid)))} differ")
    if sorted(re.sub(r"\s.*", ">", t) for t in TAG.findall(msgid)) != \
            sorted(re.sub(r"\s.*", ">", t) for t in TAG.findall(msgstr)):
        out.append("markup tags differ")
    if re.search(r"&\w+;|<\w", msgid) and re.search(r"&(?!amp;|lt;|gt;|quot;|apos;|#)", msgstr):
        out.append("a bare & in markup (write &amp;)")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--new", metavar="CODE")
    args = ap.parse_args()

    entries = marked()
    for msgid, refs in built_labels().items():
        entries.setdefault(msgid, []).extend(refs)
    entries.pop("", None)

    if args.new:
        target = PO / f"{args.new}.po"
        if target.exists():
            print(f"{target} already exists")
            return 1
        write_po(target, entries, {}, header(args.new))
        print(f"Wrote {target}: translate its msgstr lines")
        return 0

    status = 0
    if not args.check:
        PO.mkdir(exist_ok=True)
        write_po(POT, entries, {}, header(None))
    print(f"{len(entries)} strings")
    for po in sorted(PO.glob("*.po")):
        lang = po.stem
        have = i18n.read_po(po)
        broken = {m: problems(m, t) for m, t in have.items() if m in entries and problems(m, t)}
        missing = [m for m in entries if m not in have]
        unused = [m for m in have if m not in entries]
        if not args.check:
            write_po(po, entries, {m: t for m, t in have.items() if m in entries}, header(lang))
        print(f"  {lang}: {len(entries) - len(missing)} translated, {len(missing)} missing"
              + (f", {len(unused)} no longer used (dropped)" if unused and not args.check else ""))
        for m, why in broken.items():
            print(f"    BROKEN {m[:60]!r}: {'; '.join(why)}")
            status = 1
        if args.check and missing:
            for m in missing[:5]:
                print(f"    missing: {m[:70]!r}")
            status = 1
    return status


if __name__ == "__main__":
    sys.exit(main())
