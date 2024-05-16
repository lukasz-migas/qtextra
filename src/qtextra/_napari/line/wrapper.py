"""Line viewer."""

from __future__ import annotations

import typing as ty

import numpy as np
from koyo.secret import get_short_hash
from napari.utils.events import Event
from napari_plot.layers import Centroids, InfLine, Line, Region, Scatter, Shapes
from napari_plot.viewer import ViewerModel as Viewer
from qtpy.QtCore import QMutex
from qtpy.QtWidgets import QWidget

from qtextra._napari.common.wrapper import ViewerBase
from qtextra._napari.line._vispy.overrides.axis import tick_formatter
from qtextra._napari.line.qt_viewer import QtViewer
from qtextra.config.theme import CANVAS

MUTEX = QMutex()

LINE_NAME, CENTROID_NAME, SCATTER_NAME, REGION_NAME = "Line", "Centroids", "Scatter", "Region"
EXTRACT_NAME = "Extract mask"


def get_font_for_os() -> str:
    """Get font that supports unicode characters."""
    from vispy.util.fonts import list_fonts

    from qtextra.utils.utilities import IS_LINUX, IS_MAC, IS_WIN

    fonts = list_fonts()
    if IS_WIN:
        font = "Segoe UI"
        alt_font = "Calibri"
    elif IS_MAC:
        font = alt_font = "Helvetica"
    elif IS_LINUX:
        font = "DejaVu Sans"
        alt_font = "Liberation Sans"
    if font not in fonts:
        font = alt_font
    if font not in fonts:
        font = "OpenSans"
    return font


class NapariLineView(ViewerBase):
    """Napari-based image viewer."""

    # define plot type
    PLOT_TYPE = "line"

    _instances: ty.ClassVar[list] = []

    def __init__(
        self,
        parent: QWidget | None = None,
        x_label: str = "",
        y_label: str = "",
        lock_to_bottom: bool = False,
        **kwargs: ty.Any,
    ):
        self.parent = parent
        self.main_parent = kwargs.pop("main_parent", None)
        self.PLOT_ID = get_short_hash()

        # create instance of viewer
        self.viewer: Viewer = Viewer()
        self.viewer.axis.y_tick_formatter = tick_formatter
        self.viewer.drag_tool.active = "box"
        self.viewer.camera.extent_mode = "restricted"
        self.viewer.axis.x_label = x_label
        self.viewer.axis.y_label = y_label
        self.viewer.axis.label_size = 8
        self.viewer.axis.tick_size = 6
        if lock_to_bottom:
            self.viewer.camera.axis_mode = "lock_to_bottom"
        else:
            self.viewer.camera.axis_mode = "all"

        # create instance of qt widget
        self.widget = QtViewer(
            self,
            self.viewer,
            parent=parent,
            disable_controls=kwargs.pop("disable_controls", False),
            add_toolbars=kwargs.pop("add_toolbars", True),
            allow_extraction=kwargs.pop("allow_extraction", True),
            allow_tools=kwargs.pop("allow_tools", False),
            connect_theme=kwargs.pop("connect_theme", True),
        )
        font = get_font_for_os()
        self.widget.x_axis.node.axis._text.face = font
        self.widget.x_axis.node.axis._axis_label_vis.face = font
        self.widget.y_axis.node.axis._text.face = font
        self.widget.y_axis.node.axis._axis_label_vis.face = font
        self.widget.text_overlay.node.face = font

        # add few layers
        self.line_layer: Line | None = None
        self.region_layer: Region | None = None

        # connect events
        self.viewer.events.clear_canvas.connect(self._clear)
        self.viewer.layers.events.removed.connect(self._on_remove_layer)
        self.viewer.text_overlay.position = "top_right"

        # own instances
        self._instances.append(self)

    def _update_view(self) -> None:
        self.widget.canvas.native.update()
        xmin, xmax, ymin, ymax = self.viewer.camera.rect
        self.viewer.camera.rect = xmin + 1, xmax, ymin, ymax
        self.viewer.camera.rect = xmin, xmax, ymin, ymax

    def _on_remove_layer(self, evt: Event) -> None:
        """Indicate if layer has been deleted."""
        layer = evt.value
        if self.line_layer is not None and layer.name == self.line_layer.name:
            self.line_layer = None
        if self.region_layer is not None and layer.name == self.region_layer.name:
            self.region_layer = None

    def _clear(self, _evt: ty.Any = None) -> None:
        """Clear canvas."""
        self.line_layer, self.region_layer = None, None

    def plot(
        self,
        x: ty.Iterable | np.ndarray,
        y: ty.Iterable | np.ndarray,
        name: str = LINE_NAME,
        reset_y: bool = False,
        reset_x: bool = False,
        **kwargs: ty.Any,
    ) -> Line:
        """Update data."""
        layer = self.try_reuse(name, Line)
        color = kwargs.pop("color", CANVAS.as_array("line"))
        if layer:
            layer.update_attributes(False, data=np.c_[x, y], color=color, **kwargs)
        else:
            layer = self.viewer.add_line(np.c_[x, y], name=name, color=color, **kwargs)
        if reset_y:
            self.viewer.reset_y_view()
        if reset_x:
            self.viewer.reset_x_view()
        return layer

    def add_histogram(
        self,
        array: np.ndarray,
        bins: int = 10,
        rel_width: float = 0.8,
        name: str = "Histogram",
        orientation: str = "vertical",
        face_color: str = "red",
        **kwargs: ty.Any,
    ) -> Shapes:
        """Add histogram using Shapes layer."""
        from qtextra._napari.line.plotting import convert_hist_to_shapes

        shapes = convert_hist_to_shapes(array, bins, orientation, rel_width)
        layer = self.try_reuse(name, Shapes)
        if layer:
            self.remove_layer(layer)
        layer = self.viewer.add_shapes(shapes, edge_width=0, name=name, face_color=face_color, **kwargs)
        return layer

    def add_scatter(
        self,
        x: ty.Iterable | np.ndarray | None = None,
        y: ty.Iterable | np.ndarray | None = None,
        name: str = SCATTER_NAME,
        xy: np.ndarray | None = None,
        **kwargs: ty.Any,
    ) -> Scatter:
        """Add scatter points."""
        layer = self.try_reuse(name, Scatter)
        color = kwargs.pop("color", CANVAS.as_array("scatter"))
        if xy is None:
            if x is not None and y is not None:
                xy = np.c_[y, x]
        if layer:
            try:
                layer.update_attributes(False, data=xy, color=color, **kwargs)
                layer.visible = kwargs.get("visible", True)
            except Exception:
                self.remove_layer(layer)
                layer = None
        if layer is None:
            layer = self.viewer.add_scatter(
                xy,
                name=name,
                # color=color,
                **kwargs,
            )
        return layer

    def add_inf_line(
        self,
        position: float,
        orientation: str = "vertical",
        color: tuple | str = (1.0, 0.0, 0.0, 1.0),
        name: str = "InfLine",
        **kwargs: ty.Any,
    ) -> InfLine:
        """Add inf line."""
        layer = self.try_reuse(name, InfLine)
        if layer:
            layer.update_attributes(False, data=[position], color=color, **kwargs)
        else:
            layer = self.viewer.add_inf_line([position], name=name, color=color, orientation=orientation)
        return layer

    def add_centroids(self, x: np.ndarray, y: np.ndarray, name: str = CENTROID_NAME, **kwargs: ty.Any) -> Centroids:
        """Add centroids."""
        layer = self.try_reuse(name, Centroids)
        color = kwargs.pop("color", CANVAS.as_array("line"))
        if layer:
            layer.data = np.c_[x, y]
            layer.visible = kwargs.get("visible", True)
        else:
            layer = self.viewer.add_centroids(np.c_[x, y], name=name, color=color, **kwargs)
        return layer

    def add_inf_centroids(self, x: np.ndarray, name: str = CENTROID_NAME, **kwargs: ty.Any) -> InfLine:
        """Add centroids."""
        layer = self.try_reuse(name, InfLine)
        color = kwargs.pop("color", CANVAS.as_array("line"))
        if layer:
            layer.data = x
            layer.visible = kwargs.get("visible", True)
        else:
            layer = self.viewer.add_inf_line(x, orientation="vertical", name=name, color=color, **kwargs)
        return layer

    def add_region(
        self, window: tuple[float, float], name: str = REGION_NAME, editable: bool = True, **kwargs: ty.Any
    ) -> Region | None:
        """Add region of interest."""
        # get currently selected layers
        try:
            layer = self.try_reuse(name, Region)
            color = kwargs.pop("color", CANVAS.as_array("highlight"))
            if layer:
                layer.update_attributes(False, data=(window, "vertical"), color=color, **kwargs)
            else:
                layer = self.viewer.add_region((window, "vertical"), name=name, color=color, **kwargs)
            # set editable flag
            layer.editable = editable
            return layer
        except TypeError:
            return None

    def add_regions(
        self, window: tuple[float | int, float | int], name: str = REGION_NAME, editable: bool = True, **kwargs: ty.Any
    ) -> Region:
        """Add region of interest."""
        # get currently selected layers
        layer = self.try_reuse(name, Region)
        color = kwargs.pop("color", CANVAS.as_array("highlight"))
        if layer:
            layer.update_attributes(False, data=window, **kwargs)
        else:
            layer = self.viewer.add_region(window, orientation="vertical", name=name, color=color, **kwargs)
        # set editable flag
        layer.editable = editable
        return layer

    def add_extract_region_layer(self) -> Region | None:
        """Add region of interest layer."""
        if self.region_layer is None:
            self.region_layer = self.viewer.add_region(
                ((0, 0.1), "vertical"), name=EXTRACT_NAME, color=CANVAS.as_array("scatter"), opacity=0.5
            )
        self.select_one_layer(self.region_layer)
        return self.region_layer

    def remove_region_layers(self) -> None:
        """Remove all region layers from the plot."""
        layers = self.get_layers_of_type(Region)
        self.remove_layers(layers)

    def set_line_x(self, x: np.ndarray) -> None:
        """Update x-axis data of all line layers where the dimension of `x` matches that of the currently
        present data
        .
        """
        layers = self.get_layers_of_type(Line)
        for layer in layers:
            data = layer.data
            if data.shape[0] == len(x):
                data[:, 0] = x
                layer.data = data


if __name__ == "__main__":  # pragma: no cover

    def _main():  # type: ignore[no-untyped-def]
        import sys

        from qtextra.config.theme import THEMES
        from qtextra.helpers import make_btn
        from qtextra.utils.dev import qframe

        def _on_btn() -> None:
            n_bins = np.random.randint(5, 100, 1)[0]
            rel_width = np.random.rand(1)
            viewer.add_histogram(a, n_bins, rel_width=rel_width)

        app, frame, ha = qframe()
        frame.setMinimumSize(600, 600)
        viewer = NapariLineView(frame)
        THEMES.set_theme_stylesheet(viewer.widget)

        # rng = np.random.RandomState(10)  # deterministic random data
        # a = np.hstack((rng.normal(size=1000), rng.normal(loc=5, scale=2, size=1000)))
        a = np.arange(10)
        viewer.add_histogram(a, 9)

        # viewer.plot(np.arange(100), np.random.random(100))
        # viewer.add_extract_region_layer()

        # viewer.add_centroids(np.arange(100), np.random.randint(0, 1000, 100))

        btn = make_btn(frame, "Click me")
        btn.clicked.connect(_on_btn)

        ha.addWidget(viewer.widget, stretch=True)
        ha.addWidget(btn)
        frame.show()

        sys.exit(app.exec_())

    _main()  # type: ignore[no-untyped-call]
