"""Color."""

from __future__ import annotations

import typing as ty
import warnings

import numpy as np
from qtpy.QtGui import QColor

if ty.TYPE_CHECKING:
    from matplotlib.colors import Colormap as MplColormap


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


def is_dark_color(background: QColor) -> bool:
    """Check whether its a dark background."""
    a = 1 - (0.299 * background.redF() + 0.587 * background.greenF() + 0.114 * background.blueF())
    return background.alphaF() > 0 and a >= 0.45


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


def rgb_to_hex(colors, multiplier: int = 255) -> str:
    """Convert list/tuple of colors to hex."""
    return f"#{int(colors[0] * multiplier):02x}{int(colors[1] * multiplier):02x}{int(colors[2] * multiplier):02x}"


def hex_to_rgb(hex_str, decimals=3, alpha: ty.Optional[float] = None):
    """Convert hex color to numpy array."""
    hex_color = hex_str.lstrip("#")
    hex_len = len(hex_color)
    rgb = [int(hex_color[i : i + int(hex_len / 3)], 16) for i in range(0, int(hex_len), int(hex_len / 3))]
    if alpha is not None:
        if alpha == 1:
            warnings.warn(
                "The provided alpha value is equal to 1 - this function accepts values in 0-255 range.", stacklevel=2
            )
        rgb.append(alpha)
    return np.round(np.asarray(rgb) / 255, decimals)


def colormap_to_hex(colormap: MplColormap) -> ty.List[str]:
    """Convert mpl colormap to hex."""
    return [rgb_to_hex(colormap(i)) for i in range(colormap.N)]


def get_colors_from_colormap(colormap: str, n_colors: int, is_reversed: bool = False) -> ty.List[str]:
    """Get list of colors from colormap."""
    import matplotlib.cm

    if is_reversed and not colormap.endswith("_r"):
        colormap += "_r"

    return colormap_to_hex(matplotlib.cm.get_cmap(colormap, n_colors))
