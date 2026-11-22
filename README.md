# Theme Roller

**Good ol' fashioned Linux desktop theming, for Linux Mint Cinnamon.**

<!-- DRAFT OPENING (written by Claude as a starting point): xl_cheese to rework in his own words. -->

Remember when changing how your Linux desktop looked was half the fun? You'd pick a color scheme in GNOME 2, nudge a few sliders in Clearlooks, and the whole desktop came along with you. Somewhere along the way that got lost. Today you get an accent color, a light or dark switch, and if you want more, you're hunting for themes, hand-editing CSS, and living with the apps that never match.

Theme Roller brings it back. Pick three colors (an accent, a background and a text color), set how round, how tall and how shiny you like things, and click **Apply**. About a second later your whole desktop has changed with you: the panel and its menus, your apps, the window borders, the terminal, even your folder icons if you want them.

It makes themes called **xl-Cheeselooks**. Start from one of the ten that come with it, make it yours, and save it under your own name.

<!-- END OF DRAFT OPENING -->

> **Status:** getting ready for its first release. You can run it today from a copy of this repository (below); a `.deb` package is on the way.

## What you can change

- **Theme:** start from a built-in theme (xl-Cheeselooks, xl-Classic, xl-Gummy, xl-Vintage, xl-Organ Harvest, Claude, and dark versions) or one of your own. Save, duplicate, rename, and share themes as a single `.xltheme` file.
- **Global:** three colors make a complete light *or* dark theme. Size, roundness, gradient, and how hovers fade in and out. Or pick your accent from your wallpaper or any picture.
- **Style:** how things are drawn (edges, highlights, shadows, tabs), with a Depth slider. Ships with xl-Cheeselooks, xl-Classic, xl-Gummy, xl-Vintage and Claude styles, light and dark; you can write your own.
- **Panel & Menu:** the Cinnamon panel's and menus' own colors, height, roundness, gradient and see-through.
- **Window Borders:** title bar colors, height and gradient, border width and color, window roundness, and ten styles of window buttons with a choice of glyphs.
- **Terminal:** follows the theme, or its own colors.
- **Details:** tooltips, scrollbars, sliders, switches and the focus ring.
- **Icons:** folders in your colors, in six styles: two 80s school binders (xl-Big Baddy, with optional racing stripes, and xl-Rad), Claude's, Mint-Y, Yaru and Breeze. Off until you turn it on.
- **Integration:** brings your colors to the apps that don't read the theme on their own: GNOME-style apps, Flatpak apps, Qt apps like VLC, and text editors. **Scan my apps** shows which of your apps are which kind, and whether the theme reaches them.

Everything shows in a live preview first. Nothing changes on your desktop until you click **Apply**, and **Revert** puts your previous theme back.

## How far it goes

Linux Mint runs apps built with several different toolkits, and each looks for its colors in its own place. Theme Roller goes as far as a theme can without fighting the system:

- **GTK 3 apps** (most of Mint, Nemo, Xed, LibreOffice, Firefox…) and **the Cinnamon desktop**: fully themed.
- **GTK 4 and Mint's libadwaita apps**: fully themed.
- **Flatpak apps and GNOME-style apps** (libadwaita): your colors, with full styling as an option.
- **Qt apps** (VLC, KDE apps): your colors.
- **Text editors** (Xed, gedit, Meld): a matching color scheme.
- **Web-based apps** (Electron, Chrome apps) and apps that draw everything themselves: no theme reaches these.

## Trying it

On Linux Mint 22, from a copy of this repository:

```bash
git clone https://github.com/xlcheese/theme-roller.git
```

```bash
cd theme-roller
```

```bash
./bin/theme-roller
```

That opens Theme Roller. Pick a theme, change what you like, and click **Apply**.

To go back to Mint's own look, pick it again in **System Settings → Themes**. Theme Roller notices and takes its colors out of your other apps too.

## The command line

Everything the app does can also be done from a terminal. `theme-roller --help` lists it all; the main ones:

| Command | What it does |
|---|---|
| `theme-roller` | Opens the app |
| `theme-roller apply` | Builds the theme from your saved settings and applies it |
| `theme-roller apply --theme "xl-Classic"` | Applies a built-in or saved theme |
| `theme-roller revert` | Goes back to the theme you had before the last Apply |
| `theme-roller themes` | Lists the built-in themes and yours |
| `theme-roller export-theme` / `import-theme` | Shares a theme as one `.xltheme` file |
| `theme-roller scan --why` | Lists your apps by kind, and why for any it can't place |
| `theme-roller set-aside` | Takes Theme Roller's colors out of your apps for now |

From a copy of the repository, run them as `./bin/theme-roller …`.

## Where things go

Theme Roller only writes inside your home folder:

- the theme: `~/.themes/xl-Cheeselooks`
- folder icons, if you turn them on: `~/.icons/xl-Cheeselooks`
- your settings and your own themes: `~/.config/xl-cheeselooks/` and `~/.local/share/xl-cheeselooks/`
- for other apps: a marked block in `~/.config/gtk-4.0/gtk.css`, a Qt color scheme (qt5ct), a text editor scheme, and read access to your theme for Flatpak apps.

## Requirements

Linux Mint 22.x with Cinnamon 6.x. Everything uses the Python 3 and GTK that Mint already ships. For Qt apps to get your colors, install qt5ct (`sudo apt install qt5ct`).

## For developers

- Tests: `python3 -m unittest discover tests`
- Every computed value: `./bin/theme-roller tokens [filter]`
- Check a style file: `./bin/theme-roller check-style PATH`
- How it all works, and why: [the design spec](docs/design-spec.md)

## Credits

- Built on [Linux Mint](https://github.com/linuxmint/mint-themes)'s Mint-Y theme.
- Inspired by GNOME 2's Clearlooks theme and the GNOME Color Chooser.
- Folder icons from [Mint-Y](https://github.com/linuxmint/mint-y-icons) (CC BY-SA 4.0, Sam Hewitt and Alexey Varfolomeev), [Yaru](https://github.com/ubuntu/yaru) (CC BY-SA 4.0, Canonical and the Yaru contributors) and [Breeze](https://github.com/KDE/breeze-icons) (LGPL 3+, the KDE contributors). Each style's licence is in its folder under `data/icons/`.
- xl-Big Baddy and xl-Rad are xl_cheese's designs; the Claude folders and the Claude themes were designed by Claude.

## License

Theme Roller is [GPL-3.0](LICENSE). The folder icons keep their own licences (see Credits).
