import typing as ty
from weakref import ref

from napari.utils.events import disconnect_events
from napari_plot._qt.component_controls.qt_axis_controls import QtAxisWidget
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QFormLayout

from qtextra.widgets.qt_dialog import QtFramelessPopup

if ty.TYPE_CHECKING:
    from napari_plot.viewer import ViewerModel


class QtAxisControls(QtFramelessPopup):
    """Popup to control x/y-axis visual."""

    def __init__(self, viewer: "ViewerModel", parent=None):
        self.ref_viewer = ref(viewer)

        super().__init__(parent=parent)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setObjectName("axis")
        self.setMouseTracking(True)

    # noinspection PyAttributeOutsideInit
    def make_panel(self) -> QFormLayout:
        """Make panel."""
        widget = QtAxisWidget(self.ref_viewer(), self)
        layout = QFormLayout()
        layout.setSpacing(2)
        layout.addRow(self._make_move_handle("Axis controls"))
        layout.addRow(widget)
        return layout

    def close(self):
        """Disconnect events when widget is closing."""
        disconnect_events(self.ref_viewer().axis.events, self)
        super().close()
