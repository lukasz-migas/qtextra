"""Collapsible widget.

Taken from:
https://github.dev/napari/superqt/blob/f4d9881b0c64c0419fa2da182a1c403a01bd084f/src/superqt/collapsible/_collapsible.py
"""
import typing as ty

from qtpy.QtWidgets import QCheckBox, QHBoxLayout, QWidget
from superqt import QCollapsible


class QtCheckCollapsible(QCollapsible):
    """A collapsible widget to hide and unhide child widgets.

    Based on https://stackoverflow.com/a/68141638
    """

    _EXPANDED = "▼  "
    _COLLAPSED = "▲  "

    def __init__(self, title: str = "", parent: ty.Optional[QWidget] = None):
        super().__init__(title, parent)
        self._checkbox = QCheckBox()
        self._checkbox.stateChanged.connect(self._toggle_btn.setChecked)

        # remove button item from the layout
        self.layout().takeAt(0)

        # create layout where the first item is checkbox
        layout = QHBoxLayout()
        layout.addWidget(self._checkbox)
        layout.addWidget(self._toggle_btn, stretch=True)

        # add widget to layout
        self.layout().addLayout(layout)

    @property
    def is_checked(self) -> bool:
        """Determine whether widget is checked."""
        return self._checkbox.isChecked()

    def _toggle(self):
        self._checkbox.setChecked(self._toggle_btn.isChecked())
        super()._toggle()

    def _checked(self):
        self._toggle_btn.setChecked(self._checkbox.isChecked())

    def addLayout(self, layout):
        """Add layout to the central content widget's layout."""
        self._content.layout().addLayout(layout)

    def addRow(self, label, widget):
        """Add layout to the central content widget's layout."""
        if not hasattr(self._content.layout(), "addRow"):
            raise ValueError("Layout does not havd `addRow` method.")
        self._content.layout().addRow(label, widget)


if __name__ == "__main__":  # pragma: no cover

    def _main():
        import sys
        from random import choice

        from qtextra.config.theme import THEMES
        from qtextra.helpers import make_btn
        from qtextra.utils.dev import qmain

        def _toggle_theme():
            THEMES.theme = choice(THEMES.available_themes())
            THEMES.set_theme_stylesheet(frame)

        app, frame, ha = qmain(False)
        frame.setMinimumSize(600, 600)

        wdg = make_btn(frame, "Click here to toggle theme")
        wdg.clicked.connect(_toggle_theme)
        ha.addWidget(wdg)

        wdg = QtCheckCollapsible(parent=frame)
        wdg.setText("Advanced options")
        ha.addWidget(wdg)

        frame.show()
        sys.exit(app.exec_())

    _main()
