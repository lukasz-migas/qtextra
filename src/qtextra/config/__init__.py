"""Init."""

from qtextra.config.theme import THEMES, CANVAS, CanvasThemes, Themes, is_dark  # noqa
from qtextra.config.events import EVENTS


def get_settings():
    """Get settings."""
    pass


__all__ = ["CanvasThemes", "Themes", "CANVAS", "THEMES", "EVENTS", "get_settings", "is_dark"]
