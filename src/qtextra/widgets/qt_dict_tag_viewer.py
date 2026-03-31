"""Dictionary tag viewer widget."""

from __future__ import annotations

from collections.abc import Mapping

from qtpy.QtCore import Qt, Signal
from qtpy.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
)

import qtextra.helpers as hp
from qtextra.widgets.qt_dict_tag_editor import DictTagValue

VALUE_ROLE = Qt.ItemDataRole.UserRole + 1


class QtDictTagViewer(QWidget):
    """Read-only searchable viewer for dictionary values."""

    evt_items_changed = Signal(dict)
    evt_search_changed = Signal(str)

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        search_placeholder: str = "Search...",
        case_sensitive: bool = False,
    ) -> None:
        super().__init__(parent)
        self.case_sensitive = case_sensitive

        self.search_edit = hp.make_line_edit(self, placeholder=search_placeholder, func_changed=self._on_search_changed)

        self.table = QTableWidget(0, 2, self)
        self.table.setHorizontalHeaderLabels(["Key", "Value"])
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSortingEnabled(False)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setMinimumSectionSize(80)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionsClickable(True)
        self.table.horizontalHeader().setSortIndicatorShown(True)

        hp.make_v_layout(
            hp.make_h_layout(self.search_edit, spacing=4, margin=0),
            self.table,
            spacing=6,
            margin=0,
            parent=self,
        )
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.table.horizontalHeader().sortIndicatorChanged.connect(self._on_sort_requested)
        self._sort_column = 0
        self._sort_order = Qt.SortOrder.AscendingOrder

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
        """Export the displayed dictionary."""
        return self.items()

    def set_items(self, items: Mapping[str, DictTagValue]) -> None:
        """Replace all displayed items."""
        self.table.setRowCount(0)
        for key, value in items.items():
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(key))
            value_item = QTableWidgetItem(self._format_value(value))
            value_item.setData(VALUE_ROLE, value)
            self.table.setItem(row, 1, value_item)
        self._apply_sort()
        self._apply_filter()
        self._resize_columns()
        self.evt_items_changed.emit(self.export_dict())

    def clear_items(self) -> None:
        """Clear all rows."""
        self.table.setRowCount(0)
        self.evt_items_changed.emit({})

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

    def _find_row(self, key: str) -> int | None:
        normalized = self._key_id(key)
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item is not None and self._key_id(item.text()) == normalized:
                return row
        return None

    def _key_id(self, text: str) -> str:
        normalized = text.strip()
        return normalized if self.case_sensitive else normalized.casefold()

    def _format_value(self, value: DictTagValue) -> str:
        return "None" if value is None else str(value)

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
            key_text = self.table.item(row, 0).text() if self.table.item(row, 0) else ""
            value_text = self.table.item(row, 1).text() if self.table.item(row, 1) else ""
            haystack = f"{key_text} {value_text}".casefold()
            self.table.setRowHidden(row, bool(normalized and normalized not in haystack))

    def _on_sort_requested(self, section: int, order: Qt.SortOrder) -> None:
        self._sort_column = section
        self._sort_order = order
        self._apply_sort()

    def _apply_sort(self) -> None:
        rows = []
        for row in range(self.table.rowCount()):
            key_item = self.table.item(row, 0)
            value_item = self.table.item(row, 1)
            rows.append(
                {
                    "key": "" if key_item is None else key_item.text(),
                    "value_text": "" if value_item is None else value_item.text(),
                    "value": None if value_item is None else value_item.data(VALUE_ROLE),
                },
            )
        reverse = self._sort_order == Qt.SortOrder.DescendingOrder
        rows.sort(
            key=lambda row_data: (
                row_data["key"].casefold() if self._sort_column == 0 else row_data["value_text"].casefold()
            ),
            reverse=reverse,
        )
        self.table.setRowCount(0)
        for row_data in rows:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(row_data["key"]))
            value_item = QTableWidgetItem(row_data["value_text"])
            value_item.setData(VALUE_ROLE, row_data["value"])
            self.table.setItem(row, 1, value_item)
        self._apply_filter()
        self._resize_columns()

    def _resize_columns(self) -> None:
        self.table.resizeColumnToContents(0)
        self.table.setColumnWidth(0, max(120, self.table.columnWidth(0) + 16))

    setItems = set_items
    getItems = items
    exportDict = export_dict
    clearItems = clear_items
    hasItem = has_item
    getValue = get_value
