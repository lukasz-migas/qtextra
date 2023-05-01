"""Modified canvas."""
from napari_plot._vispy.canvas import VispyCanvas as _VispyCanvas


class VispyCanvas(_VispyCanvas):
    def _on_mouse_double_click(self, event):
        """Process mouse double click event."""
        if event.modifiers:
            return
        super()._on_mouse_double_click(event)
