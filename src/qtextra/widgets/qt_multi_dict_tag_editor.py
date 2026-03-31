"""Multi-dictionary tag editor widget."""

from __future__ import annotations

from collections.abc import Mapping

from qtpy.QtCore import Qt, Signal
from qtpy.QtGui import QDoubleValidator, QIntValidator
from qtpy.QtWidgets import (
    QAbstractItemView,
    QAbstractScrollArea,
    QHeaderView,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
)

import qtextra.helpers as hp
from qtextra.widgets.qt_combobox_multi import QtMultiSelectComboBox
from qtextra.widgets.qt_dict_tag_editor import DictTagValue

TYPE_ROLE = Qt.ItemDataRole.UserRole + 1
VALUE_ROLE = Qt.ItemDataRole.UserRole + 2
PRESENT_ROLE = Qt.ItemDataRole.UserRole + 3


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
        self._selected_target_samples: list[str] = []
        self._syncing_selection = False
        self._syncing_scroll = False
        self._sort_key: tuple[str, int] = ("key", 0)
        self._sort_order = Qt.SortOrder.AscendingOrder

        self.search_edit = hp.make_line_edit(self, placeholder=search_placeholder, func_changed=self._on_search_changed)
        self.key_edit = hp.make_line_edit(self, placeholder=key_placeholder, func_enter=self.add_current_key)
        self.value_edit = hp.make_line_edit(self, placeholder=value_placeholder, func_enter=self.apply_current_value)

        self.type_toggle = hp.make_toggle(
            self,
            "str",
            "int",
            "float",
            "None",
            value="str",
            orientation="horizontal",
            func=self._on_type_changed,
        )

        self.sample_combo = QtMultiSelectComboBox(parent=self, placeholder="Select target samples...")
        self.sample_combo.evt_selection_changed.connect(self._on_sample_selection_changed_from_combo)

        self.all_samples_button = hp.make_btn(self, "Select All", func=self.select_all_samples)

        self.target_summary = hp.make_label(self, "", wrap=True)
        self.target_summary.setMinimumHeight(self.key_edit.sizeHint().height())

        self.add_key_button = hp.make_btn(self, "Add Key", func=self.add_current_key)
        self.apply_value_button = hp.make_btn(self, "Apply Value", func=self.apply_current_value)
        self.remove_key_button = hp.make_btn(self, "Remove Key", func=self.remove_selected_key)
        self.clear_button = hp.make_btn(self, "Clear", func=self.confirm_clear_items)

        self._on_type_changed(self.current_value_type())

        self.key_table = QTableWidget(0, 2, self)
        self.key_table.setHorizontalHeaderLabels(["Key", "Type"])
        self.key_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._configure_table(self.key_table)

        self.table = QTableWidget(0, 0, self)
        self.table.setSizeAdjustPolicy(QAbstractScrollArea.SizeAdjustPolicy.AdjustIgnored)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._configure_table(self.table)

        self.key_table.itemSelectionChanged.connect(self._on_key_selection_changed)
        self.table.itemSelectionChanged.connect(self._on_sample_selection_changed)
        self.table.cellDoubleClicked.connect(self._on_cell_double_clicked)

        self.key_table.verticalScrollBar().valueChanged.connect(self._sync_scroll_from_key_table)
        self.table.verticalScrollBar().valueChanged.connect(self._sync_scroll_from_sample_table)

        self.key_table.horizontalHeader().sortIndicatorChanged.connect(self._on_key_sort_requested)
        self.table.horizontalHeader().sortIndicatorChanged.connect(self._on_sample_sort_requested)

        search_row = hp.make_h_layout(self.search_edit, spacing=4, margin=0)
        editor_row = hp.make_h_layout(
            self.key_edit,
            self.value_edit,
            self.type_toggle,
            spacing=4,
            margin=0,
            stretch_id=(0, 1),
            stretch_ratio=(2, 2),
        )

        target_layout = hp.make_h_layout(
            self.sample_combo,
            self.all_samples_button,
            spacing=0,
            margin=0,
            stretch_id=(0,),
        )
        buttons_row = hp.make_h_layout(
            self.add_key_button,
            self.apply_value_button,
            self.remove_key_button,
            self.clear_button,
            spacing=4,
            margin=0,
        )
        tables_row = hp.make_h_layout(self.key_table, self.table, spacing=0, margin=0, stretch_id=(0,))

        hp.make_v_layout(
            search_row,
            editor_row,
            target_layout,
            self.target_summary,
            buttons_row,
            tables_row,
            spacing=6,
            margin=0,
            parent=self,
        )
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.set_samples(samples or [])
        self._resize_columns()

    def sample_names(self) -> list[str]:
        """Return the configured sample names."""
        return list(self._samples)

    def current_value_type(self) -> str:
        """Return the currently selected value type."""
        value = self.type_toggle.value
        return "str" if not isinstance(value, str) else value

    def set_current_value_type(self, value_type: str) -> None:
        """Set the current value type and refresh validation."""
        self.type_toggle.value = value_type
        self._on_type_changed(value_type)

    def set_samples(self, samples: list[str]) -> None:
        """Set the active sample names."""
        cleaned = [sample.strip() for sample in samples if sample.strip()]
        self._samples = cleaned
        self.sample_combo.set_items(self._samples)
        self.set_target_samples(list(self._samples))
        self._rebuild_table_headers()
        self._resize_columns()

    def items(self) -> dict[str, dict[str, DictTagValue]]:
        """Return the current sample dictionaries."""
        exported = {sample: {} for sample in self._samples}
        for row in range(self.table.rowCount()):
            key_item = self.key_table.item(row, 0)
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

        self._apply_sort()
        self._apply_filter()
        self._resize_columns()
        self._emit_items_changed()

    def add_key(
        self,
        key: str,
        value: DictTagValue = None,
        *,
        target_sample: str | None = None,
        target_samples: list[str] | None = None,
        value_type: str | None = None,
    ) -> bool:
        """Add a key to one sample or all samples."""
        display_key = key.strip()
        if not display_key:
            return False
        if value is not None and not isinstance(value, (str, int, float)):
            raise TypeError("Value must be str, int, float, or None.")

        row = self._ensure_row(display_key)
        samples = self._target_samples(target_sample=target_sample, target_samples=target_samples)
        if not samples:
            return False

        value_type = self._infer_type(value) if value_type is None else value_type
        self._set_row_type(row, value_type)
        for sample in samples:
            self._set_sample_value(row, sample, value, present=True)

        self._apply_sort()
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
        target_samples: list[str] | None = None,
        value_type: str | None = None,
    ) -> bool:
        """Set a value for a key in one sample or all samples."""
        if value is not None and not isinstance(value, (str, int, float)):
            raise TypeError("Value must be str, int, float, or None.")

        row = self._find_row(key)
        if row is None:
            return False

        samples = self._target_samples(target_sample=target_sample, target_samples=target_samples)
        if not samples:
            return False

        value_type = self._infer_type(value) if value_type is None else value_type
        self._set_row_type(row, value_type)
        display_key = self.key_table.item(row, 0).text() if self.key_table.item(row, 0) else key.strip()
        for sample in samples:
            self._set_sample_value(row, sample, value, present=True)
            self.evt_value_changed.emit(display_key, sample, value)

        self._apply_sort()
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
            value = self._coerce_value(self.value_edit.text(), self.current_value_type())
        except ValueError:
            return False
        added = self.add_key(
            key,
            value,
            target_samples=self.current_target_samples(),
            value_type=self.current_value_type(),
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
            row = self._current_row()
            if row < 0:
                return False
            item = self.key_table.item(row, 0)
            if item is None:
                return False
            key = item.text()

        try:
            value = self._coerce_value(self.value_edit.text(), self.current_value_type())
        except ValueError:
            return False

        return self.set_value(
            key,
            value,
            target_samples=self.current_target_samples(),
            value_type=self.current_value_type(),
        )

    def remove_key(self, key: str) -> bool:
        """Remove a key from all samples."""
        row = self._find_row(key)
        if row is None:
            return False
        key_item = self.key_table.item(row, 0)
        display_key = "" if key_item is None else key_item.text()
        self.key_table.removeRow(row)
        self.table.removeRow(row)
        self.evt_key_removed.emit(display_key)
        self._emit_items_changed()
        return True

    def remove_selected_key(self) -> bool:
        """Remove the selected key row."""
        row = self._current_row()
        if row < 0:
            return False
        key_item = self.key_table.item(row, 0)
        if key_item is None:
            return False
        return self.remove_key(key_item.text())

    def clear_items(self, emit_signal: bool = True) -> None:
        """Remove all keys from all samples."""
        self.key_table.setRowCount(0)
        self.table.setRowCount(0)
        self.key_table.clearSelection()
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
        """Return the current target sample when exactly one sample is selected."""
        selected = self.current_target_samples()
        if len(selected) != 1:
            return None
        return selected[0]

    def current_target_samples(self) -> list[str]:
        """Return the currently selected target samples."""
        if len(self._selected_target_samples) == len(self._samples):
            return list(self._samples)
        return list(self._selected_target_samples)

    def set_target_samples(self, samples: list[str]) -> None:
        """Set the selected target samples."""
        cleaned = [sample for sample in samples if sample in self._samples]
        if not cleaned and self._samples:
            cleaned = list(self._samples)
        self._selected_target_samples = list(cleaned)
        self.sample_combo.set_selected(list(cleaned))
        self._refresh_target_summary()
        self._update_target_controls()
        self._on_target_changed()

    def select_all_samples(self) -> None:
        """Select every configured sample in the target picker."""
        self._selected_target_samples = list(self._samples)
        self.sample_combo.set_selected(list(self._samples))
        self._refresh_target_summary()
        self._update_target_controls()
        self._on_target_changed()

    def _configure_table(self, table: QTableWidget) -> None:
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSortingEnabled(False)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setMinimumSectionSize(70)
        table.horizontalHeader().setSectionsClickable(True)
        table.horizontalHeader().setSortIndicatorShown(True)
        table.setWordWrap(False)
        table.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        table.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def _rebuild_table_headers(self) -> None:
        self.key_table.setColumnCount(2)
        self.key_table.setHorizontalHeaderLabels(["Key", "Type"])
        self.table.setColumnCount(len(self._samples))
        self.table.setHorizontalHeaderLabels(self._samples)
        self.key_table.horizontalHeader().setSortIndicator(0, self._sort_order)
        if self.table.columnCount():
            self.table.horizontalHeader().setSortIndicator(0, self._sort_order)

    def _sample_column(self, sample: str) -> int:
        return self._samples.index(sample)

    def _ensure_row(self, key: str) -> int:
        row = self._find_row(key)
        if row is not None:
            return row

        row = self.key_table.rowCount()
        self.key_table.insertRow(row)
        self.table.insertRow(row)
        self.key_table.setItem(row, 0, QTableWidgetItem(key.strip()))
        self.key_table.setItem(row, 1, QTableWidgetItem("None"))
        for sample in self._samples:
            self.table.setItem(row, self._sample_column(sample), QTableWidgetItem(""))
            self._set_sample_value(row, sample, None, present=False)
        return row

    def _find_row(self, key: str) -> int | None:
        normalized = self._key_id(key)
        for row in range(self.key_table.rowCount()):
            item = self.key_table.item(row, 0)
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
                    key_item = self.key_table.item(row, 0)
                    if key_item is not None:
                        self.evt_value_changed.emit(key_item.text(), sample, values[sample])

    def _set_row_type(self, row: int, value_type: str) -> None:
        type_item = self.key_table.item(row, 1)
        if type_item is None:
            type_item = QTableWidgetItem(value_type)
            self.key_table.setItem(row, 1, type_item)
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

    def _target_samples(
        self,
        *,
        target_sample: str | None = None,
        target_samples: list[str] | None = None,
    ) -> list[str]:
        if target_samples is not None:
            selected = [sample for sample in target_samples if sample in self._samples]
            if not selected or len(selected) == len(self._samples):
                return list(self._samples)
            return selected
        if target_sample is None:
            return list(self._samples)
        if target_sample not in self._samples:
            return list(self._samples)
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
            for column in range(self.key_table.columnCount()):
                item = self.key_table.item(row, column)
                if item is not None:
                    values.append(item.text())
            for column in range(self.table.columnCount()):
                item = self.table.item(row, column)
                if item is not None:
                    values.append(item.text())
            hidden = bool(normalized and normalized not in " ".join(values).casefold())
            self.key_table.setRowHidden(row, hidden)
            self.table.setRowHidden(row, hidden)

    def _populate_inputs_from_selection(self) -> None:
        row = self._current_row()
        if row < 0:
            return

        key_item = self.key_table.item(row, 0)
        type_item = self.key_table.item(row, 1)
        if key_item is None or type_item is None:
            return

        self.key_edit.setText(key_item.text())
        self.set_current_value_type(type_item.text())

        samples = self.current_target_samples()
        if len(samples) == 1:
            item = self.table.item(row, self._sample_column(samples[0]))
            if item is None or not item.data(PRESENT_ROLE):
                self.value_edit.clear()
            else:
                value = item.data(VALUE_ROLE)
                self.value_edit.setText("" if value is None else str(value))
            return

        representative = self._representative_row_value(row, samples)
        self.value_edit.setText("" if representative is None else str(representative))

    def _on_key_selection_changed(self) -> None:
        self._select_row(self.key_table.currentRow(), source="key")

    def _on_sample_selection_changed(self) -> None:
        self._select_row(self.table.currentRow(), source="sample")

    def _select_row(self, row: int, *, source: str) -> None:
        if row < 0 or self._syncing_selection:
            return
        self._syncing_selection = True
        if source != "key":
            self.key_table.selectRow(row)
        if source != "sample":
            self.table.selectRow(row)
        self._syncing_selection = False
        self._populate_inputs_from_selection()

    def _current_row(self) -> int:
        row = self.key_table.currentRow()
        if row >= 0:
            return row
        return self.table.currentRow()

    def _on_cell_double_clicked(self, row: int, column: int) -> None:
        if column < 0 or column >= self.table.columnCount():
            return
        self.set_target_samples([self._samples[column]])
        self._select_row(row, source="sample")

    def _representative_row_value(self, row: int, samples: list[str] | None = None) -> DictTagValue | None:
        if samples is None:
            samples = list(self._samples)
        values: list[DictTagValue] = []
        for sample in samples:
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

    def _on_sample_selection_changed_from_combo(self, samples: list[str]) -> None:
        cleaned = [sample for sample in samples if sample in self._samples]
        self._selected_target_samples = cleaned
        self._refresh_target_summary()
        self._update_target_controls()
        self._on_target_changed()

    def _refresh_target_summary(self) -> None:
        if self._samples and len(self._selected_target_samples) == len(self._samples):
            self.target_summary.setText("Targets: All samples")
            return
        if not self._selected_target_samples:
            self.target_summary.setText("Targets: none")
            return
        self.target_summary.setText(f"Targets: {', '.join(self._selected_target_samples)}")

    def _update_target_controls(self) -> None:
        self.target_summary.setEnabled(True)

    def _on_target_changed(self) -> None:
        self._populate_inputs_from_selection()
        selected = self.current_target_samples()
        if len(selected) == len(self._samples):
            self.evt_target_changed.emit("All samples")
        else:
            self.evt_target_changed.emit(", ".join(selected))

    def _sync_scroll_from_key_table(self, value: int) -> None:
        if self._syncing_scroll:
            return
        self._syncing_scroll = True
        self.table.verticalScrollBar().setValue(value)
        self._syncing_scroll = False

    def _sync_scroll_from_sample_table(self, value: int) -> None:
        if self._syncing_scroll:
            return
        self._syncing_scroll = True
        self.key_table.verticalScrollBar().setValue(value)
        self._syncing_scroll = False

    def _on_key_sort_requested(self, section: int, order: Qt.SortOrder) -> None:
        self._sort_key = ("key", section)
        self._sort_order = order
        self._apply_sort()

    def _on_sample_sort_requested(self, section: int, order: Qt.SortOrder) -> None:
        self._sort_key = ("sample", section)
        self._sort_order = order
        self._apply_sort()

    def _apply_sort(self) -> None:
        selected_key = None
        row = self._current_row()
        if row >= 0 and self.key_table.item(row, 0) is not None:
            selected_key = self.key_table.item(row, 0).text()

        rows = [self._row_snapshot(index) for index in range(self.key_table.rowCount())]
        reverse = self._sort_order == Qt.SortOrder.DescendingOrder
        rows.sort(key=self._sort_value, reverse=reverse)
        self._restore_rows(rows)

        if selected_key:
            new_row = self._find_row(selected_key)
            if new_row is not None:
                self._select_row(new_row, source="key")
        self._apply_filter()
        self._resize_columns()

    def _row_snapshot(self, row: int) -> dict:
        values: dict[str, tuple[bool, DictTagValue]] = {}
        for sample in self._samples:
            item = self.table.item(row, self._sample_column(sample))
            present = False if item is None else bool(item.data(PRESENT_ROLE))
            value = None if item is None else item.data(VALUE_ROLE)
            values[sample] = (present, value)
        key_item = self.key_table.item(row, 0)
        type_item = self.key_table.item(row, 1)
        return {
            "key": "" if key_item is None else key_item.text(),
            "type": "None" if type_item is None else type_item.text(),
            "values": values,
        }

    def _restore_rows(self, rows: list[dict]) -> None:
        self.key_table.setRowCount(0)
        self.table.setRowCount(0)
        for row_data in rows:
            row = self._ensure_row(row_data["key"])
            self._set_row_type(row, row_data["type"])
            for sample, (present, value) in row_data["values"].items():
                self._set_sample_value(row, sample, value, present=present)

    def _sort_value(self, row_data: dict):
        table_name, section = self._sort_key
        if table_name == "key":
            if section == 0:
                return row_data["key"].casefold()
            return row_data["type"].casefold()

        sample = self._samples[section]
        present, value = row_data["values"][sample]
        if not present:
            return (1, "")
        return (0, "" if value is None else str(value).casefold())

    @staticmethod
    def _coerce_value(text: str, value_type: str) -> DictTagValue:
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

    @staticmethod
    def _infer_type(value: DictTagValue) -> str:
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
        self.key_table.resizeRowsToContents()
        self.table.resizeRowsToContents()
        for row in range(self.key_table.rowCount()):
            height = max(self.key_table.rowHeight(row), self.table.rowHeight(row))
            self.key_table.setRowHeight(row, height)
            self.table.setRowHeight(row, height)

        key_header = self.key_table.horizontalHeader()
        key_header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        key_header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.key_table.resizeColumnToContents(0)
        self.key_table.resizeColumnToContents(1)
        self.key_table.setColumnWidth(0, max(120, self.key_table.columnWidth(0) + 16))
        self.key_table.setColumnWidth(1, max(88, self.key_table.columnWidth(1) + 12))
        self.key_table.setFixedWidth(
            self.key_table.verticalHeader().width()
            + self.key_table.columnWidth(0)
            + self.key_table.columnWidth(1)
            + self.key_table.frameWidth() * 2
            + 2,
        )

        sample_header = self.table.horizontalHeader()
        for column in range(self.table.columnCount()):
            sample_header.setSectionResizeMode(column, QHeaderView.ResizeMode.Fixed)
            self.table.resizeColumnToContents(column)
            self.table.setColumnWidth(column, max(110, self.table.columnWidth(column) + 12))

    # Alias methods to offer a Qt-like interface
    setItems = set_items
    getItems = items
    exportDicts = export_dicts
    setSamples = set_samples
    getSampleNames = sample_names
    setTargetSamples = set_target_samples
    getTargetSamples = current_target_samples
    setCurrentValueType = set_current_value_type
    addKey = add_key
    addCurrentKey = add_current_key
    setValue = set_value
    applyCurrentValue = apply_current_value
    removeKey = remove_key
    removeSelectedKey = remove_selected_key
    clearItems = clear_items
    confirmClearItems = confirm_clear_items
    getValue = get_value
