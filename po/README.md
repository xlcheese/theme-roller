# Translating Theme Roller

Theme Roller is translated with standard gettext `.po` files, one per language:

| File | Language |
|---|---|
| `de.po` | German |
| `es.po` | Spanish |
| `fr.po` | French |
| `it.po` | Italian |
| `nl.po` | Dutch |
| `pt_BR.po` | Portuguese (Brazil) |
| `ru.po` | Russian |

`theme-roller.pot` is the template: every piece of text the app shows, in English.

The app reads the `.po` files directly, so there is nothing to compile. It picks the language from your system (Mint's language setting). To try a language without changing your system:

```bash
THEME_ROLLER_LANG=de ./bin/theme-roller
```

## Improving a translation

Open the language's `.po` file in [Poedit](https://poedit.net) or any text editor, change the `msgstr` lines, and save. Then check it:

```bash
tools/update-po.py --check
```

Keep these as they are in the English:

- **`{placeholders}`** such as `{theme}` or `{file}`. The app fills them in. You can move them within the sentence.
- **Markup** such as `<b>…</b>`, `<tt>…</tt>` and the `<a href=…>` link.
- **Names**: Theme Roller, xl-Cheeselooks, Cinnamon, Linux Mint, GNOME, Flatpak, Qt, VLC, Xed, gedit, Meld, libadwaita, style.toml.

Other things to watch:

- **Use the same words as the buttons and tabs.** Notes refer to them by name: "click **Apply**", "the Integration tab".
- **Keep labels short.** A setting's name sits beside a slider, and a long one widens the whole window. Aim for no longer than the English "Notification opacity".

## Adding a language

```bash
tools/update-po.py --new pl
```

This writes `po/pl.po` with every `msgstr` empty. Fill them in and run the check. Use the language's code: `pl`, `ja`, `zh_CN`, and so on.

## When the app's text changes

Run `tools/update-po.py`. It rewrites the template from the code and updates every language file:

- each file keeps its translations;
- new text is added untranslated;
- text the app no longer uses is dropped.

It then lists what each language still needs.
