"""Grid lines visual."""
from napari._vispy.overlays.base import ViewerOverlayMixin, VispyCanvasOverlay

from qtextra._napari.common._vispy.overlays.color_bar import ColorBar as ColorBarNode

HORIZONTAL_SIZE = (30, 200)


class VispyColorbarOverlay(ViewerOverlayMixin, VispyCanvasOverlay):
    """Colorbar visual."""

    def __init__(self, viewer, overlay, parent=None):
        super().__init__(
            node=ColorBarNode(
                cmap="viridis",
                size=HORIZONTAL_SIZE,
                pos=(0, 0),
                parent=parent,
            ),
            viewer=viewer,
            overlay=overlay,
            parent=parent,
        )
        # model events
        self.viewer.color_bar.events.visible.connect(self._on_visible_change)
        self.viewer.color_bar.events.border_width.connect(self._on_border_change)
        self.viewer.color_bar.events.border_color.connect(self._on_border_change)
        self.viewer.color_bar.events.label_color.connect(self._on_tick_change)
        self.viewer.color_bar.events.label_size.connect(self._on_tick_change)
        self.viewer.color_bar.events.position.connect(self._on_position_change)
        self.viewer.color_bar.events.colormap.connect(self._on_data_change)
        self.viewer.color_bar.events.data.connect(self._on_cbar_data_change)

        # visual events
        self.node.events.update_position.connect(self._on_position_change)

        self._on_visible_change()
        self._on_border_change(None)
        self._on_data_change(None)
        self._on_tick_change(None)
        self._on_position_change(None)

    def on_set_visible(self, _evt=None):
        """Toggle state."""
        self.viewer.color_bar.visible = not self.viewer.color_bar.visible

    def _on_border_change(self, _evt=None):
        """Change colorbar border data."""
        self.node.border_width = self.viewer.color_bar.border_width
        self.node.border_color = self.viewer.color_bar.border_color
        self.node.refresh()

    def _on_tick_change(self, _evt=None):
        """Change tick data."""
        self.node.label_size = self.viewer.color_bar.label_size
        self.node.label_color = self.viewer.color_bar.label_color
        self.node.refresh()
        self._on_position_change(None)

    def _on_data_change(self, _evt=None):
        """Change colorbar data."""
        self.node.cmap = self.viewer.color_bar.colormap

    def _on_cbar_data_change(self, _evt=None):
        """Change colorbar data."""
        self.node.colorbar_data = self.viewer.color_bar.data
        self.node.refresh()
        self._on_position_change(None)

    # def _on_position_change(self, _evt=None):
    #     """Change colorbar position."""
    #     try:
    #         w, h = self.node.size
    #     except AttributeError:
    #         return
    #     canvas_size = list(self.node.canvas.size)
    #
    #     if self.viewer.color_bar.position == CanvasPosition.BOTTOM_LEFT:
    #         transform = [5, canvas_size[1] - h, 0, 0]
    #     elif self.viewer.color_bar.position == CanvasPosition.BOTTOM_RIGHT:
    #         transform = [canvas_size[0] - w, canvas_size[1] - h, 0, 0]
    #     elif self.viewer.color_bar.position == CanvasPosition.TOP_LEFT:
    #         transform = [5, 5, 0, 0]
    #     elif self.viewer.color_bar.position == CanvasPosition.TOP_RIGHT:
    #         transform = [canvas_size[0] - w, 5, 0, 0]
    #     else:
    #         raise ValueError("Incorrect color bar position selected")
    #
    #     self.node.transform.translate = transform
