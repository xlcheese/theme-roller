#!/usr/bin/env python3
"""Review pages for native speakers: po/review/<lang>.md, one per language.

    tools/make-review.py

Each page is readable on GitHub without an account or any tools: a short
introduction in that language (how to review, how to reply), a screenshot of
Theme Roller in it (po/review/images/<lang>.png, if made), and a table of every
text: number, English, the translation. Short labels are marked ✂, so a better
wording keeps the window its size. Run after tools/update-po.py; the numbers
follow the template's order, so a reviewer's "#94" finds the same text here.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from cheeselooks import i18n  # noqa: E402

spec = importlib.util.spec_from_file_location("update_po", ROOT / "tools" / "update-po.py")
upd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(upd)

OUT = ROOT / "po" / "review"
RELEASE = "https://github.com/xlcheese/theme-roller/releases/latest"
SHORT = 28      # English this short, without a full stop: a label or a button (keep it short)

# Per language: title, introduction, and the three column headings.
# {release} is the download page.
INTRO = {
 "de": ("Theme Roller auf Deutsch: bitte prüfen",
        "Theme Roller ist ein kostenloses Programm, das den Cinnamon-Desktop von Linux Mint gestaltet. "
        "Die deutsche Übersetzung entstand ohne Muttersprachler. Wenn etwas falsch, holprig oder "
        "unnatürlich klingt, sag uns bitte Bescheid. Schon zehn Minuten helfen sehr.",
        ["**Mit dem Programm:** Ist dein Mint auf Deutsch eingestellt, installiere Theme Roller "
         "([Download]({release})) und klicke dich durch die Reiter.",
         "**Ohne Installation:** Lies einfach die Tabelle unten.",
         "**Antworten:** im Beitrag, in dem du diese Seite gefunden hast, oder auf GitHub: die Nummer und "
         "deine bessere Formulierung, z. B. „#94: … statt …“."],
        ["Bitte beibehalten: Wörter in `{Klammern}` unverändert, Auszeichnungen wie `<b>` unverändert; "
         "kurze Beschriftungen (✂) kurz halten, sonst wird das Fenster breiter; Namen wie Theme Roller, "
         "Cinnamon, GNOME, Flatpak, Qt bleiben."],
        ("Nr.", "Englisch", "Deutsch")),
 "es": ("Theme Roller en español: ayuda para revisarlo",
        "Theme Roller es una aplicación gratuita para personalizar el escritorio Cinnamon de Linux Mint. "
        "La traducción al español se hizo sin un hablante nativo. Si notas algo forzado, raro o poco "
        "natural, avísanos, por favor. Con diez minutos ya ayudas mucho.",
        ["**Con la aplicación:** si tienes Mint en español, instala Theme Roller "
         "([descarga]({release})) y revisa las pestañas.",
         "**Sin instalar nada:** revisa la tabla de abajo.",
         "**Cómo responder:** en la publicación donde viste esta página, o en GitHub: indica el número y "
         "tu propuesta, por ejemplo «#94: … en vez de …»."],
        ["Por favor, conserva: las palabras entre `{llaves}` tal cual y las etiquetas como `<b>`; las "
         "etiquetas cortas (✂) deben seguir siendo breves para que no se ensanche la ventana; los nombres como "
         "Theme Roller, Cinnamon, GNOME, Flatpak y Qt no se traducen."],
        ("N.º", "Inglés", "Español")),
 "fr": ("Theme Roller en français : aidez-nous à le relire",
        "Theme Roller est une application gratuite qui personnalise le bureau Cinnamon de Linux Mint. "
        "La traduction française a été faite sans locuteur natif. Si quelque chose sonne faux, "
        "maladroit ou peu naturel, dites-le-nous. Dix minutes suffisent à beaucoup aider.",
        ["**Avec l'application :** si votre Mint est en français, installez Theme Roller "
         "([téléchargement]({release})) et parcourez les onglets.",
         "**Sans rien installer :** lisez simplement le tableau ci-dessous.",
         "**Pour répondre :** dans la publication où vous avez trouvé cette page, ou sur GitHub : le "
         "numéro et votre meilleure formulation, par ex. « #94 : … plutôt que … »."],
        ["À garder : les mots entre `{accolades}` tels quels, et les balises comme `<b>` ; les libellés "
         "courts (✂) doivent rester courts, sinon la fenêtre s'élargit ; les noms comme Theme Roller, "
         "Cinnamon, GNOME, Flatpak et Qt ne se traduisent pas."],
        ("N°", "Anglais", "Français")),
 "it": ("Theme Roller in italiano: aiutaci a rivederlo",
        "Theme Roller è un'applicazione gratuita che personalizza il desktop Cinnamon di Linux Mint. "
        "La traduzione italiana è stata fatta senza un madrelingua. Se qualcosa suona sbagliato, goffo o "
        "poco naturale, faccelo sapere. Bastano dieci minuti per aiutare molto.",
        ["**Con l'applicazione:** se il tuo Mint è in italiano, installa Theme Roller "
         "([download]({release})) e scorri le schede.",
         "**Senza installare nulla:** leggi la tabella qui sotto.",
         "**Come rispondere:** nel post in cui hai trovato questa pagina, o su GitHub: il numero e la tua "
         "formulazione migliore, ad es. «#94: … invece di …»."],
        ["Da mantenere: le parole tra `{graffe}` così come sono, e i tag come `<b>`; le etichette brevi "
         "(✂) devono restare brevi, altrimenti la finestra si allarga; i nomi come Theme Roller, "
         "Cinnamon, GNOME, Flatpak e Qt non si traducono."],
        ("N.", "Inglese", "Italiano")),
 "nl": ("Theme Roller in het Nederlands: help het na te kijken",
        "Theme Roller is een gratis programma dat het Cinnamon-bureaublad van Linux Mint vormgeeft. De "
        "Nederlandse vertaling is gemaakt zonder moedertaalspreker. Klinkt iets fout, stroef of "
        "onnatuurlijk, laat het ons dan weten. Tien minuten helpt al enorm.",
        ["**Met het programma:** staat je Mint in het Nederlands, installeer dan Theme Roller "
         "([downloaden]({release})) en klik door de tabbladen.",
         "**Zonder iets te installeren:** lees de tabel hieronder.",
         "**Reageren:** in het bericht waar je deze pagina vond, of op GitHub: het nummer en je betere "
         "formulering, bijvoorbeeld ‘#94: … in plaats van …’."],
        ["Graag zo laten: woorden tussen `{accolades}` ongewijzigd, en opmaak zoals `<b>`; korte labels "
         "(✂) moeten kort blijven, anders wordt het venster breder; namen als Theme Roller, Cinnamon, "
         "GNOME, Flatpak en Qt blijven Engels."],
        ("Nr.", "Engels", "Nederlands")),
 "pt_BR": ("Theme Roller em português: ajude a revisar",
           "O Theme Roller é um aplicativo gratuito que personaliza a área de trabalho Cinnamon do Linux "
           "Mint. A tradução para o português foi feita sem um falante nativo. Se algo soar errado, "
           "estranho ou pouco natural, avise a gente. Dez minutos já ajudam muito.",
           ["**Com o aplicativo:** se o seu Mint está em português, instale o Theme Roller "
            "([download]({release})) e percorra as abas.",
            "**Sem instalar nada:** leia a tabela abaixo.",
            "**Como responder:** na publicação onde você encontrou esta página, ou no GitHub: o número e "
            "a sua redação melhor, por exemplo “#94: … em vez de …”."],
           ["Por favor, mantenha: as palavras entre `{chaves}` como estão, e marcações como `<b>`; os "
            "rótulos curtos (✂) precisam continuar curtos, senão a janela fica mais larga; nomes como "
            "Theme Roller, Cinnamon, GNOME, Flatpak e Qt não se traduzem."],
           ("Nº", "Inglês", "Português")),
 "ru": ("Theme Roller на русском: помогите проверить перевод",
        "Theme Roller — бесплатная программа для оформления рабочего стола Cinnamon в Linux Mint. "
        "Русский перевод сделан без носителя языка. Если что-то звучит неправильно, коряво или "
        "неестественно, пожалуйста, сообщите нам. Даже десять минут очень помогут.",
        ["**С программой:** если ваш Mint на русском, установите Theme Roller "
         "([скачать]({release})) и пройдитесь по вкладкам.",
         "**Без установки:** просто прочитайте таблицу ниже.",
         "**Как ответить:** в сообщении, где вы нашли эту страницу, или на GitHub: номер и ваш "
         "вариант, например «#94: … вместо …»."],
        ["Пожалуйста, сохраняйте: слова в `{фигурных скобках}` без изменений, разметку вроде `<b>`; "
         "короткие подписи (✂) должны оставаться короткими, иначе окно станет шире; названия Theme "
         "Roller, Cinnamon, GNOME, Flatpak и Qt не переводятся."],
        ("№", "Английский", "Русский")),
}


def cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", "<br>")


def page(lang: str, msgids: list[str], table: dict[str, str]) -> str:
    title, intro, how, keep, (h_no, h_en, h_tr) = INTRO[lang]
    lines = [f"# {title}", "", intro, ""]
    lines += [f"- {h.format(release=RELEASE)}" for h in how] + [""]
    lines += [f"> {k}" for k in keep] + [""]
    if (OUT / "images" / f"{lang}.png").exists():
        lines += [f"![Theme Roller]({'images/' + lang + '.png'})", ""]
    lines += [f"| {h_no} | {h_en} | {h_tr} |", "|---:|---|---|"]
    for n, m in enumerate(msgids, 1):
        short = len(m) <= SHORT and not m.rstrip().endswith(".") and "\n" not in m
        lines.append(f"| {n}{' ✂' if short else ''} | {cell(m)} | {cell(table.get(m, ''))} |")
    return "\n".join(lines) + "\n"


def main() -> None:
    msgids = list(dict.fromkeys(m for m in i18n.read_po_ids(upd.POT) if m))
    OUT.mkdir(parents=True, exist_ok=True)
    for lang in INTRO:
        table = i18n.read_po(ROOT / "po" / f"{lang}.po")
        (OUT / f"{lang}.md").write_text(page(lang, msgids, table), encoding="utf-8")
        print(f"Wrote {OUT / f'{lang}.md'}")


if __name__ == "__main__":
    main()
