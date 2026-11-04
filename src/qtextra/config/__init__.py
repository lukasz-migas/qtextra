"""Init."""

from qtextra.config.events import EVENTS
from qtextra.config.theme import THEMES, QtStyler, Themes, get_system_theme, is_dark, is_system_dark


def get_settings():
    """Get settings."""


__all__ = ["EVENTS", "THEMES", "QtStyler", "Themes", "get_settings", "get_system_theme", "is_dark", "is_system_dark"]
