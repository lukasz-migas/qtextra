"""Searchable combobox."""

from __future__ import annotations

import typing as ty

from qtpy.QtCore import Qt
from qtpy.QtWidgets import QComboBox, QCompleter, QStyledItemDelegate, QWidget


class QtSearchableComboBox(QComboBox):
    """Searchable combobox."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setEditable(True)
        self.completer_object = QCompleter()
        self.completer_object.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.completer_object.setModelSorting(QCompleter.ModelSorting.CaseSensitivelySortedModel)
        self.completer_object.setFilterMode(Qt.MatchFlag.MatchContains)
        self.completer_object.activated.connect(self.on_activated)
        self.setCompleter(self.completer_object)
        self.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)  # ensures that incorrect values are not added
        self.completer_object.popup().setItemDelegate(QStyledItemDelegate(self))
        self.completer_object.popup().setObjectName("search_box_popup")

    def _text_activated(self):  # pragma: no cover
        self.textActivated.emit(self.currentText())

    def on_activated(self, value: str):
        """On activated."""
        self.currentIndexChanged.emit(self.currentIndex())
        self.currentTextChanged.emit(self.currentText())

    def addItem(self, *args):
        """Add item."""
        super().addItem(*args)
        self.completer_object.setModel(self.model())

    def addItems(self, items: ty.Sequence[str]):
        """Add items."""
        super().addItems(items)
        self.completer_object.setModel(self.model())

    def removeItem(self, index: int):
        """Remove item."""
        super().removeItem(index)
        self.completer_object.setModel(self.model())

    # Alias methods to offer Qt-like interface
    _textActivated = _text_activated
    onActivated = on_activated


def add_search_to_combobox(combo: QComboBox) -> None:
    """Add search to combobox."""
    combo.setEditable(True)
    completer_object = QCompleter()
    completer_object.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
    completer_object.setModelSorting(QCompleter.ModelSorting.CaseSensitivelySortedModel)
    completer_object.setFilterMode(Qt.MatchFlag.MatchContains)
    combo.setCompleter(completer_object)
    combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)  # ensures that incorrect values are not added
    completer_object.popup().setItemDelegate(QStyledItemDelegate(combo))
    completer_object.popup().setObjectName("search_box_popup")
    combo.completer_object = completer_object
    combo._text_activated = lambda: combo.textActivated.emit(combo.currentText())
