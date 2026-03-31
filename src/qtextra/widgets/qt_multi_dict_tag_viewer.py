"""Multi-dictionary tag viewer widget."""

from __future__ import annotations

from collections.abc import Mapping

from qtpy.QtCore import Qt, Signal
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
from qtextra.widgets.qt_dict_tag_editor import DictTagValue

VALUE_ROLE = Qt.ItemDataRole.UserRole + 1
PRESENT_ROLE = Qt.ItemDataRole.UserRole + 2


class QtMultiDictTagViewer(QWidget):
    """Read-only searchable viewer for multiple dictionaries."""

    evt_items_changed = Signal(dict)
    evt_search_changed = Signal(str)

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        samples: list[str] | None = None,
        search_placeholder: str = "Search...",
        case_sensitive: bool = False,
    ) -> None:
        super().__init__(parent)
        self.case_sensitive = case_sensitive
        self._samples: list[str] = []
        self._syncing_selection = False
        self._syncing_scroll = False
        self._sort_key: tuple[str, int] = ("key", 0)
        self._sort_order = Qt.SortOrder.AscendingOrder

        self.search_edit = hp.make_line_edit(self, placeholder=search_placeholder, func_changed=self._on_search_changed)

        self.key_table = QTableWidget(0, 1, self)
        self.key_table.setHorizontalHeaderLabels(["Key"])
        self.key_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._configure_table(self.key_table)

        self.table = QTableWidget(0, 0, self)
        self.table.setSizeAdjustPolicy(QAbstractScrollArea.SizeAdjustPolicy.AdjustIgnored)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._configure_table(self.table)

        self.key_table.itemSelectionChanged.connect(self._on_key_selection_changed)
        self.table.itemSelectionChanged.connect(self._on_sample_selection_changed)
        self.key_table.verticalScrollBar().valueChanged.connect(self._sync_scroll_from_key_table)
        self.table.verticalScrollBar().valueChanged.connect(self._sync_scroll_from_sample_table)
        self.key_table.horizontalHeader().sortIndicatorChanged.connect(self._on_key_sort_requested)
        self.table.horizontalHeader().sortIndicatorChanged.connect(self._on_sample_sort_requested)

        hp.make_v_layout(
            hp.make_h_layout(self.search_edit, spacing=4, margin=0),
            hp.make_h_layout(self.key_table, self.table, spacing=0, margin=0, stretch_id=(0,)),
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
        """Export the displayed nested dictionaries."""
        return self.items()

    def set_samples(self, samples: list[str]) -> None:
        """Set the active sample names."""
        self._samples = [sample.strip() for sample in samples if sample.strip()]
        self._rebuild_table_headers()
        self._resize_columns()

    def set_items(self, items: Mapping[str, Mapping[str, DictTagValue]]) -> None:
        """Replace all displayed sample dictionaries."""
        self.set_samples(list(items))
        self.key_table.setRowCount(0)
        self.table.setRowCount(0)

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
            for sample in self._samples:
                if key in items[sample]:
                    self._set_sample_value(row, sample, items[sample][key], present=True)
                else:
                    matched_key = self._find_key_in_sample(items[sample], key)
                    if matched_key is not None:
                        self._set_sample_value(row, sample, items[sample][matched_key], present=True)

        self._apply_sort()
        self._apply_filter()
        self._resize_columns()
        self.evt_items_changed.emit(self.export_dicts())

    def clear_items(self) -> None:
        """Clear all rows."""
        self.key_table.setRowCount(0)
        self.table.setRowCount(0)
        self.evt_items_changed.emit({sample: {} for sample in self._samples})

    def get_value(self, key: str, sample: str) -> DictTagValue:
        """Return the value for a key in a sample."""
        row = self._find_row(key)
        if row is None:
            raise KeyError(key)
        if sample not in self._samples:
            raise KeyError(sample)
        item = self.table.item(row, self._sample_column(sample))
        if item is None or not item.data(PRESENT_ROLE):
            raise KeyError(f"{sample}:{key}")
        return item.data(VALUE_ROLE)

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
        self.key_table.setColumnCount(1)
        self.key_table.setHorizontalHeaderLabels(["Key"])
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

    def _key_id(self, text: str) -> str:
        normalized = text.strip()
        return normalized if self.case_sensitive else normalized.casefold()

    def _format_value(self, value: DictTagValue) -> str:
        return "None" if value is None else str(value)

    def _set_sample_value(self, row: int, sample: str, value: DictTagValue, *, present: bool) -> None:
        column = self._sample_column(sample)
        item = self.table.item(row, column)
        if item is None:
            item = QTableWidgetItem("")
            self.table.setItem(row, column, item)
        item.setData(PRESENT_ROLE, present)
        item.setData(VALUE_ROLE, value)
        item.setText("" if not present else self._format_value(value))

    def _on_search_changed(self, text: str) -> None:
        if text.strip():
            self._apply_filter(text)
        else:
            self._apply_sort()
        self.evt_search_changed.emit(text)

    def _apply_filter(self, text: str | None = None) -> None:
        query = self.search_edit.text() if text is None else text
        normalized = query.strip().casefold()
        for row in range(self.table.rowCount()):
            values = []
            key_item = self.key_table.item(row, 0)
            if key_item is not None:
                values.append(key_item.text())
            for column in range(self.table.columnCount()):
                item = self.table.item(row, column)
                if item is not None:
                    values.append(item.text())
            hidden = bool(normalized and normalized not in " ".join(values).casefold())
            self.key_table.setRowHidden(row, hidden)
            self.table.setRowHidden(row, hidden)

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
        row = self.key_table.currentRow()
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
        return {"key": "" if key_item is None else key_item.text(), "values": values}

    def _restore_rows(self, rows: list[dict]) -> None:
        self.key_table.setRowCount(0)
        self.table.setRowCount(0)
        for row_data in rows:
            row = self._ensure_row(row_data["key"])
            for sample, (present, value) in row_data["values"].items():
                self._set_sample_value(row, sample, value, present=present)

    def _sort_value(self, row_data: dict):
        table_name, section = self._sort_key
        if table_name == "key":
            return row_data["key"].casefold()

        sample = self._samples[section]
        present, value = row_data["values"][sample]
        if not present:
            return (1, "")
        return (0, "" if value is None else str(value).casefold())

    def _resize_columns(self) -> None:
        self.key_table.resizeRowsToContents()
        self.table.resizeRowsToContents()
        for row in range(self.key_table.rowCount()):
            height = max(self.key_table.rowHeight(row), self.table.rowHeight(row))
            self.key_table.setRowHeight(row, height)
            self.table.setRowHeight(row, height)

        key_header = self.key_table.horizontalHeader()
        key_header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.key_table.resizeColumnToContents(0)
        self.key_table.setColumnWidth(0, max(140, self.key_table.columnWidth(0) + 16))
        self.key_table.setFixedWidth(
            self.key_table.verticalHeader().width()
            + self.key_table.columnWidth(0)
            + self.key_table.frameWidth() * 2
            + 2,
        )

        sample_header = self.table.horizontalHeader()
        for column in range(self.table.columnCount()):
            sample_header.setSectionResizeMode(column, QHeaderView.ResizeMode.Fixed)
            self.table.resizeColumnToContents(column)
            self.table.setColumnWidth(column, max(110, self.table.columnWidth(column) + 12))

    setItems = set_items
    getItems = items
    exportDicts = export_dicts
    clearItems = clear_items
    setSamples = set_samples
    getSampleNames = sample_names
    getValue = get_value
