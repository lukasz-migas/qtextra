"""Collapsible widget.

Taken from:
https://github.dev/napari/superqt/blob/f4d9881b0c64c0419fa2da182a1c403a01bd084f/src/superqt/collapsible/_collapsible.py
"""

from __future__ import annotations

import typing as ty

from qtpy.QtWidgets import QCheckBox, QHBoxLayout, QLayout, QWidget
from superqt import QCollapsible

import qtextra.helpers as hp
from qtextra.config import THEMES


class QtCheckCollapsible(QCollapsible):
    """A collapsible widget to hide and unhide child widgets.

    Based on https://stackoverflow.com/a/68141638
    """

    def __init__(self, title: str = "", parent: QWidget | None = None):
        super().__init__(title, parent)
        self._checkbox = QCheckBox()
        self._checkbox.stateChanged.connect(self._toggle_btn.setChecked)

        # remove button item from the layout
        self.layout().takeAt(0)

        # create layout where the first item is checkbox
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(1)
        layout.addWidget(self._checkbox)
        layout.addWidget(self._toggle_btn, stretch=True)

        # add widget to layout
        self.layout().addLayout(layout)
        self.layout().setSpacing(0)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self._set_icon()

        THEMES.evt_theme_icon_changed.connect(self._set_icon)

    def _set_icon(self):
        self.setExpandedIcon(hp.make_qta_icon("chevron_down"))
        self.setCollapsedIcon(hp.make_qta_icon("chevron_up"))

    def set_checkbox_visible(self, state: bool) -> None:
        """Show or hide the checkbox."""
        self._checkbox.setVisible(state)

    @property
    def is_checked(self) -> bool:
        """Determine whether widget is checked."""
        return self._checkbox.isChecked()

    def _toggle(self):
        self._checkbox.setChecked(self._toggle_btn.isChecked())
        super()._toggle()

    def _checked(self):
        self._toggle_btn.setChecked(self._checkbox.isChecked())

    def addLayout(self, layout: QLayout):
        """Add layout to the central content widget's layout."""
        self._content.layout().addLayout(layout)

    def addRow(self, label: QWidget | QLayout, widget: QWidget | None = None):
        """Add layout to the central content widget's layout."""
        if not hasattr(self._content.layout(), "addRow"):
            raise ValueError("Layout does not have `addRow` method.")
        if widget:
            self._content.layout().addRow(label, widget)
        else:
            self._content.layout().addRow(label)


if __name__ == "__main__":  # pragma: no cover

    def _main():  # type: ignore[no-untyped-def]
        import sys

        from qtextra.utils.dev import qmain, theme_toggle_btn

        app, frame, ha = qmain(False)
        frame.setMinimumSize(600, 600)
        ha.addWidget(theme_toggle_btn(frame))

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
