"""Popup for developer tools."""
from qtpy.QtWidgets import QLayout, QVBoxLayout, QWidget
from qtreload.qt_reload import QtReloadWidget

from qtextra.widgets.qt_dialog import QtFramelessTool


class QDevPopup(QtFramelessTool):
    HIDE_WHEN_CLOSE = True

    def __init__(self, parent: QWidget, modules: list[str]):
        self.modules = modules
        super().__init__(parent)

    # noinspection PyAttributeOutsideInit
    def make_panel(self) -> QLayout:
        """Make panel."""
        self.qdev = QtReloadWidget(self.modules, self)

        _, hide_layout = self._make_hide_handle("Developer tools")
        layout = QVBoxLayout()
        layout.setContentsMargins(6, 6, 6, 6)
        layout.addLayout(hide_layout)
        layout.addWidget(self.qdev, stretch=True)
        return layout
