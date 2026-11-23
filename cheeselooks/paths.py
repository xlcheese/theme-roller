"""Where things live, on disk and in the repository."""

from __future__ import annotations

import os
from pathlib import Path

from .tokens import THEME_NAME

HOME = Path.home()
# the app's own folders (settings, your themes and styles, cache): Theme Roller's
# (22 Nov; xl-cheeselooks before). What's named for the theme keeps its name:
# ~/.themes/xl-Cheeselooks, ~/.icons/xl-Cheeselooks.
APP_DIR = "theme-roller"


def _xdg(var: str, default: Path) -> Path:
    value = os.environ.get(var)
    return Path(value) if value else default


def data_dir() -> Path:
    """Templates, built-in styles and presets.

    CHEESELOOKS_DATA wins; otherwise the repository checkout this package
    runs from; otherwise the system install location.
    """
    env = os.environ.get("CHEESELOOKS_DATA")
    if env:
        return Path(env)
    repo = Path(__file__).resolve().parents[1]
    if (repo / "templates").is_dir():
        return repo
    return Path("/usr/share") / APP_DIR


def templates_dir() -> Path:
    return data_dir() / "templates"


def config_dir() -> Path:
    return _xdg("XDG_CONFIG_HOME", HOME / ".config") / APP_DIR


def gtk4_css() -> Path:
    """GTK 4's per-user stylesheet, where the libadwaita colours go."""
    return _xdg("XDG_CONFIG_HOME", HOME / ".config") / "gtk-4.0" / "gtk.css"


def settings_file() -> Path:
    return config_dir() / "settings.json"


def user_presets_dir() -> Path:
    return config_dir() / "presets"


def builtin_presets_dir() -> Path:
    return data_dir() / "presets"


def style_dirs() -> list[Path]:
    """User styles first, so a user style can replace a built-in one."""
    return [_xdg("XDG_DATA_HOME", HOME / ".local" / "share") / APP_DIR / "styles",
            data_dir() / "styles"]


def theme_dir() -> Path:
    return HOME / ".themes" / THEME_NAME


def cache_dir() -> Path:
    return _xdg("XDG_CACHE_HOME", HOME / ".cache") / APP_DIR


def last_good_dir() -> Path:
    return cache_dir() / "last-good"
