"""Searchable combobox."""
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QComboBox, QCompleter, QStyledItemDelegate


class QtSearchableComboBox(QComboBox):
    """Searchable combobox."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setEditable(True)
        self.completer_object = QCompleter()
        self.completer_object.setCaseSensitivity(Qt.CaseInsensitive)
        self.completer_object.setModelSorting(QCompleter.CaseSensitivelySortedModel)
        self.completer_object.setFilterMode(Qt.MatchContains)
        self.setCompleter(self.completer_object)
        self.setInsertPolicy(QComboBox.NoInsert)  # ensures that incorrect values are not added
        self.completer_object.popup().setItemDelegate(QStyledItemDelegate(self))
        self.completer_object.popup().setObjectName("search_box_popup")

    def _text_activated(self):  # pragma: no cover
        self.textActivated.emit(self.currentText())

    def addItem(self, *args):
        """Add item."""
        super().addItem(*args)
        self.completer_object.setModel(self.model())

    def addItems(self, *args):
        """Add items."""
        super().addItems(*args)
        self.completer_object.setModel(self.model())

    def removeItem(self, index: int):
        """Remove item."""
        super().removeItem(index)
        self.completer_object.setModel(self.model())
