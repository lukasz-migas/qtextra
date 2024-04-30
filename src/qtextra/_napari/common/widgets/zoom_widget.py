"""Zoom widget for napari viewer."""

from __future__ import annotations

import typing as ty
from weakref import ref

from qtpy.QtWidgets import QFormLayout, QWidget

import qtextra.helpers as hp
from qtextra.widgets.qt_dialog import QtFramelessPopup

if ty.TYPE_CHECKING:
    from napari_plot.viewer import Viewer


class ZoomPopup(QtFramelessPopup):
    """Dialog to zoom-in on specific region of plot."""

    def __init__(
        self,
        viewer: Viewer,
        parent: QWidget | None = None,
        default_value: float | None = None,
        default_window: float | None = None,
        default_auto_scale: bool = True,
    ):
        self.ref_viewer: ty.Callable[[], Viewer] = ref(viewer)
        self._default_value = default_value
        self._default_window = default_window
        self._default_auto_scale = default_auto_scale
        super().__init__(parent=parent)
        self.position.setFocus()

    def on_zoom(self) -> None:
        """Zoom-in on position."""

    # noinspection PyAttributeOutsideInit
    def make_panel(self) -> QFormLayout:
        """Make panel."""
        self.position = hp.make_double_spin_box(
            self,
            0,
            10000,
            0.5,
            n_decimals=2,
            value=self._default_value or 0.0,
            tooltip="Specify location you would like to zoom-in to.",
        )
        self.position.valueChanged.connect(self.on_zoom)

        self.window_spin = hp.make_double_spin_box(
            self,
            0.1,
            500,
            0.5,
            n_decimals=2,
            value=self._default_window or 0.1,
            tooltip="Specify window around the position. Position will be used as the center point and"
            "\n window will be subtracted and added to it.",
        )
        self.window_spin.valueChanged.connect(self.on_zoom)

        self.auto_scale_y = hp.make_checkbox(
            self, "", tooltip="When checked, the y-axis intensity will be auto-scaled to match the data range."
        )
        self.auto_scale_y.setChecked(self._default_auto_scale or True)
        self.auto_scale_y.stateChanged.connect(self.on_zoom)

        layout = hp.make_form_layout()
        layout.addRow(hp.make_label(self, "Position"), self.position)
        layout.addRow(hp.make_label(self, "Window"), self.window_spin)
        layout.addRow(hp.make_label(self, "Auto-scale intensity"), self.auto_scale_y)
        return layout


class XZoomPopup(ZoomPopup):
    """X-axis zoom widget."""

    def __init__(
        self,
        viewer: Viewer,
        parent: QWidget | None = None,
        default_value: float | None = None,
        default_window: float | None = None,
        default_auto_scale: bool = True,
    ):
        super().__init__(
            viewer,
            parent=parent,
            default_value=default_value,
            default_window=default_window,
            default_auto_scale=default_auto_scale,
        )
        self.setup()

    def setup(self) -> None:
        """Setup widget."""
        with hp.qt_signals_blocked(self.position):
            xmin, xmax, _, _ = self.ref_viewer()._get_rect_extent()
            self.position.setRange(xmin, xmax)

    def on_zoom(self) -> None:
        """Zoom-in on the range."""
        pos = self.position.value()
        window = self.window_spin.value()
        xmin, xmax = pos - window, pos + window
        self.ref_viewer().set_x_view(xmin, xmax, auto_scale=self.auto_scale_y.isChecked())
        # set default value
        parent = self.parent()
        if (
            parent is not None
            and hasattr(parent, "default_value")
            and hasattr(parent, "default_window")
            and hasattr(parent, "default_auto_scale")
        ):
            parent.default_value = pos
            parent.default_window = window
            parent.default_auto_scale = self.auto_scale_y.isChecked()
