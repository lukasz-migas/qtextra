"""Dictionary tag editor widget."""

from __future__ import annotations

from collections.abc import Mapping

from qtpy.QtCore import Qt, Signal
from qtpy.QtGui import QDoubleValidator, QIntValidator
from qtpy.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHeaderView,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
)

import qtextra.helpers as hp

DictTagValue = str | int | float | None

TYPE_ROLE = Qt.ItemDataRole.UserRole + 1
VALUE_ROLE = Qt.ItemDataRole.UserRole + 2


class QtDictTagEditor(QWidget):
    """Editor for managing a searchable dictionary with typed values."""

    evt_items_changed = Signal(dict)
    evt_item_added = Signal(str, object)
    evt_item_removed = Signal(str)
    evt_key_text_changed = Signal(str)
    evt_value_text_changed = Signal(str)
    evt_search_changed = Signal(str)

    def __init__(
        self,
        parent: QWidget | None = None,
        key_placeholder: str = "Key...",
        value_placeholder: str = "Value...",
        search_placeholder: str = "Search...",
        *,
        case_sensitive: bool = False,
    ) -> None:
        super().__init__(parent)
        self.case_sensitive = case_sensitive
        self._default_value_placeholder = value_placeholder

        self.search_edit = QLineEdit(self)
        self.search_edit.setPlaceholderText(search_placeholder)
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.textChanged.connect(self._on_search_changed)

        self.key_edit = QLineEdit(self)
        self.key_edit.setPlaceholderText(key_placeholder)
        self.key_edit.setClearButtonEnabled(True)
        self.key_edit.textChanged.connect(self.evt_key_text_changed.emit)

        self.value_edit = QLineEdit(self)
        self.value_edit.setPlaceholderText(value_placeholder)
        self.value_edit.setClearButtonEnabled(True)
        self.value_edit.textChanged.connect(self.evt_value_text_changed.emit)

        self.type_combo = QComboBox(self)
        self.type_combo.addItems(["str", "int", "float", "None"])
        self.type_combo.currentTextChanged.connect(self._on_type_changed)

        self.add_button = QPushButton("Add / Update", self)
        self.add_button.clicked.connect(self.add_current_item)

        self.remove_button = QPushButton("Remove Selected", self)
        self.remove_button.clicked.connect(self.remove_selected_item)

        self.clear_button = QPushButton("Clear", self)
        self.clear_button.clicked.connect(self.clear_items)

        self.key_edit.returnPressed.connect(self.add_current_item)
        self.value_edit.returnPressed.connect(self.add_current_item)
        self._on_type_changed(self.type_combo.currentText())

        self.table = QTableWidget(0, 3, self)
        self.table.setHorizontalHeaderLabels(["Key", "Value", "Type"])
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setMinimumSectionSize(80)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.table.itemSelectionChanged.connect(self._populate_inputs_from_selection)

        search_row = hp.make_h_layout(self.search_edit, spacing=4, margin=0)
        inputs_row = hp.make_h_layout(
            self.key_edit,
            self.value_edit,
            self.type_combo,
            self.add_button,
            self.remove_button,
            self.clear_button,
            spacing=4,
            margin=0,
        )
        inputs_row.setStretch(0, 2)
        inputs_row.setStretch(1, 2)

        hp.make_v_layout(search_row, inputs_row, self.table, spacing=6, margin=0, parent=self)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._resize_columns()

    def items(self) -> dict[str, DictTagValue]:
        """Return the current items in table order."""
        exported: dict[str, DictTagValue] = {}
        for row in range(self.table.rowCount()):
            key_item = self.table.item(row, 0)
            value_item = self.table.item(row, 1)
            if key_item is None or value_item is None:
                continue
            exported[key_item.text()] = value_item.data(VALUE_ROLE)
        return exported

    def export_dict(self) -> dict[str, DictTagValue]:
        """Export the current dictionary."""
        return self.items()

    def set_items(self, items: Mapping[str, DictTagValue]) -> None:
        """Replace all items."""
        self.clear_items(emit_signal=False)
        for key, value in items.items():
            self._set_row(key, value, emit_signal=False)
        self._apply_filter()
        self._emit_items_changed()

    def add_item(self, key: str, value: DictTagValue) -> bool:
        """Add or replace a single item."""
        if value is not None and not isinstance(value, (str, int, float)):
            raise TypeError("Value must be str, int, float, or None.")
        return self._set_row(key, value, emit_signal=True)

    def add_items(self, items: Mapping[str, DictTagValue]) -> list[str]:
        """Add or replace multiple items and return affected keys."""
        changed: list[str] = []
        for key, value in items.items():
            if self.add_item(key, value):
                changed.append(key.strip())
        return changed

    def add_current_item(self) -> bool:
        """Add or update the current key/value input."""
        key = self.key_edit.text().strip()
        if not key:
            return False

        try:
            value = self._coerce_value(self.value_edit.text(), self.type_combo.currentText())
        except ValueError:
            return False

        added = self.add_item(key, value)
        if added:
            self.key_edit.clear()
            self.value_edit.clear()
            self.table.clearSelection()
            self.key_edit.setFocus()
        return added

    def remove_item(self, key: str) -> bool:
        """Remove an item by key."""
        row = self._find_row(key)
        if row is None:
            return False

        key_item = self.table.item(row, 0)
        display_key = "" if key_item is None else key_item.text()
        self.table.removeRow(row)
        self.evt_item_removed.emit(display_key)
        self._emit_items_changed()
        return True

    def remove_selected_item(self) -> bool:
        """Remove the currently selected row."""
        row = self.table.currentRow()
        if row < 0:
            return False
        key_item = self.table.item(row, 0)
        if key_item is None:
            return False
        return self.remove_item(key_item.text())

    def clear_items(self, emit_signal: bool = True) -> None:
        """Remove all items."""
        self.table.setRowCount(0)
        self.table.clearSelection()
        self._resize_columns()
        if emit_signal:
            self._emit_items_changed()

    def has_item(self, key: str) -> bool:
        """Return whether a key is present."""
        return self._find_row(key) is not None

    def get_value(self, key: str) -> DictTagValue:
        """Return the value for a key."""
        row = self._find_row(key)
        if row is None:
            raise KeyError(key)
        item = self.table.item(row, 1)
        if item is None:
            raise KeyError(key)
        return item.data(VALUE_ROLE)

    def _set_row(self, key: str, value: DictTagValue, *, emit_signal: bool) -> bool:
        display_key = key.strip()
        if not display_key:
            return False

        row = self._find_row(display_key)
        value_type = self._infer_type(value)

        if row is None:
            row = self.table.rowCount()
            self.table.insertRow(row)
            key_item = QTableWidgetItem(display_key)
            value_item = QTableWidgetItem()
            type_item = QTableWidgetItem(value_type)
            self.table.setItem(row, 0, key_item)
            self.table.setItem(row, 1, value_item)
            self.table.setItem(row, 2, type_item)
        else:
            key_item = self.table.item(row, 0)
            value_item = self.table.item(row, 1)
            type_item = self.table.item(row, 2)
            if key_item is None or value_item is None or type_item is None:
                return False
            key_item.setText(display_key)

        value_item.setText(self._format_value(value))
        value_item.setData(TYPE_ROLE, value_type)
        value_item.setData(VALUE_ROLE, value)
        type_item.setText(value_type)

        self._apply_filter()
        self._resize_columns()
        if emit_signal:
            self.evt_item_added.emit(display_key, value)
            self._emit_items_changed()
        return True

    def _find_row(self, key: str) -> int | None:
        key_to_match = self._key_id(key.strip())
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item is not None and self._key_id(item.text()) == key_to_match:
                return row
        return None

    def _key_id(self, text: str) -> str:
        return text if self.case_sensitive else text.casefold()

    def _on_search_changed(self, text: str) -> None:
        self._apply_filter(text)
        self.evt_search_changed.emit(text)

    def _apply_filter(self, text: str | None = None) -> None:
        query = self.search_edit.text() if text is None else text
        normalized = query.strip().casefold()
        for row in range(self.table.rowCount()):
            haystack = " ".join(
                filter(
                    None,
                    [
                        self.table.item(row, 0).text() if self.table.item(row, 0) else "",
                        self.table.item(row, 1).text() if self.table.item(row, 1) else "",
                        self.table.item(row, 2).text() if self.table.item(row, 2) else "",
                    ],
                ),
            ).casefold()
            self.table.setRowHidden(row, bool(normalized and normalized not in haystack))

    def _populate_inputs_from_selection(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            return

        key_item = self.table.item(row, 0)
        value_item = self.table.item(row, 1)
        type_item = self.table.item(row, 2)
        if key_item is None or value_item is None or type_item is None:
            return

        self.key_edit.setText(key_item.text())
        self.type_combo.setCurrentText(type_item.text())
        value = value_item.data(VALUE_ROLE)
        self.value_edit.setText("" if value is None else str(value))

    def _coerce_value(self, text: str, value_type: str) -> DictTagValue:
        if value_type == "str":
            return text
        if value_type == "int":
            stripped = text.strip()
            if not stripped:
                raise ValueError("Integer value cannot be empty.")
            return int(stripped)
        if value_type == "float":
            stripped = text.strip()
            if not stripped:
                raise ValueError("Float value cannot be empty.")
            return float(stripped)
        if value_type == "None":
            return None
        raise ValueError(f"Unsupported value type: {value_type}")

    def _infer_type(self, value: DictTagValue) -> str:
        if value is None:
            return "None"
        if isinstance(value, bool):
            return "int"
        if isinstance(value, int):
            return "int"
        if isinstance(value, float):
            return "float"
        return "str"

    def _format_value(self, value: DictTagValue) -> str:
        return "None" if value is None else str(value)

    def _on_type_changed(self, value_type: str) -> None:
        if value_type == "int":
            self.value_edit.setValidator(QIntValidator(self))
            self.value_edit.setPlaceholderText("Integer value...")
            self.value_edit.setEnabled(True)
            return
        if value_type == "float":
            validator = QDoubleValidator(self)
            validator.setNotation(QDoubleValidator.Notation.StandardNotation)
            self.value_edit.setValidator(validator)
            self.value_edit.setPlaceholderText("Float value...")
            self.value_edit.setEnabled(True)
            return

        self.value_edit.setValidator(None)
        if value_type == "None":
            self.value_edit.clear()
            self.value_edit.setPlaceholderText("Ignored for None values")
            self.value_edit.setEnabled(False)
            return

        self.value_edit.setPlaceholderText(self._default_value_placeholder)
        self.value_edit.setEnabled(True)

    def _emit_items_changed(self) -> None:
        self.evt_items_changed.emit(self.export_dict())

    def _resize_columns(self) -> None:
        self.table.resizeColumnToContents(2)
        self.table.setColumnWidth(2, max(88, self.table.columnWidth(2) + 12))

    # Alias methods to offer a Qt-like interface
    addItem = add_item
    addItems = add_items
    addCurrentItem = add_current_item
    removeItem = remove_item
    removeSelectedItem = remove_selected_item
    clearItems = clear_items
    hasItem = has_item
    setItems = set_items
    getItems = items
    exportDict = export_dict
    getValue = get_value
