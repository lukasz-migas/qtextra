"""Info widget."""

from qtpy.QtWidgets import QFormLayout, QWidget

import qtextra.helpers as hp
from qtextra.widgets.qt_dialog import QtFramelessPopup


class InfoDialog(QtFramelessPopup):
    """Dialog to display some useful information."""

    def __init__(self, parent: QWidget, text: str):
        super().__init__(parent)
        self.setMinimumWidth(300)
        self.setMinimumHeight(200)
        self.label.setText(text)

    # noinspection PyAttributeOutsideInit
    def make_panel(self) -> QFormLayout:
        """Make panel."""
        header_layout = self._make_title_handle("Help information")

        self.label = hp.make_scrollable_label(
            self, wrap=True, enable_url=True, selectable=True, object_name="title_label"
        )

        layout = hp.make_form_layout(parent=self)
        layout.addRow(header_layout)
        layout.addRow(self.label)
        return layout
