"""Toolbar for MPL-based plots."""

import typing as ty

from qtpy.QtCore import Qt
from qtpy.QtWidgets import QHBoxLayout, QWidget

from qtextra.widgets.qt_mini_toolbar import QtMiniToolbar

if ty.TYPE_CHECKING:
    from qtextra._visuals.mpl import ViewMplLine


class MplToolbar(QWidget):
    """Toolbar."""

    def __init__(self, view: "ViewMplLine", parent):
        super().__init__(parent=parent)
        # create instance
        toolbar = QtMiniToolbar(self, Qt.Orientation.Vertical)

        # view reset/clear
        self.tools_erase_btn = toolbar.insert_qta_tool("erase", tooltip="Clear image", func=view.clear)
        self.tools_erase_btn.hide()
        self.tools_zoomout_btn = toolbar.insert_qta_tool("zoom_out", tooltip="Zoom-out", func=view.on_zoom_out)
        # view modifiers
        toolbar.insert_separator()
        self.tools_clip_btn = toolbar.insert_qta_tool(
            "clipboard",
            tooltip="Copy figure to clipboard",
            func=view.copy_to_clipboard,
        )
        self.tools_save_btn = toolbar.insert_qta_tool(
            "save",
            tooltip="Save figure",
            func=view.on_save_figure,
        )

        layout = QHBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(toolbar)
