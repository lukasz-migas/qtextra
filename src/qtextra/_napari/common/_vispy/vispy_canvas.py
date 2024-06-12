"""Vispy canvas."""
from napari._vispy.utils.gl import get_max_texture_sizes
from qtpy.QtCore import QSize
from vispy.scene import SceneCanvas, Widget
from vispy.util.event import Event


class VispyCanvas(SceneCanvas):
    """SceneCanvas for our QtViewer class.

    Get the max texture size in __init__().

    Attributes
    ----------
    max_texture_sizes : Tuple[int, int]
        The max textures sizes as a (2d, 3d) tuple.
    """

    def __init__(self, *args, **kwargs):
        # Since the base class is frozen we must create this attribute
        # before calling super().__init__().
        self.max_texture_sizes = None
        self._last_theme_color = None
        self._background_color_override = None
        super().__init__(*args, **kwargs)

        # Call get_max_texture_sizes() here so that we query OpenGL right now while we know a Canvas exists.
        # Later calls to get_max_texture_sizes() will return the same results because it's using an lru_cache.
        self.max_texture_sizes = get_max_texture_sizes()

        # enable hover events
        self._send_hover_events = True  # temporary workaround

        self.events.ignore_callback_errors = False
        self.native.setMinimumSize(QSize(100, 100))
        self.context.set_depth_func("lequal")

        # connect events
        self.events.mouse_double_click.connect(self._on_mouse_double_click)

        self.events.add(reset_view=Event)

    @property
    def destroyed(self):
        return self._backend.destroyed

    def _on_mouse_double_click(self, event):
        """Process mouse double click event."""
        if event.button == 1 and "Control" not in event.modifiers:
            self.events.reset_view()

    @property
    def background_color_override(self):
        """Get background color."""
        return self._background_color_override

    @background_color_override.setter
    def background_color_override(self, value):
        self._background_color_override = value
        self.bgcolor = value or self._last_theme_color

    def _on_theme_change(self, event):
        from qtextra.config.theme import THEMES

        # store last requested theme color, in case we need to reuse it
        # when clearing the background_color_override, without needing to
        # keep track of the viewer.
        self._last_theme_color = THEMES.get_theme(event.value)["canvas"]
        self.bgcolor = self._last_theme_color

    @property
    def bgcolor(self):
        """Get background color."""
        SceneCanvas.bgcolor.fget(self)

    @bgcolor.setter
    def bgcolor(self, value):
        _value = self._background_color_override or value
        SceneCanvas.bgcolor.fset(self, _value)

    @property
    def central_widget(self):
        """Overrides SceneCanvas.central_widget to make border_width=0."""
        if self._central_widget is None:
            self._central_widget = Widget(size=self.size, parent=self.scene, border_width=0)
        return self._central_widget

    def _process_mouse_event(self, event):
        """Ignore mouse wheel events which have modifiers."""
        if event.type == "mouse_wheel" and len(event.modifiers) > 0:
            return
        if event.handled:
            return
        super()._process_mouse_event(event)


if __name__ == "__main__":  # pragma: no cover
    import sys

    from qtpy.QtWidgets import QDialog, QVBoxLayout

    from qtextra.utils.dev import qapplication

    _ = qapplication()  # analysis:ignore

    dlg = QDialog()
    canvas = VispyCanvas()
    view = canvas.central_widget.add_view()

    layout = QVBoxLayout()
    layout.addWidget(canvas.native)
    dlg.setLayout(layout)

    dlg.show()
    canvas.show()
    sys.exit(dlg.exec_())
