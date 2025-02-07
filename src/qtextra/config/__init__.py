"""Init."""

from qtextra.config.theme import THEMES, CANVAS, CanvasThemes, Themes, is_dark  # noqa
from qtextra.config.events import EVENTS


def get_settings():
    """Get settings."""
    pass


__all__ = ["CANVAS", "EVENTS", "THEMES", "CanvasThemes", "Themes", "get_settings", "is_dark"]
