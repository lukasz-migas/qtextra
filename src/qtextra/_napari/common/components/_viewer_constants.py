"""Constants."""
from collections import OrderedDict

from napari.components._viewer_constants import CanvasPosition

POSITION_TRANSLATIONS = OrderedDict(
    [
        (CanvasPosition.TOP_LEFT, "Top left"),
        (CanvasPosition.TOP_RIGHT, "Top right"),
        (CanvasPosition.BOTTOM_RIGHT, "Bottom right"),
        (CanvasPosition.BOTTOM_LEFT, "Bottom left"),
    ]
)


TEXT_POSITION_TRANSLATIONS = OrderedDict(
    [
        (CanvasPosition.TOP_LEFT, "Top left"),
        (CanvasPosition.TOP_CENTER, "Top center"),
        (CanvasPosition.TOP_RIGHT, "Top right"),
        (CanvasPosition.BOTTOM_RIGHT, "Bottom right"),
        (CanvasPosition.BOTTOM_CENTER, "Bottom center"),
        (CanvasPosition.BOTTOM_LEFT, "Bottom left"),
    ]
)
