"""Combobox with a remove button."""

from __future__ import annotations

import typing as ty

from qtpy.QtCore import Signal
from qtpy.QtWidgets import QComboBox, QSizePolicy, QWidget

import qtextra.helpers as hp


class QtRemovableComboBox(QWidget):
    """Combobox with a remove button next to it.

    Intended for use in dynamic UIs where the user can add/remove combobox rows.
    When the remove button is clicked, the `evt_removed` signal is emitted and the
    widget is hidden. The parent is responsible for actually removing the widget from
    the layout if desired.
    """

    evt_removed = Signal(object)
    currentIndexChanged = Signal(int)
    currentTextChanged = Signal(str)

    def __init__(
        self,
        parent: QWidget | None = None,
        items: ty.Sequence[str] | None = None,
        tooltip: str = "",
        remove_tooltip: str = "Remove",
    ):
        super().__init__(parent)
        self.combobox = QComboBox(self)
        self.combobox.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        if tooltip:
            self.combobox.setToolTip(tooltip)
        if items:
            self.combobox.addItems(items)

        self.remove_btn = hp.make_qta_btn(
            self,
            "delete",
            tooltip=remove_tooltip,
            size_preset="small",
            func=self._on_remove,
        )

        layout = hp.make_h_layout(parent=self, margin=0, spacing=1)
        layout.addWidget(self.combobox, 1)
        layout.addWidget(self.remove_btn, 0)

        # forward combobox signals
        self.combobox.currentIndexChanged.connect(self.currentIndexChanged)
        self.combobox.currentTextChanged.connect(self.currentTextChanged)

    def _on_remove(self) -> None:
        """Handle remove button click."""
        self.evt_removed.emit(self)
        self.hide()

    # -- QComboBox API forwarding --

    def addItem(self, *args: ty.Any) -> None:
        """Add item to the combobox."""
        self.combobox.addItem(*args)

    def addItems(self, items: ty.Sequence[str]) -> None:
        """Add items to the combobox."""
        self.combobox.addItems(items)

    def removeItem(self, index: int) -> None:
        """Remove item from the combobox."""
        self.combobox.removeItem(index)

    def currentIndex(self) -> int:
        """Return the current index."""
        return self.combobox.currentIndex()

    def setCurrentIndex(self, index: int) -> None:
        """Set the current index."""
        self.combobox.setCurrentIndex(index)

    def currentText(self) -> str:
        """Return the current text."""
        return self.combobox.currentText()

    def setCurrentText(self, text: str) -> None:
        """Set the current text."""
        self.combobox.setCurrentText(text)

    def currentData(self, role: int = 256) -> ty.Any:
        """Return the current data."""
        return self.combobox.currentData(role)

    def count(self) -> int:
        """Return the number of items."""
        return self.combobox.count()

    def clear(self) -> None:
        """Clear all items."""
        self.combobox.clear()

    def setEditable(self, editable: bool) -> None:
        """Set whether the combobox is editable."""
        self.combobox.setEditable(editable)

    def itemText(self, index: int) -> str:
        """Return the text at the given index."""
        return self.combobox.itemText(index)

    def itemData(self, index: int, role: int = 256) -> ty.Any:
        """Return the data at the given index."""
        return self.combobox.itemData(index, role)

    def setItemText(self, index: int, text: str) -> None:
        """Set the text at the given index."""
        self.combobox.setItemText(index, text)

    def setItemData(self, index: int, value: ty.Any, role: int = 256) -> None:
        """Set the data at the given index."""
        self.combobox.setItemData(index, value, role)

    def findText(self, text: str) -> int:
        """Find the index of the given text."""
        return self.combobox.findText(text)


if __name__ == "__main__":  # pragma: no cover
    import sys

    from qtextra.utils.dev import qframe

    app, frame, ha = qframe(False)

    def _removed(widget: QtRemovableComboBox) -> None:
        ha.removeWidget(widget)
        widget.deleteLater()

    for i in range(3):
        combo = QtRemovableComboBox(items=["Option A", "Option B", "Option C"])
        combo.setCurrentIndex(i)
        combo.evt_removed.connect(_removed)
        ha.addWidget(combo)

    frame.show()
    sys.exit(app.exec_())
