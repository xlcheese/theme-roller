# Changelog

## Next

- **The theme is called Theme-Roller** in Mint's Themes settings (Applications, Desktop and Icons), not xl-Cheeselooks, so it says which tool to open to change it. Its folders are `~/.themes/Theme-Roller` and `~/.icons/Theme-Roller`. If you used 0.9.0, your next **Apply** moves everything over by itself and removes the old folders; **Revert** still goes back to what you had. The built-in themes and styles keep their xl- names.
- **More things answer the pointer** in every theme: text fields' borders darken a step on hover, a checked checkbox or radio button lightens like a button does, and switches lighten on and off.
- **Style sheets can outline hovers and selections**, as KDE's Breeze does:
  - `menu_item` `hover_edge`: a line around the hovered item in apps' menus and in Cinnamon's right-click, applet and panel launcher menus;
  - `sidebar_row` (new): `hover_color`, `selected_color`, `hover_edge` and `selected_border` for Nemo's sidebar, file dialogs and settings-style page lists;
  - `[panel]` `menu_hover_edge` and `menu_category_edge` for the Cinnamon main menu, and `menu_see_through = true` to let the desktop show through its hovers as it does through the menu.

  The lines are drawn inside the item, so nothing shifts. The starter style sheet has examples.
- **Qt apps' color scheme is called Theme-Roller** too (qt5ct lists it). The next Apply replaces 0.9.0's xl-Cheeselooks scheme and its lines in `~/.profile`.

## 0.9.0: the first release

Good ol' fashioned Linux desktop theming for your Linux Mint Cinnamon desktop.

This is Theme Roller's first public release. It's numbered 0.9 rather than 1.0 on purpose: it's been tested on real Mint desktops, but it hasn't met many of them yet. If something looks wrong on yours, please [open an issue](https://github.com/xlcheese/theme-roller/issues) with a screenshot.

### What it does

Choose three colors, turn some knobs and dials, and click **Apply**. Theme Roller builds a complete theme for your whole desktop and switches to it within a second:

- **Every kind of app:** GTK 3 and GTK 4 apps, libadwaita apps, the Cinnamon panel and menus, and the window borders.
- **A live preview.** Nothing changes on your desktop until you click Apply, and **Revert** puts your previous theme back, including Mint's own.
- **Styles** that decide how everything is drawn: edges, highlights, shadows, tabs, buttons. Make your own from a starter style sheet in which every option is explained.
- **Panel & Menu, Window Borders, Terminal, Details:** fine-tune any part separately, or leave it to follow your colors. Window Borders includes ten window-button styles, with four sets of minimize, maximize and close symbols or your icon theme's own.
- **Folder icons in your colors**, in six styles, from Mint-Y, Yaru and Breeze to two 80s school binders. Only the folders change; your icon theme stays.
- **Colors from a picture:** take your accent from your wallpaper or any image.
- **Your colors in apps that don't read the theme on their own:** GNOME-style apps, Flatpak apps, Qt apps like VLC, and text editors. **Scan my apps** shows which of your apps are which kind, and whether the theme reaches them.
- **Share themes** as a single `.xltheme` file.

### Built-in themes

xl-Cheeselooks, xl-Classic, xl-Gummy and Claude, each in light and dark, plus xl-Pigeon. Two more are waiting at the bottom of the list for anyone who scrolls that far.

### Languages

English, Spanish, German, French, Brazilian Portuguese, Italian, Russian and Dutch, following the language set in Mint. The translations are new; if you're a native speaker and something reads oddly, corrections are very welcome ([how to help](po/README.md)).

### Installing

Download `theme-roller_0.9.0_all.deb` below, double-click it, and open **Theme Roller** from the menu under Preferences. Or from a terminal:

```bash
sudo apt install ./theme-roller_0.9.0_all.deb
```

Requires Linux Mint 22 with Cinnamon. For Qt apps to get your colors, also install qt5ct (the package recommends it).

### Uninstalling

First click **About → Remove from my desktop…** in Theme Roller: Mint's default theme comes back and Theme Roller's colors leave your apps. Then uninstall it from the Software Manager, or with `sudo apt remove theme-roller`. Your settings and saved themes stay in your home folder in case you come back.

### Good to know

- **Window border changes restart Cinnamon** by themselves when you click Apply. Your windows stay open; the screen flickers once. Cinnamon only reloads window borders that way.
- **Qt apps:** the first time Theme Roller colors them, log out and back in. After that, reopening an app is enough.
- **Web-based apps** (Electron and Chrome apps) draw their own look, and no theme reaches them.
- **Built for Linux Mint 22 with Cinnamon.** Cinnamon on other Linux distributions may work, but hasn't been tested yet.

### Thanks

To everyone who remembers when theming Linux was half the fun. Developed with the help of Claude, an AI assistant by Anthropic.
