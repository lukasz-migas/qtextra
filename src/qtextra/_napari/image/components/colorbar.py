"""Colorbar."""
from typing import Optional, Tuple

import numpy as np
from napari.utils.colormaps.standardize_color import transform_color
from napari.utils.events import EventedModel
from napari.utils.events.custom_types import Array
from pydantic import validator

from qtextra._napari.common.components._viewer_constants import Position

ColorBarItem = Tuple[np.ndarray, str, Tuple[float, float]]


class ColorBar(EventedModel):
    """Colorbar object."""

    # fields
    visible: bool = False
    border_width: int = 1
    border_color: Array[float, (4,)] = (1.0, 1.0, 1.0, 1.0)
    label_color: Array[float, (4,)] = (1.0, 1.0, 1.0, 1.0)
    label_size: int = 7
    colormap: str = "viridis"
    position: Position = Position.BOTTOM_LEFT
    data: Optional[Tuple[ColorBarItem, ...]] = None

    @validator("border_color", "label_color", pre=True)
    def _coerce_color(cls, v):
        return transform_color(v)[0]
