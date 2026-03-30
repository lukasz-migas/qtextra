"""Multi-dictionary tag editor widget."""

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
from qtextra.widgets.qt_dict_tag_editor import DictTagValue

TYPE_ROLE = Qt.ItemDataRole.UserRole + 1
VALUE_ROLE = Qt.ItemDataRole.UserRole + 2
PRESENT_ROLE = Qt.ItemDataRole.UserRole + 3

ALL_SAMPLES_LABEL = "All samples"


class QtMultiDictTagEditor(QWidget):
    """Editor for managing multiple dictionaries side by side."""

    evt_items_changed = Signal(dict)
    evt_key_added = Signal(str)
    evt_key_removed = Signal(str)
    evt_value_changed = Signal(str, str, object)
    evt_search_changed = Signal(str)
    evt_target_changed = Signal(str)

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        samples: list[str] | None = None,
        key_placeholder: str = "Key...",
        value_placeholder: str = "Value...",
        search_placeholder: str = "Search...",
        case_sensitive: bool = False,
    ) -> None:
        super().__init__(parent)
        self.case_sensitive = case_sensitive
        self._default_value_placeholder = value_placeholder
        self._samples: list[str] = []

        self.search_edit = QLineEdit(self)
        self.search_edit.setPlaceholderText(search_placeholder)
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.textChanged.connect(self._on_search_changed)

        self.key_edit = QLineEdit(self)
        self.key_edit.setPlaceholderText(key_placeholder)
        self.key_edit.setClearButtonEnabled(True)

        self.value_edit = QLineEdit(self)
        self.value_edit.setPlaceholderText(value_placeholder)
        self.value_edit.setClearButtonEnabled(True)

        self.type_combo = QComboBox(self)
        self.type_combo.addItems(["str", "int", "float", "None"])
        self.type_combo.currentTextChanged.connect(self._on_type_changed)

        self.target_combo = QComboBox(self)
        self.target_combo.currentTextChanged.connect(self._on_target_changed)

        self.add_key_button = QPushButton("Add Key", self)
        self.add_key_button.clicked.connect(self.add_current_key)

        self.apply_value_button = QPushButton("Apply Value", self)
        self.apply_value_button.clicked.connect(self.apply_current_value)

        self.remove_key_button = QPushButton("Remove Key", self)
        self.remove_key_button.clicked.connect(self.remove_selected_key)

        self.clear_button = QPushButton("Clear", self)
        self.clear_button.clicked.connect(self.confirm_clear_items)

        self.key_edit.returnPressed.connect(self.add_current_key)
        self.value_edit.returnPressed.connect(self.apply_current_value)
        self._on_type_changed(self.type_combo.currentText())

        self.table = QTableWidget(0, 2, self)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setMinimumSectionSize(88)
        self.table.itemSelectionChanged.connect(self._populate_inputs_from_selection)
        self.table.cellDoubleClicked.connect(self._on_cell_double_clicked)

        search_row = hp.make_h_layout(self.search_edit, spacing=4, margin=0)
        controls_row = hp.make_h_layout(
            self.key_edit,
            self.value_edit,
            self.type_combo,
            self.target_combo,
            self.add_key_button,
            self.apply_value_button,
            self.remove_key_button,
            self.clear_button,
            spacing=4,
            margin=0,
        )
        controls_row.setStretch(0, 2)
        controls_row.setStretch(1, 2)

        hp.make_v_layout(search_row, controls_row, self.table, spacing=6, margin=0, parent=self)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.set_samples(samples or [])
        self._resize_columns()

    def sample_names(self) -> list[str]:
        """Return the configured sample names."""
        return list(self._samples)

    def set_samples(self, samples: list[str]) -> None:
        """Set the active sample names."""
        cleaned = [sample.strip() for sample in samples if sample.strip()]
        self._samples = cleaned
        self.target_combo.blockSignals(True)
        self.target_combo.clear()
        self.target_combo.addItem(ALL_SAMPLES_LABEL)
        self.target_combo.addItems(self._samples)
        self.target_combo.blockSignals(False)
        self._rebuild_table_headers()
        self._resize_columns()

    def items(self) -> dict[str, dict[str, DictTagValue]]:
        """Return the current sample dictionaries."""
        exported = {sample: {} for sample in self._samples}
        for row in range(self.table.rowCount()):
            key_item = self.table.item(row, 0)
            if key_item is None:
                continue
            key = key_item.text()
            for sample in self._samples:
                item = self.table.item(row, self._sample_column(sample))
                if item is None or not item.data(PRESENT_ROLE):
                    continue
                exported[sample][key] = item.data(VALUE_ROLE)
        return exported

    def export_dicts(self) -> dict[str, dict[str, DictTagValue]]:
        """Export the current nested dictionaries."""
        return self.items()

    def set_items(self, items: Mapping[str, Mapping[str, DictTagValue]]) -> None:
        """Replace all sample dictionaries."""
        self.set_samples(list(items))
        self.clear_items(emit_signal=False)

        ordered_keys: list[str] = []
        seen: set[str] = set()
        for sample in self._samples:
            for key in items[sample]:
                normalized = self._key_id(key)
                if normalized in seen:
                    continue
                seen.add(normalized)
                ordered_keys.append(key)

        for key in ordered_keys:
            row = self._ensure_row(key)
            row_values: dict[str, DictTagValue] = {}
            for sample in self._samples:
                if key in items[sample]:
                    row_values[sample] = items[sample][key]
                else:
                    matched_key = self._find_key_in_sample(items[sample], key)
                    if matched_key is not None:
                        row_values[sample] = items[sample][matched_key]
            self._set_row_values(row, row_values, emit_signal=False)

        self._apply_filter()
        self._resize_columns()
        self._emit_items_changed()

    def add_key(
        self,
        key: str,
        value: DictTagValue = None,
        *,
        target_sample: str | None = None,
        value_type: str | None = None,
    ) -> bool:
        """Add a key to one sample or all samples."""
        display_key = key.strip()
        if not display_key:
            return False
        if value is not None and not isinstance(value, (str, int, float)):
            raise TypeError("Value must be str, int, float, or None.")

        row = self._ensure_row(display_key)
        samples = self._target_samples(target_sample)
        if not samples:
            return False

        if value_type is None:
            value_type = self._infer_type(value)
        self._set_row_type(row, value_type)
        for sample in samples:
            self._set_sample_value(row, sample, value, present=True)

        self._apply_filter()
        self._resize_columns()
        self.evt_key_added.emit(display_key)
        self._emit_items_changed()
        return True

    def set_value(
        self,
        key: str,
        value: DictTagValue,
        *,
        target_sample: str | None = None,
        value_type: str | None = None,
    ) -> bool:
        """Set a value for a key in one sample or all samples."""
        if value is not None and not isinstance(value, (str, int, float)):
            raise TypeError("Value must be str, int, float, or None.")

        row = self._find_row(key)
        if row is None:
            return False

        samples = self._target_samples(target_sample)
        if not samples:
            return False

        value_type = self._infer_type(value) if value_type is None else value_type
        self._set_row_type(row, value_type)
        display_key = self.table.item(row, 0).text() if self.table.item(row, 0) else key.strip()
        for sample in samples:
            self._set_sample_value(row, sample, value, present=True)
            self.evt_value_changed.emit(display_key, sample, value)

        self._apply_filter()
        self._resize_columns()
        self._emit_items_changed()
        return True

    def add_current_key(self) -> bool:
        """Add the current key to the selected target."""
        key = self.key_edit.text().strip()
        if not key:
            return False
        try:
            value = self._coerce_value(self.value_edit.text(), self.type_combo.currentText())
        except ValueError:
            return False
        added = self.add_key(
            key,
            value,
            target_sample=self.current_target_sample(),
            value_type=self.type_combo.currentText(),
        )
        if added:
            self.key_edit.clear()
            self.value_edit.clear()
            self.key_edit.setFocus()
        return added

    def apply_current_value(self) -> bool:
        """Apply the current value to the selected target for the current key."""
        key = self.key_edit.text().strip()
        if not key:
            row = self.table.currentRow()
            if row < 0:
                return False
            item = self.table.item(row, 0)
            if item is None:
                return False
            key = item.text()

        try:
            value = self._coerce_value(self.value_edit.text(), self.type_combo.currentText())
        except ValueError:
            return False

        return self.set_value(
            key,
            value,
            target_sample=self.current_target_sample(),
            value_type=self.type_combo.currentText(),
        )

    def remove_key(self, key: str) -> bool:
        """Remove a key from all samples."""
        row = self._find_row(key)
        if row is None:
            return False
        key_item = self.table.item(row, 0)
        display_key = "" if key_item is None else key_item.text()
        self.table.removeRow(row)
        self.evt_key_removed.emit(display_key)
        self._emit_items_changed()
        return True

    def remove_selected_key(self) -> bool:
        """Remove the selected key row."""
        row = self.table.currentRow()
        if row < 0:
            return False
        key_item = self.table.item(row, 0)
        if key_item is None:
            return False
        return self.remove_key(key_item.text())

    def clear_items(self, emit_signal: bool = True) -> None:
        """Remove all keys from all samples."""
        self.table.setRowCount(0)
        self.table.clearSelection()
        self._resize_columns()
        if emit_signal:
            self._emit_items_changed()

    def confirm_clear_items(self) -> bool:
        """Ask for confirmation before clearing all keys."""
        if not hp.confirm(self, "Are you sure you want to clear all items?", "Clear items?"):
            return False
        self.clear_items()
        return True

    def get_value(self, key: str, sample: str) -> DictTagValue:
        """Return the typed value for a key in a sample."""
        row = self._find_row(key)
        if row is None:
            raise KeyError(key)
        if sample not in self._samples:
            raise KeyError(sample)
        item = self.table.item(row, self._sample_column(sample))
        if item is None or not item.data(PRESENT_ROLE):
            raise KeyError(f"{sample}:{key}")
        return item.data(VALUE_ROLE)

    def current_target_sample(self) -> str | None:
        """Return the current target sample, or ``None`` for all samples."""
        current = self.target_combo.currentText()
        if current == ALL_SAMPLES_LABEL:
            return None
        return current or None

    def _rebuild_table_headers(self) -> None:
        headers = ["Key", "Type", *self._samples]
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)

    def _sample_column(self, sample: str) -> int:
        return 2 + self._samples.index(sample)

    def _ensure_row(self, key: str) -> int:
        row = self._find_row(key)
        if row is not None:
            return row

        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(key.strip()))
        self.table.setItem(row, 1, QTableWidgetItem("None"))
        for sample in self._samples:
            self.table.setItem(row, self._sample_column(sample), QTableWidgetItem(""))
            self._set_sample_value(row, sample, None, present=False)
        return row

    def _find_row(self, key: str) -> int | None:
        normalized = self._key_id(key)
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item is not None and self._key_id(item.text()) == normalized:
                return row
        return None

    def _find_key_in_sample(self, items: Mapping[str, DictTagValue], key: str) -> str | None:
        normalized = self._key_id(key)
        for existing_key in items:
            if self._key_id(existing_key) == normalized:
                return existing_key
        return None

    def _set_row_values(self, row: int, values: Mapping[str, DictTagValue], *, emit_signal: bool) -> None:
        row_type = self._infer_row_type(values.values())
        self._set_row_type(row, row_type)
        for sample in self._samples:
            if sample in values:
                self._set_sample_value(row, sample, values[sample], present=True)
                if emit_signal:
                    key_item = self.table.item(row, 0)
                    if key_item is not None:
                        self.evt_value_changed.emit(key_item.text(), sample, values[sample])

    def _set_row_type(self, row: int, value_type: str) -> None:
        type_item = self.table.item(row, 1)
        if type_item is None:
            type_item = QTableWidgetItem(value_type)
            self.table.setItem(row, 1, type_item)
        type_item.setText(value_type)
        type_item.setData(TYPE_ROLE, value_type)

    def _set_sample_value(self, row: int, sample: str, value: DictTagValue, *, present: bool) -> None:
        column = self._sample_column(sample)
        item = self.table.item(row, column)
        if item is None:
            item = QTableWidgetItem("")
            self.table.setItem(row, column, item)
        item.setData(PRESENT_ROLE, present)
        item.setData(VALUE_ROLE, value)
        item.setData(TYPE_ROLE, self._infer_type(value))
        item.setText("" if not present else self._format_value(value))

    def _target_samples(self, target_sample: str | None) -> list[str]:
        if target_sample is None:
            return list(self._samples)
        if target_sample not in self._samples:
            return []
        return [target_sample]

    def _key_id(self, text: str) -> str:
        normalized = text.strip()
        return normalized if self.case_sensitive else normalized.casefold()

    def _on_search_changed(self, text: str) -> None:
        self._apply_filter(text)
        self.evt_search_changed.emit(text)

    def _apply_filter(self, text: str | None = None) -> None:
        query = self.search_edit.text() if text is None else text
        normalized = query.strip().casefold()
        for row in range(self.table.rowCount()):
            values = []
            for column in range(self.table.columnCount()):
                item = self.table.item(row, column)
                if item is not None:
                    values.append(item.text())
            haystack = " ".join(values).casefold()
            self.table.setRowHidden(row, bool(normalized and normalized not in haystack))

    def _populate_inputs_from_selection(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            return

        key_item = self.table.item(row, 0)
        type_item = self.table.item(row, 1)
        if key_item is None or type_item is None:
            return

        self.key_edit.setText(key_item.text())
        self.type_combo.setCurrentText(type_item.text())

        sample = self.current_target_sample()
        if sample is not None:
            item = self.table.item(row, self._sample_column(sample))
            if item is None or not item.data(PRESENT_ROLE):
                self.value_edit.clear()
            else:
                value = item.data(VALUE_ROLE)
                self.value_edit.setText("" if value is None else str(value))
            return

        representative = self._representative_row_value(row)
        self.value_edit.setText("" if representative is None else str(representative))

    def _on_cell_double_clicked(self, row: int, column: int) -> None:
        if column < 2 or column >= self.table.columnCount():
            return

        sample = self._samples[column - 2]
        self.target_combo.setCurrentText(sample)
        self.table.selectRow(row)

    def _representative_row_value(self, row: int) -> DictTagValue | None:
        values: list[DictTagValue] = []
        for sample in self._samples:
            item = self.table.item(row, self._sample_column(sample))
            if item is None or not item.data(PRESENT_ROLE):
                continue
            values.append(item.data(VALUE_ROLE))
        if not values:
            return None
        first = values[0]
        if all(value == first for value in values):
            return first
        return None

    def _on_target_changed(self, text: str) -> None:
        self._populate_inputs_from_selection()
        self.evt_target_changed.emit(text)

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

    def _infer_row_type(self, values) -> str:
        for value in values:
            if value is not None:
                return self._infer_type(value)
        return "None"

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
        self.evt_items_changed.emit(self.export_dicts())

    def _resize_columns(self) -> None:
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.table.resizeColumnToContents(1)
        self.table.setColumnWidth(1, max(88, self.table.columnWidth(1) + 12))
        for column in range(2, self.table.columnCount()):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
            self.table.resizeColumnToContents(column)
            self.table.setColumnWidth(column, max(110, self.table.columnWidth(column) + 12))

    # Alias methods to offer a Qt-like interface
    setItems = set_items
    getItems = items
    exportDicts = export_dicts
    setSamples = set_samples
    getSampleNames = sample_names
    addKey = add_key
    addCurrentKey = add_current_key
    setValue = set_value
    applyCurrentValue = apply_current_value
    removeKey = remove_key
    removeSelectedKey = remove_selected_key
    clearItems = clear_items
    confirmClearItems = confirm_clear_items
    getValue = get_value
