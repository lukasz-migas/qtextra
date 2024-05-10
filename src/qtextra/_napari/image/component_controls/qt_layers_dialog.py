"""Tool dialog to display layer controls."""

import typing as ty
from weakref import ref

from qtpy.QtCore import QEvent, Qt
from qtpy.QtWidgets import QVBoxLayout

from qtextra.widgets.qt_dialog import QtFramelessTool

if ty.TYPE_CHECKING:
    from napari._qt.qt_viewer import QtViewer


class DialogNapariControls(QtFramelessTool):
    """Controls display."""

    def __init__(self, qt_viewer: "QtViewer"):
        self.ref_qt_viewer: ty.Callable[[], "QtViewer"] = ref(qt_viewer)
        super().__init__(parent=qt_viewer)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        self.setMinimumHeight(600)

    def make_panel(self) -> QVBoxLayout:
        """Make panel."""
        qt_viewer = self.ref_qt_viewer()

        va = QVBoxLayout()
        va.setSpacing(1)
        va.setContentsMargins(6, 6, 6, 6)
        va.addLayout(self._make_hide_handle("Viewer Controls")[1])
        va.addWidget(qt_viewer.controls)
        va.addWidget(qt_viewer.layerButtons)
        va.addWidget(qt_viewer.layers, stretch=True)
        va.addWidget(qt_viewer.viewerButtons)
        return va

    def keyPressEvent(self, event: QEvent) -> None:  # type: ignore[override]
        """Called whenever a key is pressed."""
        qt_viewer = self.ref_qt_viewer()
        qt_viewer.canvas._backend._keyEvent(qt_viewer.canvas.events.key_press, event)
        event.accept()

    def keyReleaseEvent(self, event: QEvent) -> None:  # type: ignore[override]
        """Called whenever a key is released."""
        qt_viewer = self.ref_qt_viewer()
        qt_viewer.canvas._backend._keyEvent(qt_viewer.canvas.events.key_release, event)
        event.accept()
