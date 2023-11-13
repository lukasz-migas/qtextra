"""Colorbar."""
from typing import Optional, Tuple

import numpy as np
from napari.components.overlays import CanvasOverlay
from napari.utils.colormaps.standardize_color import transform_color
from napari.utils.events.custom_types import Array
from pydantic import validator

ColorBarItem = Tuple[np.ndarray, str, Tuple[float, float]]


class ColorBarOverlay(CanvasOverlay):
    """Colorbar object."""

    # fields
    border_width: int = 1
    border_color: Array[float, (4,)] = (1.0, 1.0, 1.0, 1.0)
    label_color: Array[float, (4,)] = (1.0, 1.0, 1.0, 1.0)
    label_size: int = 7
    colormap: str = "viridis"
    data: Optional[Tuple[ColorBarItem, ...]] = None

    @validator("border_color", "label_color", pre=True)
    def _coerce_color(cls, v):
        return transform_color(v)[0]
