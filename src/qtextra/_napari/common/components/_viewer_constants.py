"""Constants."""
from collections import OrderedDict

from napari.components._viewer_constants import Position, TextOverlayPosition

POSITION_TRANSLATIONS = OrderedDict(
    [
        (Position.TOP_LEFT, "Top left"),
        (Position.TOP_RIGHT, "Top right"),
        (Position.BOTTOM_RIGHT, "Bottom right"),
        (Position.BOTTOM_LEFT, "Bottom left"),
    ]
)


TEXT_POSITION_TRANSLATIONS = OrderedDict(
    [
        (TextOverlayPosition.TOP_LEFT, "Top left"),
        (TextOverlayPosition.TOP_CENTER, "Top center"),
        (TextOverlayPosition.TOP_RIGHT, "Top right"),
        (TextOverlayPosition.BOTTOM_RIGHT, "Bottom right"),
        (TextOverlayPosition.BOTTOM_CENTER, "Bottom center"),
        (TextOverlayPosition.BOTTOM_LEFT, "Bottom left"),
    ]
)
