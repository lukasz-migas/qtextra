"""Cross-hair."""
from enum import Enum
from typing import Tuple

from napari.components.overlays import SceneOverlay
from napari.utils.colormaps.standardize_color import transform_color
from napari.utils.events.custom_types import Array
from pydantic import validator


class Shape(str, Enum):
    """Shape of the cross hair."""

    CROSSHAIR = "crosshair"
    BOX = "box"


class CrossHairOverlay(SceneOverlay):
    """Crosshair object."""

    width: int = 1
    color: Array[float, (4,)] = (1.0, 0.0, 0.0, 1.0)
    position: Tuple[float, float] = (0, 0)
    window: int = 1
    shape: Shape = Shape.BOX
    auto_hide: bool = True

    @validator("color", pre=True)
    def _coerce_color(cls, v):
        return transform_color(v)[0]
