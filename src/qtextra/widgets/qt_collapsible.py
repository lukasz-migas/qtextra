"""Collapsible widget.

Taken from:
https://github.dev/napari/superqt/blob/f4d9881b0c64c0419fa2da182a1c403a01bd084f/src/superqt/collapsible/_collapsible.py
"""

from __future__ import annotations

from contextlib import suppress

from qtpy.QtCore import Qt
from qtpy.QtWidgets import QCheckBox, QHBoxLayout, QLayout, QWidget
from superqt import QCollapsible

import qtextra.helpers as hp
from qtextra.config import THEMES


class QtCheckCollapsible(QCollapsible):
    """A collapsible widget to hide and unhide child widgets.

    Based on https://stackoverflow.com/a/68141638
    """

    def __init__(
        self, title: str = "", parent: QWidget | None = None, icon: str = "info", warning_icon: str = "warning"
    ):
        super().__init__(title, parent)
        self.checkbox = QCheckBox()
        self.checkbox.stateChanged.connect(self._toggle_btn.setChecked)

        # remove button item from the layout
        self.layout().takeAt(0)

        self.action_btn = hp.make_qta_btn(self, icon_name=icon, standout=True, average=True)

        self.warning_label = hp.make_warning_label(self, "", icon_name=warning_icon, normal=True)

        # create layout where the first item is checkbox
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(1)
        layout.addWidget(self.checkbox)
        layout.addWidget(self._toggle_btn, stretch=True)
        layout.addWidget(self.action_btn, alignment=Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.warning_label, alignment=Qt.AlignmentFlag.AlignVCenter)

        # add widget to layout
        self.layout().addLayout(layout)
        self.layout().setSpacing(0)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self._update_icon()

        content = QWidget()
        layout = hp.make_form_layout(parent=content)
        layout.setContentsMargins(2, 2, 2, 2)
        self.setContent(content)
        with suppress(RuntimeError):
            THEMES.evt_theme_icon_changed.connect(self._update_icon)

    def _update_icon(self) -> None:
        self.setExpandedIcon(hp.make_qta_icon("chevron_down"))
        self.setCollapsedIcon(hp.make_qta_icon("chevron_up"))

    def set_checkbox_visible(self, state: bool) -> None:
        """Show or hide the checkbox."""
        self.checkbox.setVisible(state)

    def set_icon_visible(self, state: bool) -> None:
        """Show or hide the checkbox."""
        self.action_btn.setVisible(state)

    def set_warning_visible(self, state: bool) -> None:
        """Show or hide the checkbox."""
        self.warning_label.setVisible(state)

    @property
    def is_checked(self) -> bool:
        """Determine whether widget is checked."""
        return self.checkbox.isChecked()

    def _toggle(self):
        self.checkbox.setChecked(self._toggle_btn.isChecked())
        super()._toggle()

    def _checked(self):
        self._toggle_btn.setChecked(self.checkbox.isChecked())

    def addLayout(self, layout: QLayout):
        """Add layout to the central content widget's layout."""
        self._content.layout().addLayout(layout)

    def addRow(self, label: str | QWidget | QLayout, widget: QWidget | None = None):
        """Add layout to the central content widget's layout."""
        if not hasattr(self._content.layout(), "addRow"):
            raise ValueError("Layout does not have `addRow` method.")
        if widget:
            self._content.layout().addRow(label, widget)
        else:
            self._content.layout().addRow(label)

    # Alias methods to offer Qt-like interface
    setCheckboxVisible = set_checkbox_visible
    setIconVisible = set_icon_visible
    setWarningVisible = set_warning_visible


if __name__ == "__main__":  # pragma: no cover

    def _main():  # type: ignore[no-untyped-def]
        import sys

        from qtextra.utils.dev import qframe

        app, frame, ha = qframe(False)
        frame.setMinimumSize(600, 600)

        wdg = QtCheckCollapsible(parent=frame)
        wdg.setText("Advanced options")
        ha.addWidget(wdg)

        wdg = QtCheckCollapsible(parent=frame)
        wdg.set_checkbox_visible(False)
        wdg.setText("Advanced options")
        ha.addWidget(wdg)

        frame.show()
        sys.exit(app.exec_())

    _main()
