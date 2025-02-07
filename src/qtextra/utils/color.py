"""Color."""

from __future__ import annotations

import numpy as np
from koyo.color import hex_to_rgb, rgb_to_hex
from qtpy.QtGui import QColor


def get_text_color(
    background: QColor | str, light_color: QColor | None = None, dark_color: QColor | None = None
) -> QColor:
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
    if not isinstance(background, QColor):
        background = QColor(background)
    is_dark = is_dark_color(background)
    return dark_color if is_dark else light_color


def qt_rgb_to_hex(color: str) -> str:
    """Qt color to hex."""
    assert color.startswith("rgb("), "Incorrect color provided"
    colors = np.asarray(list(map(int, color.split("rgb(")[1].split(")")[0].split(",")))) / 255
    return rgb_to_hex(colors)


def hex_to_qt_rgb(color: str) -> str:
    """Convert hex to Qt color."""
    rgb = np.round(hex_to_rgb(color) * 255, 0).astype(np.int32)
    return f"rgb({rgb[0]}, {rgb[1]}, {rgb[2]})"


def rgb_to_qt_rgb(color: np.ndarray) -> str:
    """Convert numpy array to Qt color."""
    color = (255 * color).astype("int")
    return f"rgb({color[0]}, {color[1]}, {color[2]})"


def is_dark_color(background: QColor) -> bool:
    """Check whether its a dark background."""
    a = 1 - (0.299 * background.redF() + 0.587 * background.greenF() + 0.114 * background.blueF())
    return background.alphaF() > 0 and a >= 0.45
