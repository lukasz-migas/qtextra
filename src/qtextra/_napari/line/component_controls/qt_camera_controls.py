import typing as ty
from weakref import ref

from napari.utils.events import disconnect_events
from napari_plot._qt.component_controls.qt_camera_controls import QtCameraWidget
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QFormLayout

from qtextra.widgets.qt_dialog import QtFramelessPopup

if ty.TYPE_CHECKING:
    from napari_plot.viewer import ViewerModel


class QtCameraControls(QtFramelessPopup):
    """Popup to control camera model."""

    def __init__(self, viewer: "ViewerModel", parent=None):
        self.ref_viewer = ref(viewer)

        super().__init__(parent=parent)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setObjectName("camera")
        self.setMouseTracking(True)

    # noinspection PyAttributeOutsideInit
    def make_panel(self) -> QFormLayout:
        """Make panel."""
        widget = QtCameraWidget(self.ref_viewer(), self)
        layout = QFormLayout()
        layout.setSpacing(2)
        layout.addRow(self._make_move_handle("Camera controls"))
        layout.addRow(widget)
        return layout

    def close(self):
        """Disconnect events when widget is closing."""
        disconnect_events(self.ref_viewer().camera.events, self)
        super().close()
