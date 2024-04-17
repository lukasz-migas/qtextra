from weakref import ref

from qtpy.QtWidgets import QFormLayout

import qtextra.helpers as hp
from qtextra.widgets.qt_dialog import QtFramelessPopup


class ZoomPopup(QtFramelessPopup):
    """Dialog to zoom-in on specific region of plot."""

    def __init__(self, viewer, parent=None):
        self.ref_viewer = ref(viewer)
        super().__init__(parent=parent)
        self.position.setFocus()

    def on_zoom(self):
        """Zoom-in on position."""

    # noinspection PyAttributeOutsideInit
    def make_panel(self) -> QFormLayout:
        """Make panel."""
        self.position = hp.make_double_spin_box(
            self, 0, 10000, 0.5, n_decimals=2, tooltip="Specify location you would like to zoom-in to."
        )
        self.position.valueChanged.connect(self.on_zoom)

        self.window = hp.make_double_spin_box(
            self,
            0.1,
            500,
            0.5,
            n_decimals=2,
            tooltip="Specify window around the position. Position will be used as the center point and"
            "\n window will be subtracted and added to it.",
        )
        self.window.setValue(1)
        self.window.valueChanged.connect(self.on_zoom)

        self.auto_scale_y = hp.make_checkbox(
            self, "", tooltip="When checked, the y-axis intensity will be auto-scaled to match the data range."
        )
        self.auto_scale_y.setChecked(True)
        self.auto_scale_y.stateChanged.connect(self.on_zoom)

        layout = hp.make_form_layout()
        layout.addRow(hp.make_label(self, "Position"), self.position)
        layout.addRow(hp.make_label(self, "Window"), self.window)
        layout.addRow(hp.make_label(self, "Auto-scale intensity"), self.auto_scale_y)

        return layout


class XZoomPopup(ZoomPopup):
    """X-axis zoom widget."""

    def __init__(self, viewer, parent=None):
        super().__init__(viewer, parent=parent)
        self.setup()

    def setup(self) -> None:
        """Setup widget."""
        with hp.qt_signals_blocked(self.position):
            xmin, xmax, _, _ = self.ref_viewer()._get_rect_extent()
            self.position.setRange(xmin, xmax)

    def on_zoom(self):
        """Zoom-in on the range."""
        pos = self.position.value()
        window = self.window.value()
        xmin, xmax = pos - window, pos + window
        self.ref_viewer().set_x_view(xmin, xmax, auto_scale=self.auto_scale_y.isChecked())
