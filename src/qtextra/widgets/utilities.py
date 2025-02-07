"""Utility widgets for the application."""

from __future__ import annotations

from qtpy.QtGui import QColor


def get_text_color(background: QColor, light_color: QColor | None = None, dark_color: QColor | None = None) -> QColor:
    """Select color depending on whether the background is light or dark.

    Parameters
    ----------
    background : QColor
        background color
    light_color : QColor
        the color used on light background
    dark_color : QColor
        the color used on dark background
    """
    if light_color is None:
        light_color = QColor("#000000")
    if dark_color is None:
        dark_color = QColor("#FFFFFF")
    is_dark = is_dark_color(background)
    return dark_color if is_dark else light_color


def is_dark_color(background: QColor) -> bool:
    """Check whether its a dark background."""
    a = 1 - (0.299 * background.redF() + 0.587 * background.greenF() + 0.114 * background.blueF())
    return background.alphaF() > 0 and a >= 0.3
