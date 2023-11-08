"""Cross-hair visual."""
from __future__ import annotations

import numpy as np
from napari._vispy.overlays.base import ViewerOverlayMixin, VispySceneOverlay
from vispy.scene.visuals import Line

from qtextra._napari.common.components.overlays.crosshair import Shape

MAX = np.finfo(np.float16).max


def position_to_cross(position: tuple[float, float], size: float = 3.0) -> np.ndarray:
    """Convert position specified by the user to crosshair."""
    size = size / 2
    y, x = np.round(position)
    data = [[x - size, y, 0], [x + size, y, 0], [x, y - size, 0], [x, y + size, 0], [x, y, -size], [x, y, size]]
    return np.asarray(data)


def position_to_box(position: tuple[float, float], size: float = 1.0) -> np.ndarray:
    """Convert position specified by the user to box."""
    size = size / 2
    y, x = np.round(position)
    data = [
        [x - size, y - size, 0],
        [x + size, y - size, 0],
        [x + size, y - size, 0],
        [x + size, y + size, 0],
        [x + size, y + size, 0],
        [x - size, y + size, 0],
        [x - size, y + size, 0],
        [x - size, y - size, 0],
        # from here onwards this is cross
        [x - MAX, y, 0],
        [x + MAX, y, 0],
        [x, y - MAX, 0],
        [x, y + MAX, 0],
    ]
    return np.asarray(data)


class VispyCrosshairVisual(ViewerOverlayMixin, VispySceneOverlay):
    """Cross-hair."""

    def __init__(self, viewer, overlay, parent=None):
        super().__init__(
            node=Line(connect="segments", method="gl", parent=parent, width=3),
            viewer=viewer,
            overlay=overlay,
            parent=parent,
        )

        self.viewer.cross_hair.events.visible.connect(self._on_visible_change)
        self.viewer.cross_hair.events.width.connect(self._on_data_change)
        self.viewer.cross_hair.events.color.connect(self._on_data_change)
        self.viewer.cross_hair.events.position.connect(self._on_data_change)
        self.viewer.cross_hair.events.shape.connect(self._on_data_change)
        self.viewer.cross_hair.events.window.connect(self._on_data_change)

        self._on_visible_change()
        self._on_data_change(None)

    def _on_data_change(self, _evt=None):
        """Change position."""
        if self.viewer.cross_hair.shape == Shape.BOX:
            data = position_to_box(self.viewer.cross_hair.position, self.viewer.cross_hair.window)
        else:
            data = position_to_cross(self.viewer.cross_hair.position, self.viewer.cross_hair.window)
        self.node.set_data(data, color=self.viewer.cross_hair.color, width=self.viewer.cross_hair.width)
