# ruff: noqa: D102
"""
Defines the DataFrameViewer class to display DataFrames as a table. The DataFrameViewer is made up of three separate
QTableWidgets... DataTableView for the DataFrame's contents, and two HeaderView widgets for the column and index
 headers.
"""

from __future__ import annotations

import contextlib
import io
import typing as ty
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
import qtpy.QtCore as Qc
import qtpy.QtGui as Qg
import qtpy.QtWidgets as Qw
from loguru import logger
from qtpy.QtCore import Qt

from qtextra.widgets._qt_table_models import BaseTabularTableModel, is_float_like

try:
    import polars as pl
except ImportError:  # pragma: no cover - optional dependency
    pl = None

AUTO_SIZE_SAMPLE = 100
AUTO_SIZE_COLUMN_LIMIT = 200
AUTO_SIZE_ROW_LIMIT = 200
DEFAULT_COLUMN_WIDTH = 120
DEFAULT_ROW_HEIGHT = 30
MAX_COLUMN_WIDTH = 500
MAX_ROW_HEIGHT = 100
HEADER_PADDING = 20
ROW_PADDING = 5
MAX_VERTICAL_SPAN_ROWS = 5000
BLANK_FILTER_LABEL = "(Blank)"
ASCENDING_SORT_INDICATOR = " ▲"
DESCENDING_SORT_INDICATOR = " ▼"


def _sample_count(total: int, limit: int) -> int:
    """Return bounded sample size."""
    return min(total, limit)


def _text_width(metrics: Qg.QFontMetrics, text: str) -> int:
    """Measure text width."""
    return metrics.horizontalAdvance(text)


def _normalize_tabular_data(
    data: pd.DataFrame | pd.Series | ty.Any | None,
    *,
    inplace: bool = True,
) -> pd.DataFrame:
    """Normalize supported tabular inputs to a pandas DataFrame."""
    if data is None:
        return pd.DataFrame()
    if isinstance(data, pd.Series):
        data = data.to_frame()
    if isinstance(data, pd.DataFrame):
        return data if inplace else data.copy()
    if pl is not None:
        if isinstance(data, pl.Series):
            return pd.DataFrame({data.name or "column_0": data.to_list()})
        if isinstance(data, pl.DataFrame):
            try:
                return data.to_pandas()
            except ModuleNotFoundError:
                return pd.DataFrame(data.to_dicts(), columns=data.columns)
    msg = f"Unsupported tabular data type: {type(data)!r}"
    raise TypeError(msg)


def _column_label_to_text(label: ty.Any) -> str:
    """Return a readable column label."""
    if isinstance(label, tuple):
        return " / ".join(str(part) for part in label)
    return str(label)


def _row_label_to_text(label: ty.Any) -> str:
    """Return a readable row label."""
    if isinstance(label, tuple):
        return " / ".join(str(part) for part in label)
    return str(label)


def _is_numeric_series(series: pd.Series) -> bool:
    """Return whether a series should use numeric filtering."""
    return pd.api.types.is_numeric_dtype(series.dtype) and not pd.api.types.is_bool_dtype(series.dtype)


def _set_span_if_needed(
    view: Qw.QTableView,
    row: int,
    column: int,
    row_span: int,
    column_span: int,
) -> None:
    """Apply a span only when it covers more than one cell."""
    if row_span <= 1 and column_span <= 1:
        return
    view.setSpan(row, column, row_span, column_span)


@dataclass(slots=True)
class NumericColumnFilter:
    """Filter state for numeric columns."""

    minimum: float | None = None
    maximum: float | None = None
    include_blanks: bool = True

    def is_active(self) -> bool:
        """Return whether the filter affects visibility."""
        return self.minimum is not None or self.maximum is not None or not self.include_blanks


@dataclass(slots=True)
class StringColumnFilter:
    """Filter state for string-like columns."""

    allowed_values: set[str] = field(default_factory=set)
    include_blanks: bool = True

    def is_active(self) -> bool:
        """Return whether the filter affects visibility."""
        return bool(self.allowed_values) or not self.include_blanks


class DataFrameProxyModel(BaseTabularTableModel):
    """Proxy model that exposes the visible dataframe state."""

    def __init__(self, source_model: DataTableModel, parent: Qw.QWidget | None = None):
        super().__init__(parent, editable=source_model._editable)
        self.source_model = source_model
        self._visible_rows: list[int] = list(range(source_model.rowCount()))
        self._visible_columns: list[int] = list(range(source_model.columnCount()))
        self._hidden_source_rows: set[int] = set()
        self._column_filters: dict[int, NumericColumnFilter | StringColumnFilter] = {}
        self._sort_column: int | None = None
        self._sort_order: Qt.SortOrder | None = None
        self._refresh_mappings()

    @property
    def df(self) -> pd.DataFrame:
        """Return the source dataframe."""
        return self.source_model.df

    @property
    def sort_column(self) -> int | None:
        """Return the active source sort column."""
        return self._sort_column

    @property
    def sort_order(self) -> Qt.SortOrder | None:
        """Return the active sort order."""
        return self._sort_order

    @property
    def visible_rows(self) -> list[int]:
        """Return the visible source row positions."""
        return list(self._visible_rows)

    @property
    def visible_columns(self) -> list[int]:
        """Return the visible source column positions."""
        return list(self._visible_columns)

    def source_row(self, row: int) -> int:
        """Map a visible row to a source row."""
        return self._visible_rows[row]

    def source_column(self, column: int) -> int:
        """Map a visible column to a source column."""
        return self._visible_columns[column]

    def set_source_dataframe(self, df: pd.DataFrame) -> None:
        """Replace the source dataframe and reset proxy state."""
        self.source_model = DataTableModel(df)
        self.clear_state()

    def clear_state(self) -> None:
        """Reset sorting, filtering, and column visibility."""
        self._column_filters.clear()
        self._sort_column = None
        self._sort_order = None
        self._hidden_source_rows.clear()
        self._visible_columns = list(range(self.source_model.columnCount()))
        self._refresh_mappings()

    def clear_sorting(self) -> None:
        """Reset row sorting to the source order."""
        self._sort_column = None
        self._sort_order = None
        self._refresh_mappings()

    def clear_filters(self) -> None:
        """Remove all active column filters."""
        self._column_filters.clear()
        self._refresh_mappings()

    def clear_filter_for_column(self, column: int) -> None:
        """Remove the filter for a source column."""
        self._column_filters.pop(column, None)
        self._refresh_mappings()

    def toggle_sort(self, column: int) -> None:
        """Toggle sort state for a source column."""
        if self._sort_column != column:
            self._sort_column = column
            self._sort_order = Qt.SortOrder.AscendingOrder
        elif self._sort_order == Qt.SortOrder.AscendingOrder:
            self._sort_order = Qt.SortOrder.DescendingOrder
        else:
            self._sort_column = None
            self._sort_order = None
        self._refresh_mappings()

    def set_sort(self, column: int, order: Qt.SortOrder | None) -> None:
        """Set sort state explicitly."""
        self._sort_column = column if order is not None else None
        self._sort_order = order
        self._refresh_mappings()

    def set_numeric_filter(
        self,
        column: int,
        *,
        minimum: float | None = None,
        maximum: float | None = None,
        include_blanks: bool = True,
    ) -> None:
        """Apply a numeric filter to a source column."""
        filter_state = NumericColumnFilter(minimum=minimum, maximum=maximum, include_blanks=include_blanks)
        if filter_state.is_active():
            self._column_filters[column] = filter_state
        else:
            self._column_filters.pop(column, None)
        self._refresh_mappings()

    def set_string_filter(
        self,
        column: int,
        *,
        allowed_values: ty.Iterable[str] | None = None,
        include_blanks: bool = True,
    ) -> None:
        """Apply a value-selection filter to a source column."""
        filter_state = StringColumnFilter(
            allowed_values={str(value) for value in (allowed_values or [])},
            include_blanks=include_blanks,
        )
        if filter_state.is_active():
            self._column_filters[column] = filter_state
        else:
            self._column_filters.pop(column, None)
        self._refresh_mappings()

    def is_column_filtered(self, column: int) -> bool:
        """Return whether a source column has an active filter."""
        filter_state = self._column_filters.get(column)
        return filter_state.is_active() if filter_state is not None else False

    def is_column_visible(self, column: int) -> bool:
        """Return whether a source column is visible."""
        return column in self._visible_columns

    def is_row_visible(self, row: int) -> bool:
        """Return whether a source row is visible."""
        return row not in self._hidden_source_rows

    def set_column_visible(self, column: int, visible: bool) -> bool:
        """Show or hide a source column."""
        if visible:
            if column not in self._visible_columns:
                self._visible_columns.append(column)
                self._visible_columns.sort()
                self._refresh_mappings(update_columns=False)
            return True

        if column not in self._visible_columns:
            return True
        if len(self._visible_columns) <= 1:
            return False
        self._visible_columns.remove(column)
        self._refresh_mappings(update_columns=False)
        return True

    def set_row_visible(self, row: int, visible: bool) -> bool:
        """Show or hide a source row."""
        if visible:
            if row in self._hidden_source_rows:
                self._hidden_source_rows.remove(row)
                self._refresh_mappings(update_columns=False)
            return True

        if row in self._hidden_source_rows:
            return True
        if row in self._visible_rows and len(self._visible_rows) <= 1:
            return False
        self._hidden_source_rows.add(row)
        self._refresh_mappings(update_columns=False)
        return True

    def distinct_values_for_column(self, column: int) -> list[str]:
        """Return visible distinct non-blank values for a source column."""
        rows = self._filtered_rows(exclude_column=column)
        series = self.df.iloc[rows, column] if rows else self.df.iloc[0:0, column]
        values = {str(value) for value in series if not pd.isna(value)}
        return sorted(values, key=str.casefold)

    def filter_state_for_column(self, column: int) -> NumericColumnFilter | StringColumnFilter | None:
        """Return the current filter state for a source column."""
        return self._column_filters.get(column)

    def _filtered_rows(self, exclude_column: int | None = None) -> list[int]:
        """Return source rows that pass the current filters."""
        if self.df.empty:
            return []

        mask = np.ones(self.df.shape[0], dtype=bool)
        for column, filter_state in self._column_filters.items():
            if column == exclude_column:
                continue
            series = self.df.iloc[:, column]
            if isinstance(filter_state, NumericColumnFilter):
                non_blank = ~series.isna().to_numpy()
                column_mask = np.ones(series.shape[0], dtype=bool)
                if filter_state.minimum is not None:
                    column_mask &= (series >= filter_state.minimum).fillna(False).to_numpy()
                if filter_state.maximum is not None:
                    column_mask &= (series <= filter_state.maximum).fillna(False).to_numpy()
                if filter_state.include_blanks:
                    column_mask |= ~non_blank
                else:
                    column_mask &= non_blank
            else:
                non_blank = ~series.isna().to_numpy()
                if filter_state.allowed_values:
                    column_mask = np.zeros(series.shape[0], dtype=bool)
                    non_blank_values = series[non_blank].astype(str)
                    column_mask[non_blank] = non_blank_values.isin(filter_state.allowed_values).to_numpy()
                else:
                    column_mask = np.ones(series.shape[0], dtype=bool)
                if filter_state.include_blanks:
                    column_mask |= ~non_blank
                else:
                    column_mask &= non_blank
            mask &= column_mask
        rows = np.flatnonzero(mask).tolist()
        return [row for row in rows if row not in self._hidden_source_rows]

    def _sorted_rows(self, rows: list[int]) -> list[int]:
        """Return rows in the current sort order."""
        if self._sort_column is None or self._sort_order is None or len(rows) <= 1:
            return rows

        series = self.df.iloc[rows, self._sort_column].reset_index(drop=True)
        sorted_positions = series.sort_values(
            ascending=self._sort_order == Qt.SortOrder.AscendingOrder,
            kind="mergesort",
            na_position="last",
        ).index.to_list()
        return [rows[position] for position in sorted_positions]

    def _refresh_mappings(self, *, update_columns: bool = True) -> None:
        """Recompute row and column mappings."""
        self.beginResetModel()
        if update_columns:
            self._visible_columns = [
                column for column in range(self.source_model.columnCount()) if column in self._visible_columns
            ]
        self._visible_rows = self._sorted_rows(self._filtered_rows())
        self.set_shape(len(self._visible_rows), len(self._visible_columns))
        self.endResetModel()

    def _value_at(self, row: int, column: int):
        """Return a visible cell value."""
        return self.source_model._value_at(self.source_row(row), self.source_column(column))

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        """Return mapped source data for supported roles."""
        if not index.isValid():
            return None
        source_index = self.source_model.index(self.source_row(index.row()), self.source_column(index.column()))
        return self.source_model.data(source_index, role)

    def _set_value_at(self, row: int, column: int, value) -> None:
        """Set a visible cell value in the source model."""
        self.source_model._set_value_at(self.source_row(row), self.source_column(column), value)

    def setData(self, index, value, role=None):
        """Set visible cell data and recompute proxy state."""
        if not index.isValid():
            return False
        source_index = self.source_model.index(self.source_row(index.row()), self.source_column(index.column()))
        if not self.source_model.setData(source_index, value, role):
            return False
        self._refresh_mappings(update_columns=False)
        return True


class NumericColumnFilterDialog(Qw.QDialog):
    """Dialog used to configure numeric filters."""

    def __init__(
        self,
        parent: Qw.QWidget | None,
        column_label: str,
        filter_state: NumericColumnFilter | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Filter {column_label}")
        self.setModal(True)

        self.minimum_edit = Qw.QLineEdit(self)
        self.maximum_edit = Qw.QLineEdit(self)
        self.include_blanks_checkbox = Qw.QCheckBox("Include blank values", self)
        self.include_blanks_checkbox.setChecked(True if filter_state is None else filter_state.include_blanks)

        if filter_state is not None:
            if filter_state.minimum is not None:
                self.minimum_edit.setText(str(filter_state.minimum))
            if filter_state.maximum is not None:
                self.maximum_edit.setText(str(filter_state.maximum))

        form_layout = Qw.QFormLayout()
        form_layout.addRow("Minimum", self.minimum_edit)
        form_layout.addRow("Maximum", self.maximum_edit)
        form_layout.addRow("", self.include_blanks_checkbox)

        button_box = Qw.QDialogButtonBox(
            Qw.QDialogButtonBox.StandardButton.Ok
            | Qw.QDialogButtonBox.StandardButton.Cancel
            | Qw.QDialogButtonBox.StandardButton.Reset,
            parent=self,
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        button_box.button(Qw.QDialogButtonBox.StandardButton.Reset).clicked.connect(self._clear_inputs)

        layout = Qw.QVBoxLayout(self)
        layout.addLayout(form_layout)
        layout.addWidget(button_box)

    def _clear_inputs(self) -> None:
        """Reset the dialog to an unfiltered state."""
        self.minimum_edit.clear()
        self.maximum_edit.clear()
        self.include_blanks_checkbox.setChecked(True)

    def filter_values(self) -> tuple[float | None, float | None, bool]:
        """Return the configured filter values."""
        minimum_text = self.minimum_edit.text().strip()
        maximum_text = self.maximum_edit.text().strip()
        minimum = float(minimum_text) if minimum_text else None
        maximum = float(maximum_text) if maximum_text else None
        return minimum, maximum, self.include_blanks_checkbox.isChecked()


class StringColumnFilterDialog(Qw.QDialog):
    """Dialog used to configure string filters."""

    def __init__(
        self,
        parent: Qw.QWidget | None,
        column_label: str,
        values: list[str],
        filter_state: StringColumnFilter | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Filter {column_label}")
        self.setModal(True)
        self._all_values = values

        self.search_edit = Qw.QLineEdit(self)
        self.search_edit.setPlaceholderText("Filter values...")
        self.search_edit.textChanged.connect(self._update_item_visibility)

        self.values_list = Qw.QListWidget(self)
        default_selected = (
            set(values) if filter_state is None or not filter_state.allowed_values else filter_state.allowed_values
        )
        for value in values:
            item = Qw.QListWidgetItem(value, self.values_list)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if value in default_selected else Qt.CheckState.Unchecked)

        self.include_blanks_checkbox = Qw.QCheckBox("Include blank values", self)
        self.include_blanks_checkbox.setChecked(True if filter_state is None else filter_state.include_blanks)

        buttons_layout = Qw.QHBoxLayout()
        select_all_button = Qw.QPushButton("Select all", self)
        select_all_button.clicked.connect(self._select_all)
        select_none_button = Qw.QPushButton("Select none", self)
        select_none_button.clicked.connect(self._select_none)
        buttons_layout.addWidget(select_all_button)
        buttons_layout.addWidget(select_none_button)

        button_box = Qw.QDialogButtonBox(
            Qw.QDialogButtonBox.StandardButton.Ok
            | Qw.QDialogButtonBox.StandardButton.Cancel
            | Qw.QDialogButtonBox.StandardButton.Reset,
            parent=self,
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        button_box.button(Qw.QDialogButtonBox.StandardButton.Reset).clicked.connect(self._reset_selection)

        layout = Qw.QVBoxLayout(self)
        layout.addWidget(self.search_edit)
        layout.addLayout(buttons_layout)
        layout.addWidget(self.values_list)
        layout.addWidget(self.include_blanks_checkbox)
        layout.addWidget(button_box)

    def _update_item_visibility(self, text: str) -> None:
        """Show only values that match the search text."""
        needle = text.strip().lower()
        for row in range(self.values_list.count()):
            item = self.values_list.item(row)
            item.setHidden(bool(needle) and needle not in item.text().lower())

    def _select_all(self) -> None:
        """Check every visible value."""
        for row in range(self.values_list.count()):
            item = self.values_list.item(row)
            item.setCheckState(Qt.CheckState.Checked)

    def _select_none(self) -> None:
        """Uncheck every visible value."""
        for row in range(self.values_list.count()):
            item = self.values_list.item(row)
            item.setCheckState(Qt.CheckState.Unchecked)

    def _reset_selection(self) -> None:
        """Reset the dialog to an unfiltered state."""
        self.search_edit.clear()
        self._select_all()
        self.include_blanks_checkbox.setChecked(True)

    def selected_values(self) -> tuple[set[str], bool]:
        """Return the configured string filter."""
        values: set[str] = set()
        for row in range(self.values_list.count()):
            item = self.values_list.item(row)
            if item.checkState() == Qt.CheckState.Checked:
                values.add(item.text())
        return values, self.include_blanks_checkbox.isChecked()


class ColumnVisibilityDialog(Qw.QDialog):
    """Dialog used to show or hide columns."""

    def __init__(self, parent: Qw.QWidget | None, proxy_model: DataFrameProxyModel):
        super().__init__(parent)
        self.setWindowTitle("Columns")
        self.setModal(True)
        self._items: dict[int, Qw.QListWidgetItem] = {}
        self._initial_visibility: dict[int, bool] = {}
        self.resize(360, 420)
        self.setSizeGripEnabled(True)

        layout = Qw.QVBoxLayout(self)
        self.search_edit = Qw.QLineEdit(self)
        self.search_edit.setPlaceholderText("Filter columns...")
        self.search_edit.textChanged.connect(self._update_item_visibility)
        layout.addWidget(self.search_edit)

        self.visibility_filter = Qw.QComboBox(self)
        self.visibility_filter.addItems(["All columns", "Visible columns", "Hidden columns"])
        self.visibility_filter.currentIndexChanged.connect(self._apply_filters)
        layout.addWidget(self.visibility_filter)

        self.columns_list = Qw.QListWidget(self)
        self.columns_list.setSelectionMode(Qw.QAbstractItemView.SelectionMode.NoSelection)
        self.columns_list.setUniformItemSizes(True)
        self.columns_list.setAlternatingRowColors(True)
        self.columns_list.setVerticalScrollMode(Qw.QAbstractItemView.ScrollMode.ScrollPerPixel)
        for column in range(proxy_model.df.columns.shape[0]):
            label = _column_label_to_text(proxy_model.df.columns[column])
            item = Qw.QListWidgetItem(label, self.columns_list)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            is_visible = proxy_model.is_column_visible(column)
            item.setCheckState(Qt.CheckState.Checked if is_visible else Qt.CheckState.Unchecked)
            item.setData(Qt.ItemDataRole.UserRole, column)
            self._items[column] = item
            self._initial_visibility[column] = is_visible
        self.columns_list.setMinimumHeight(220)
        layout.addWidget(self.columns_list, stretch=1)

        buttons_layout = Qw.QHBoxLayout()
        check_all_button = Qw.QPushButton("Check all", self)
        check_all_button.clicked.connect(self._check_all)
        uncheck_all_button = Qw.QPushButton("Uncheck all", self)
        uncheck_all_button.clicked.connect(self._uncheck_all)
        buttons_layout.addWidget(check_all_button)
        buttons_layout.addWidget(uncheck_all_button)
        layout.addLayout(buttons_layout)

        button_box = Qw.QDialogButtonBox(
            Qw.QDialogButtonBox.StandardButton.Ok | Qw.QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _update_item_visibility(self, text: str) -> None:
        """Show only column names that match the search text."""
        self._apply_filters(text)

    def _apply_filters(self, text: str | int = "") -> None:
        """Apply the current text and visibility filters to the list."""
        if isinstance(text, int):
            text = self.search_edit.text()
        needle = text.strip().lower()
        for row in range(self.columns_list.count()):
            item = self.columns_list.item(row)
            column = ty.cast(int, item.data(Qt.ItemDataRole.UserRole))
            is_visible_column = self._initial_visibility.get(column, True)
            visibility_mode = self.visibility_filter.currentText()
            visibility_match = True
            if visibility_mode == "Visible columns":
                visibility_match = is_visible_column
            elif visibility_mode == "Hidden columns":
                visibility_match = not is_visible_column
            text_match = not needle or needle in item.text().lower()
            item.setHidden(not (visibility_match and text_match))

    def _check_all(self) -> None:
        """Check every column."""
        for row in range(self.columns_list.count()):
            self.columns_list.item(row).setCheckState(Qt.CheckState.Checked)
        self._apply_filters()

    def _uncheck_all(self) -> None:
        """Uncheck every column except the first one."""
        if self.columns_list.count() == 0:
            return
        for row in range(self.columns_list.count()):
            item = self.columns_list.item(row)
            item.setCheckState(Qt.CheckState.Checked if row == 0 else Qt.CheckState.Unchecked)
        self._apply_filters()

    def checked_columns(self) -> list[int]:
        """Return the checked source columns."""
        columns: list[int] = []
        for row in range(self.columns_list.count()):
            item = self.columns_list.item(row)
            if item.checkState() == Qt.CheckState.Checked:
                columns.append(ty.cast(int, item.data(Qt.ItemDataRole.UserRole)))
        return columns


class RowVisibilityDialog(Qw.QDialog):
    """Dialog used to show or hide rows."""

    def __init__(self, parent: Qw.QWidget | None, proxy_model: DataFrameProxyModel):
        super().__init__(parent)
        self.setWindowTitle("Rows")
        self.setModal(True)
        self._initial_visibility: dict[int, bool] = {}
        self.resize(360, 420)
        self.setSizeGripEnabled(True)

        layout = Qw.QVBoxLayout(self)
        self.search_edit = Qw.QLineEdit(self)
        self.search_edit.setPlaceholderText("Filter rows...")
        self.search_edit.textChanged.connect(self._update_item_visibility)
        layout.addWidget(self.search_edit)

        self.visibility_filter = Qw.QComboBox(self)
        self.visibility_filter.addItems(["All rows", "Visible rows", "Hidden rows"])
        self.visibility_filter.currentIndexChanged.connect(self._apply_filters)
        layout.addWidget(self.visibility_filter)

        self.rows_list = Qw.QListWidget(self)
        self.rows_list.setSelectionMode(Qw.QAbstractItemView.SelectionMode.NoSelection)
        self.rows_list.setUniformItemSizes(True)
        self.rows_list.setAlternatingRowColors(True)
        self.rows_list.setVerticalScrollMode(Qw.QAbstractItemView.ScrollMode.ScrollPerPixel)
        for row in range(proxy_model.df.index.shape[0]):
            label = _row_label_to_text(proxy_model.df.index[row])
            item = Qw.QListWidgetItem(label, self.rows_list)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            is_visible = proxy_model.is_row_visible(row)
            item.setCheckState(Qt.CheckState.Checked if is_visible else Qt.CheckState.Unchecked)
            item.setData(Qt.ItemDataRole.UserRole, row)
            self._initial_visibility[row] = is_visible
        self.rows_list.setMinimumHeight(220)
        layout.addWidget(self.rows_list, stretch=1)

        buttons_layout = Qw.QHBoxLayout()
        check_all_button = Qw.QPushButton("Check all", self)
        check_all_button.clicked.connect(self._check_all)
        uncheck_all_button = Qw.QPushButton("Uncheck all", self)
        uncheck_all_button.clicked.connect(self._uncheck_all)
        buttons_layout.addWidget(check_all_button)
        buttons_layout.addWidget(uncheck_all_button)
        layout.addLayout(buttons_layout)

        button_box = Qw.QDialogButtonBox(
            Qw.QDialogButtonBox.StandardButton.Ok | Qw.QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _update_item_visibility(self, text: str) -> None:
        """Show only row labels that match the search text."""
        self._apply_filters(text)

    def _apply_filters(self, text: str | int = "") -> None:
        """Apply the current text and visibility filters to the list."""
        if isinstance(text, int):
            text = self.search_edit.text()
        needle = text.strip().lower()
        for row in range(self.rows_list.count()):
            item = self.rows_list.item(row)
            source_row = ty.cast(int, item.data(Qt.ItemDataRole.UserRole))
            is_visible_row = self._initial_visibility.get(source_row, True)
            visibility_mode = self.visibility_filter.currentText()
            visibility_match = True
            if visibility_mode == "Visible rows":
                visibility_match = is_visible_row
            elif visibility_mode == "Hidden rows":
                visibility_match = not is_visible_row
            text_match = not needle or needle in item.text().lower()
            item.setHidden(not (visibility_match and text_match))

    def _check_all(self) -> None:
        """Check every row."""
        for row in range(self.rows_list.count()):
            self.rows_list.item(row).setCheckState(Qt.CheckState.Checked)
        self._apply_filters()

    def _uncheck_all(self) -> None:
        """Uncheck every row except the first one."""
        if self.rows_list.count() == 0:
            return
        for row in range(self.rows_list.count()):
            item = self.rows_list.item(row)
            item.setCheckState(Qt.CheckState.Checked if row == 0 else Qt.CheckState.Unchecked)
        self._apply_filters()

    def checked_rows(self) -> list[int]:
        """Return the checked source rows."""
        rows: list[int] = []
        for row in range(self.rows_list.count()):
            item = self.rows_list.item(row)
            if item.checkState() == Qt.CheckState.Checked:
                rows.append(ty.cast(int, item.data(Qt.ItemDataRole.UserRole)))
        return rows


class QtDataFrameWidget(Qw.QWidget):
    """
    Displays a DataFrame as a table.

    Args:
    ----
        df (DataFrame): The DataFrame to display
    """

    def __init__(
        self,
        parent: Qw.QWidget | None,
        df: ty.Any | None,
        inplace: bool = True,
        editable: bool = False,
        stretch: bool = False,
        sortable: bool = True,
        filterable: bool = True,
        column_visibility_control: bool = True,
    ):
        super().__init__(parent)
        df = _normalize_tabular_data(df, inplace=inplace)

        # Indicates whether the widget has been shown yet. Set to True in
        self._loaded = False
        self.editable = editable
        self.sortable = sortable
        self.filterable = filterable
        self.column_visibility_control = column_visibility_control
        self._column_widths: dict[int, int] = {}

        # Set up DataFrame TableView and Model
        self.dataView = DataTableView(df, parent=self)
        self.dataView.setObjectName("dataView")
        if not editable:
            self.dataView.setEditTriggers(Qw.QAbstractItemView.EditTrigger.NoEditTriggers)

        # Create headers
        self.columnHeader = HeaderView(self, df, Qt.Orientation.Horizontal)
        self.columnHeader.setObjectName("columnHeader")
        self.indexHeader = HeaderView(self, df, Qt.Orientation.Vertical)
        self.indexHeader.setObjectName("indexHeader")
        self.cornerView = CornerView(self, df)
        self.cornerView.setObjectName("cornerView")

        # Link scrollbars
        # Scrolling in the data table also scrolls the headers
        self.dataView.horizontalScrollBar().valueChanged.connect(self.columnHeader.horizontalScrollBar().setValue)
        self.dataView.verticalScrollBar().valueChanged.connect(self.indexHeader.verticalScrollBar().setValue)
        # Scrolling in headers also scrolls the data table
        self.columnHeader.horizontalScrollBar().valueChanged.connect(self.dataView.horizontalScrollBar().setValue)
        self.indexHeader.verticalScrollBar().valueChanged.connect(self.dataView.verticalScrollBar().setValue)
        self.dataView.horizontalScrollBar().valueChanged.connect(self._sync_horizontal_offset)
        self.dataView.horizontalScrollBar().rangeChanged.connect(self._sync_header_scroll_metrics)
        self.dataView.verticalScrollBar().rangeChanged.connect(self._sync_header_scroll_metrics)

        self.dataView.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.dataView.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # Disable scrolling on the headers. Even though the scrollbars are hidden, scrolling by dragging desyncs them
        self.indexHeader.horizontalScrollBar().valueChanged.connect(self._ignore_scroll_value_change)

        # Set up layout
        self.gridLayout = Qw.QGridLayout(self)
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.gridLayout.setSpacing(0)

        # Add items to the layout
        # widget, row, column, rowspan, colspan
        self.gridLayout.addWidget(self.cornerView, 0, 0, 1, 1)
        self.gridLayout.addWidget(self.columnHeader, 0, 1, 1, 1)
        self.gridLayout.addWidget(self.indexHeader, 1, 0, 1, 1)
        self.gridLayout.addWidget(self.dataView, 1, 1, 1, 1)
        self.gridLayout.addWidget(self.dataView.horizontalScrollBar(), 2, 1, 1, 1)
        self.gridLayout.addWidget(self.dataView.verticalScrollBar(), 1, 2, 1, 1)

        # These expand when the window is enlarged instead of having the grid squares spread out
        self.gridLayout.setColumnStretch(1, 1)
        self.gridLayout.setRowStretch(1, 1)
        # React to scroll range changes so we can hide bars when unnecessary
        self.dataView.horizontalScrollBar().rangeChanged.connect(self._sync_horizontal_scrollbar_visibility)
        self.dataView.verticalScrollBar().rangeChanged.connect(self._sync_vertical_scrollbar_visibility)

        for item in [self.dataView, self.columnHeader, self.indexHeader, self.cornerView]:
            item.setContentsMargins(0, 0, 0, 0)
            item.setItemDelegate(NoFocusDelegate())
            item.setFrameShape(Qw.QFrame.Shape.NoFrame)
        # Ensure widgets expand within the layout
        self.dataView.setSizePolicy(Qw.QSizePolicy.Policy.Expanding, Qw.QSizePolicy.Policy.Expanding)
        self.columnHeader.setSizePolicy(Qw.QSizePolicy.Policy.Expanding, Qw.QSizePolicy.Policy.Fixed)
        self.indexHeader.setSizePolicy(Qw.QSizePolicy.Policy.Fixed, Qw.QSizePolicy.Policy.Expanding)
        self.cornerView.setSizePolicy(Qw.QSizePolicy.Policy.Fixed, Qw.QSizePolicy.Policy.Fixed)

    def showEvent(self, event: Qg.QShowEvent):
        """Initialize column and row sizes on the first time the widget is shown."""
        if not self._loaded:
            self._init_sizes()
        self._update_scrollbar_visibility()
        self._loaded = True
        event.accept()

    def set_data(self, df):
        """Replace the dataframe and reset view state."""
        df = _normalize_tabular_data(df)
        self._loaded = False
        self._column_widths.clear()
        self.setUpdatesEnabled(False)
        try:
            self.dataView.set_data(df)
            proxy_model = self.dataView.proxy_model
            self.columnHeader.set_data(proxy_model)
            self.indexHeader.set_data(proxy_model)
            self.cornerView.set_data(proxy_model)
            self._init_sizes()
            self._update_scrollbar_visibility()
            self._sync_header_scroll_metrics()
            self.updateGeometry()
            self.gridLayout.activate()
        finally:
            self.setUpdatesEnabled(True)

    def _update_scrollbar_visibility(self):
        """Hide scrollbars when not needed."""
        hbar = self.dataView.horizontalScrollBar()
        vbar = self.dataView.verticalScrollBar()
        hbar.setVisible(hbar.maximum() > 0)
        vbar.setVisible(vbar.maximum() > 0)

    def _ignore_scroll_value_change(self, _value: int) -> None:
        """Consume header scrollbar changes triggered by hidden scrollbars."""

    def _sync_horizontal_scrollbar_visibility(self, _min: int, max_value: int) -> None:
        """Update horizontal scrollbar visibility."""
        self.dataView.horizontalScrollBar().setVisible(max_value > 0)
        self._sync_header_scroll_metrics()

    def _sync_vertical_scrollbar_visibility(self, _min: int, max_value: int) -> None:
        """Update vertical scrollbar visibility."""
        self.dataView.verticalScrollBar().setVisible(max_value > 0)
        self._sync_header_scroll_metrics()

    def _sync_horizontal_offset(self, value: int) -> None:
        """Keep the header aligned with the data viewport."""
        if self.columnHeader.horizontalScrollBar().value() != value:
            self.columnHeader.horizontalScrollBar().setValue(value)
        self.columnHeader.viewport().update()
        self.dataView.viewport().update()

    def _sync_header_scroll_metrics(self, *_args: ty.Any) -> None:
        """Mirror scrollbar range metrics onto the header views."""
        data_hbar = self.dataView.horizontalScrollBar()
        header_hbar = self.columnHeader.horizontalScrollBar()
        if header_hbar.pageStep() != data_hbar.pageStep():
            header_hbar.setPageStep(data_hbar.pageStep())
        if header_hbar.singleStep() != data_hbar.singleStep():
            header_hbar.setSingleStep(data_hbar.singleStep())
        if header_hbar.maximum() != data_hbar.maximum():
            header_hbar.setRange(data_hbar.minimum(), data_hbar.maximum())
        if header_hbar.value() != data_hbar.value():
            header_hbar.setValue(data_hbar.value())

    def _resize_all_rows(self):
        """Auto-resize every row to its content height."""
        row_count = self.indexHeader.model().rowCount()
        for row_index in range(_sample_count(row_count, AUTO_SIZE_ROW_LIMIT)):
            self.auto_size_row(row_index)

    def _sync_corner_view(self):
        """Keep the top-left corner aligned with the row and column headers."""
        self.cornerView.sync_to_headers()

    def _init_sizes(self):
        """Shared sizing logic for initial load and data resets."""
        column_count = self.columnHeader.model().columnCount()
        row_count = self.indexHeader.model().rowCount()

        self.columnHeader.horizontalHeader().setDefaultSectionSize(DEFAULT_COLUMN_WIDTH)
        self.dataView.horizontalHeader().setDefaultSectionSize(DEFAULT_COLUMN_WIDTH)

        for column_index in range(_sample_count(column_count, AUTO_SIZE_COLUMN_LIMIT)):
            self.auto_size_column(column_index)

        default_row_height = DEFAULT_ROW_HEIGHT
        for row_index in range(_sample_count(row_count, AUTO_SIZE_ROW_LIMIT)):
            self.auto_size_row(row_index)
            height = self.indexHeader.rowHeight(row_index)
            default_row_height = max(default_row_height, height)
        default_row_height = min(default_row_height, MAX_ROW_HEIGHT)
        self.indexHeader.verticalHeader().setDefaultSectionSize(default_row_height)
        self.dataView.verticalHeader().setDefaultSectionSize(default_row_height)
        self._restore_column_widths()
        self.columnHeader._apply_extent()
        self.indexHeader._apply_extent()
        self._sync_corner_view()
        self._sync_header_scroll_metrics()

    def auto_size_column(self, column_index: int) -> None:
        """Set the size of column at column_index to fit its contents."""
        metrics = self.dataView.fontMetrics()
        header_metrics = self.columnHeader.fontMetrics()
        width = DEFAULT_COLUMN_WIDTH

        # Iterate over the column's rows and check the width of each to determine the max width for the column
        # Only check the first N rows for performance. If there is larger content in cells below it will be cut off
        header_model = self.columnHeader.model()
        for level in range(header_model.rowCount()):
            header_index = header_model.index(level, column_index)
            header_text = header_model.data(header_index, Qt.ItemDataRole.DisplayRole) or ""
            width = max(width, _text_width(header_metrics, header_text))

        for i in range(_sample_count(self.dataView.model().rowCount(), AUTO_SIZE_SAMPLE)):
            mi = self.dataView.model().index(i, column_index)
            text = self.dataView.model().data(mi) or ""
            w = _text_width(metrics, text)
            width = max(width, w)

        width = min(width + HEADER_PADDING, MAX_COLUMN_WIDTH)

        self._set_column_width(column_index, width)

    def auto_size_row(self, row_index: int) -> None:
        """Set the size of row at row_index to fix its contents."""
        metrics = self.dataView.fontMetrics()
        height = DEFAULT_ROW_HEIGHT

        # Iterate over the row's columns and check the width of each to determine the max height for the row
        # Only check the first N columns for performance.
        index_model = self.indexHeader.model()
        for level in range(index_model.columnCount()):
            header_index = index_model.index(row_index, level)
            header_text = index_model.data(header_index, Qt.ItemDataRole.DisplayRole) or ""
            height = max(height, metrics.boundingRect(header_text).height())

        for i in range(_sample_count(self.dataView.model().columnCount(), AUTO_SIZE_SAMPLE)):
            mi = self.dataView.model().index(row_index, i)
            cell_width = self.columnHeader.columnWidth(i)
            text = self.dataView.model().data(mi) or ""
            # Gets row height at a constrained width (the column width).
            # This constrained width, with the flag of Qt.TextWordWrap
            # gets the height the cell would have to be to fit the text.
            constrained_rect = Qc.QRect(0, 0, cell_width, 0)
            h = metrics.boundingRect(constrained_rect, Qt.TextFlag.TextWordWrap, text).height()

            height = max(height, h)

        height = min(height + ROW_PADDING, MAX_ROW_HEIGHT)

        self.indexHeader.setRowHeight(row_index, height)
        self.dataView.setRowHeight(row_index, height)

    @property
    def proxy_model(self) -> DataFrameProxyModel:
        """Return the active dataframe proxy model."""
        return self.dataView.proxy_model

    def clear_sorting(self) -> None:
        """Reset sorting to the source row order."""
        self.proxy_model.clear_sorting()
        self._refresh_after_proxy_change()

    def clear_filters(self) -> None:
        """Remove all active column filters."""
        self.proxy_model.clear_filters()
        self._refresh_after_proxy_change()

    def set_numeric_filter(
        self,
        column: int,
        *,
        minimum: float | None = None,
        maximum: float | None = None,
        include_blanks: bool = True,
    ) -> None:
        """Apply a numeric filter to a source column."""
        self.proxy_model.set_numeric_filter(
            column,
            minimum=minimum,
            maximum=maximum,
            include_blanks=include_blanks,
        )
        self._refresh_after_proxy_change()

    def set_value_filter(
        self,
        column: int,
        allowed_values: ty.Iterable[str] | None,
        *,
        include_blanks: bool = True,
    ) -> None:
        """Apply a value-selection filter to a source column."""
        self.proxy_model.set_string_filter(column, allowed_values=allowed_values, include_blanks=include_blanks)
        self._refresh_after_proxy_change()

    def set_column_visible(self, column: int, visible: bool) -> None:
        """Show or hide a source column."""
        if self.proxy_model.set_column_visible(column, visible):
            self._refresh_after_proxy_change()

    def set_row_visible(self, row: int, visible: bool) -> None:
        """Show or hide a source row."""
        if self.proxy_model.set_row_visible(row, visible):
            self._refresh_after_proxy_change()

    def visible_columns(self) -> list[int]:
        """Return the visible source column positions."""
        return self.proxy_model.visible_columns

    def visible_rows(self) -> list[int]:
        """Return the visible source row positions."""
        return self.proxy_model.visible_rows

    def toggle_sort(self, column: int) -> None:
        """Toggle sorting for a source column."""
        self.proxy_model.toggle_sort(column)
        self._refresh_after_proxy_change()

    def _set_column_width(self, column_index: int, width: int) -> None:
        """Apply and remember the width for a visible column."""
        source_column = self.proxy_model.source_column(column_index)
        self._column_widths[source_column] = width
        self.columnHeader.setColumnWidth(column_index, width)
        self.dataView.setColumnWidth(column_index, width)
        self.columnHeader._apply_extent()
        self._sync_header_scroll_metrics()

    def _restore_column_widths(self) -> None:
        """Restore stored widths for visible columns."""
        for visible_column, source_column in enumerate(self.proxy_model.visible_columns):
            width = self._column_widths.get(source_column, DEFAULT_COLUMN_WIDTH)
            self.columnHeader.setColumnWidth(visible_column, width)
            self.dataView.setColumnWidth(visible_column, width)

    def _refresh_after_proxy_change(self) -> None:
        """Refresh headers and geometry after proxy state changes."""
        self.columnHeader.set_data(self.proxy_model)
        self.indexHeader.set_data(self.proxy_model)
        self.cornerView.set_data(self.proxy_model)
        self._restore_column_widths()
        self._resize_all_rows()
        self.columnHeader._apply_extent()
        self.indexHeader._apply_extent()
        self._sync_corner_view()
        self._update_scrollbar_visibility()
        self._sync_header_scroll_metrics()
        self.updateGeometry()

    def keyPressEvent(self, event):
        """Handle key presses."""
        Qw.QWidget.keyPressEvent(self, event)

        if event.matches(Qg.QKeySequence.StandardKey.Copy):
            self.dataView.copy()
            logger.trace("Copied selection to clipboard")
        if event.matches(Qg.QKeySequence.StandardKey.Paste):
            self.dataView.paste()
            logger.trace("Pasted clipboard contents")
        if event.key() == Qt.Key.Key_P and (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
            self.dataView.print()
            logger.trace("Printed clipboard contents")
        if event.key() == Qt.Key.Key_D and (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
            self.debug()
            logger.trace("Debug contents")

    def debug(self):
        """Debug."""
        print(self.columnHeader.sizeHint())
        print(self.dataView.sizeHint())
        print(self.dataView.horizontalScrollBar().sizeHint())


# Remove dotted border on cell focus.  https://stackoverflow.com/a/55252650/3620725
class NoFocusDelegate(Qw.QStyledItemDelegate):
    """Delegate to remove focus border."""

    def paint(self, painter: Qw.QPainter, style: Qw.QStyleOptionViewItem, index: Qw.QModelIndex):
        """Paint event."""
        if style.state & Qw.QStyle.StateFlag.State_HasFocus:
            style.state = style.state ^ Qw.QStyle.StateFlag.State_HasFocus
        super().paint(painter, style, index)


class DataTableModel(BaseTabularTableModel):
    """Model for DataTableView to connect for DataFrame data."""

    def __init__(self, df, parent=None):
        super().__init__(parent, editable=True)
        df = _normalize_tabular_data(df)
        self.df = df
        self._values = df.to_numpy(copy=False)
        self.set_shape(len(df), df.columns.shape[0])

    def headerData(self, section, orientation, role=None):
        # Headers for DataTableView are hidden. Header data is shown in HeaderView
        return None

    def _value_at(self, row: int, column: int):
        """Return raw cell value."""
        return self._values[row, column]

    def _display_value(self, value):
        """Return display value."""
        if pd.isnull(value):
            return ""
        if is_float_like(value):
            return f"{value:.4f}"
        return str(value)

    def _set_value_at(self, row: int, column: int, value) -> None:
        """Set the data at the given index."""
        self.df.iat[row, column] = value
        self._values = self.df.to_numpy(copy=False)

    def setData(self, index, value, role=None):
        """Set the data at the given index."""
        if not (self._editable and role == Qt.ItemDataRole.EditRole):
            return None
        try:
            self._set_value_at(index.row(), index.column(), value)
        except (TypeError, ValueError) as e:
            print(e)
            return False
        self.dataChanged.emit(index, index)
        return True


class DataTableView(Qw.QTableView):
    """Displays the DataFrame data as a table."""

    def __init__(self, df, parent):
        super().__init__(parent)
        self.parent = parent
        self.source_model: DataTableModel | None = None
        self.proxy_model: DataFrameProxyModel | None = None

        # Create and set model
        self.set_data(df)

        # Hide the headers. The DataFrame headers (index & columns) will be displayed in the DataFrameHeaderViews
        self.horizontalHeader().hide()
        self.verticalHeader().hide()

        # Settings
        self.setAlternatingRowColors(True)
        self.setWordWrap(False)
        self.setHorizontalScrollMode(Qw.QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setVerticalScrollMode(Qw.QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.horizontalHeader().setDefaultSectionSize(DEFAULT_COLUMN_WIDTH)
        self.verticalHeader().setDefaultSectionSize(DEFAULT_ROW_HEIGHT)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

    def set_data(self, df):
        """Set data model."""
        df = _normalize_tabular_data(df)
        with contextlib.suppress(Exception):
            self.selectionModel().selectionChanged.disconnect(self.on_selection_changed)
        self.source_model = DataTableModel(df)
        self.proxy_model = DataFrameProxyModel(self.source_model, self)
        self.setModel(self.proxy_model)
        self.selectionModel().selectionChanged.connect(self.on_selection_changed)

    def on_selection_changed(self):
        """
        Runs when cells are selected in the main table. This logic highlights the correct cells in the vertical and
        horizontal headers when a data cell is selected.
        """
        columnHeader = self.parent.columnHeader
        indexHeader = self.parent.indexHeader

        # The two blocks below check what columns or rows are selected in the data table and highlights the
        # corresponding ones in the two headers. The if statements check for focus on headers, because if the user
        # clicks a header that will auto-select all cells in that row or column which will trigger this function
        # and cause and infinite loop

        if not columnHeader.hasFocus():
            selection = self.selectionModel().selection()
            columnHeader.selectionModel().select(
                selection,
                Qc.QItemSelectionModel.SelectionFlag.Columns | Qc.QItemSelectionModel.SelectionFlag.ClearAndSelect,
            )

        if not indexHeader.hasFocus():
            selection = self.selectionModel().selection()
            indexHeader.selectionModel().select(
                selection,
                Qc.QItemSelectionModel.SelectionFlag.Rows | Qc.QItemSelectionModel.SelectionFlag.ClearAndSelect,
            )

    def print(self):
        """Print information."""
        print(self.model().df)

    def copy(self):
        """Copy the selected cells to clipboard in an Excel-pasteable format."""
        self.copy_selection_to_clipboard()

    def copy_selection_to_clipboard(self) -> None:
        """Copy the current rectangular selection with row labels and column headers."""
        export_df = self._selection_dataframe()
        if export_df is None:
            return
        self._copy_dataframe_to_clipboard(export_df)

    def copy_selected_rows_to_clipboard(self) -> None:
        """Copy the selected rows with visible columns."""
        export_df = self._selected_rows_dataframe()
        if export_df is None:
            return
        self._copy_dataframe_to_clipboard(export_df)

    def copy_selected_columns_to_clipboard(self) -> None:
        """Copy the selected visible columns across visible rows."""
        export_df = self._selected_columns_dataframe()
        if export_df is None:
            return
        self._copy_dataframe_to_clipboard(export_df)

    def _copy_dataframe_to_clipboard(self, df: pd.DataFrame) -> None:
        """Copy a dataframe to the clipboard as tab-separated text."""
        buffer = io.StringIO()
        df.to_csv(buffer, sep="\t", index=True, header=True, lineterminator="\n")
        Qg.QGuiApplication.clipboard().setText(buffer.getvalue())

    def _visible_dataframe(self) -> pd.DataFrame:
        """Return the dataframe currently exposed by the proxy model."""
        assert self.proxy_model is not None
        row_positions = self.proxy_model.visible_rows
        column_positions = self.proxy_model.visible_columns
        return self.proxy_model.df.iloc[row_positions, column_positions]

    def _selection_dataframe(self) -> pd.DataFrame | None:
        """Return the currently selected rectangular dataframe slice."""
        indexes = self.selectionModel().selectedIndexes()
        if not indexes:
            return None
        selected_rows = sorted({index.row() for index in indexes})
        selected_columns = sorted({index.column() for index in indexes})
        if not selected_rows or not selected_columns:
            return None
        visible_df = self._visible_dataframe()
        return visible_df.iloc[selected_rows, selected_columns]

    def _selected_rows_dataframe(self) -> pd.DataFrame | None:
        """Return the currently selected rows for all visible columns."""
        indexes = self.selectionModel().selectedIndexes()
        if not indexes:
            return None
        selected_rows = sorted({index.row() for index in indexes})
        if not selected_rows:
            return None
        visible_df = self._visible_dataframe()
        return visible_df.iloc[selected_rows, :]

    def _selected_columns_dataframe(self) -> pd.DataFrame | None:
        """Return the currently selected columns for all visible rows."""
        indexes = self.selectionModel().selectedIndexes()
        if not indexes:
            return None
        selected_columns = sorted({index.column() for index in indexes})
        if not selected_columns:
            return None
        visible_df = self._visible_dataframe()
        return visible_df.iloc[:, selected_columns]

    def _show_context_menu(self, position: Qc.QPoint) -> None:
        """Show the selection copy context menu."""
        if not self.selectionModel().selectedIndexes():
            return
        menu = Qw.QMenu(self)
        copy_selection_action = menu.addAction("Copy selection")
        copy_selection_action.triggered.connect(self.copy_selection_to_clipboard)
        copy_rows_action = menu.addAction("Copy selected rows")
        copy_rows_action.triggered.connect(self.copy_selected_rows_to_clipboard)
        copy_columns_action = menu.addAction("Copy selected columns")
        copy_columns_action.triggered.connect(self.copy_selected_columns_to_clipboard)
        menu.exec(self.viewport().mapToGlobal(position))

    def paste(self):
        """Paste data from clipboard."""
        # import sys
        #
        # # Set up clipboard object
        # app = Qw.QApplication.instance()
        # if not app:
        #     app = Qw.QApplication(sys.argv)
        # clipboard = app.clipboard()
        # # TODO
        # print(clipboard.text())

    def sizeHint(self):
        """Get size hint."""
        return super().sizeHint()


class HeaderModel(Qc.QAbstractTableModel):
    """Model for HeaderView."""

    def __init__(self, proxy_model: DataFrameProxyModel, orientation, parent=None):
        super().__init__(parent)
        self.proxy_model = proxy_model
        self.df = proxy_model.df
        self.orientation = orientation

    def columnCount(self, parent=None):
        """Number of columns."""
        if self.orientation == Qt.Orientation.Horizontal:
            return len(self.proxy_model.visible_columns)
        # Vertical
        return self.df.index.nlevels

    def rowCount(self, parent=None):
        """Number of rows."""
        if self.orientation == Qt.Orientation.Horizontal:
            return self.df.columns.nlevels
        if self.orientation == Qt.Orientation.Vertical:
            return len(self.proxy_model.visible_rows)
        return None

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        """Data."""
        row = index.row()
        col = index.column()

        if role == Qt.ItemDataRole.DisplayRole or role == Qt.ItemDataRole.ToolTipRole:
            if self.orientation == Qt.Orientation.Horizontal:
                source_column = self.proxy_model.source_column(col)
                if isinstance(self.df.columns, pd.MultiIndex):
                    text = str(self.df.columns.values[source_column][row])
                else:
                    text = str(self.df.columns.values[source_column])
                return self._with_sort_indicator(text, row=row, source_column=source_column, role=role)

            if self.orientation == Qt.Orientation.Vertical:
                source_row = self.proxy_model.source_row(row)
                if isinstance(self.df.index, pd.MultiIndex):
                    return str(self.df.index.values[source_row][col])
                return str(self.df.index.values[source_row])
            return None
        if role == Qt.ItemDataRole.FontRole:
            bold_font = Qg.QFont()
            bold_font.setBold(True)
            if self.orientation == Qt.Orientation.Horizontal:
                source_column = self.proxy_model.source_column(col)
                if self.proxy_model.is_column_filtered(source_column):
                    bold_font.setUnderline(True)
                if self.proxy_model.sort_column == source_column:
                    bold_font.setItalic(True)
            return bold_font
        return None

    def _with_sort_indicator(
        self,
        text: str,
        *,
        row: int,
        source_column: int,
        role: Qt.ItemDataRole,
    ) -> str:
        """Append the current sort indicator to the leaf header cell."""
        if role != Qt.ItemDataRole.DisplayRole:
            return text
        if self.orientation != Qt.Orientation.Horizontal:
            return text
        if row != self.rowCount() - 1:
            return text
        if self.proxy_model.sort_column != source_column or self.proxy_model.sort_order is None:
            return text
        indicator = (
            ASCENDING_SORT_INDICATOR
            if self.proxy_model.sort_order == Qt.SortOrder.AscendingOrder
            else DESCENDING_SORT_INDICATOR
        )
        return f"{text}{indicator}"

    # The headers of this table will show the level names of the MultiIndex
    def headerData(self, section, orientation, role=None):
        """Header data."""
        if role == Qt.ItemDataRole.FontRole:
            bold_font = Qg.QFont()
            bold_font.setBold(True)
            return bold_font
        if role in [Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.ToolTipRole]:
            if self.orientation == Qt.Orientation.Horizontal and orientation == Qt.Orientation.Vertical:
                if isinstance(self.df.columns, pd.MultiIndex):
                    return str(self.df.columns.names[section])
                return str(self.df.columns.name)
            if self.orientation == Qt.Orientation.Vertical and orientation == Qt.Orientation.Horizontal:
                if isinstance(self.df.index, pd.MultiIndex):
                    return str(self.df.index.names[section])
                return str(self.df.index.name)
            return None  # These cells should be hidden anyways
        return None


class CornerModel(Qc.QAbstractTableModel):
    """Model for the corner view that displays index and column level names."""

    def __init__(self, proxy_model: DataFrameProxyModel, parent=None):
        super().__init__(parent)
        self.proxy_model = proxy_model
        self.df = proxy_model.df

    @property
    def column_level_names(self) -> list[str]:
        names = list(self.df.columns.names) if isinstance(self.df.columns, pd.MultiIndex) else [self.df.columns.name]
        return [str(name) if name is not None else "" for name in names]

    @property
    def index_level_names(self) -> list[str]:
        names = list(self.df.index.names) if isinstance(self.df.index, pd.MultiIndex) else [self.df.index.name]
        return [str(name) if name is not None else "" for name in names]

    def rowCount(self, parent=None):
        """Number of rows."""
        return len(self.column_level_names)

    def columnCount(self, parent=None):
        """Number of columns."""
        return len(self.index_level_names)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        """Display level names in the corner grid."""
        if not index.isValid():
            return None
        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.ToolTipRole):
            row = index.row()
            col = index.column()
            row_names = self.column_level_names
            col_names = self.index_level_names
            if col == len(col_names) - 1:
                return row_names[row]
            if row == len(row_names) - 1:
                return col_names[col]
            return ""
        if role == Qt.ItemDataRole.FontRole:
            bold_font = Qg.QFont()
            bold_font.setBold(True)
            return bold_font
        if role == Qt.ItemDataRole.TextAlignmentRole:
            return Qt.AlignmentFlag.AlignCenter
        return None


class CornerView(Qw.QTableView):
    """Corner view that renders index and column level names without gutter headers."""

    def __init__(self, parent: QtDataFrameWidget, df):
        super().__init__(parent)
        self.parent = parent
        self.setWordWrap(False)
        self.setEditTriggers(Qw.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setSelectionMode(Qw.QAbstractItemView.SelectionMode.NoSelection)
        self.horizontalHeader().hide()
        self.verticalHeader().hide()
        self.horizontalHeader().setDefaultSectionSize(DEFAULT_COLUMN_WIDTH)
        self.verticalHeader().setDefaultSectionSize(DEFAULT_ROW_HEIGHT)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollMode(Qw.QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setVerticalScrollMode(Qw.QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.set_data(parent.proxy_model)

    def set_data(self, proxy_model: DataFrameProxyModel) -> None:
        """Update corner model."""
        self.setModel(CornerModel(proxy_model, self))
        self._apply_spans()
        self.sync_to_headers()

    def sync_to_headers(self) -> None:
        """Align corner geometry and sections with the index and column headers."""
        index_header = self.parent.indexHeader
        column_header = self.parent.columnHeader

        for col in range(self.model().columnCount()):
            self.setColumnWidth(col, index_header.columnWidth(col))
        for row in range(self.model().rowCount()):
            self.setRowHeight(row, column_header.rowHeight(row))

        self.setFixedSize(index_header.header_extent(), column_header.header_extent())

    def _apply_spans(self) -> None:
        """Merge the empty top-left region into a single visual block."""
        self.clearSpans()
        rows = self.model().rowCount()
        cols = self.model().columnCount()
        if rows > 1 and cols > 1:
            _set_span_if_needed(self, 0, 0, rows - 1, cols - 1)


class HeaderView(Qw.QTableView):
    """Displays the DataFrame index or columns depending on orientation."""

    df = None

    def __init__(self, parent: QtDataFrameWidget, df: pd.DataFrame, orientation: Qt.Orientation):
        super().__init__(parent)

        # Setup
        self.orientation = orientation
        self.parent = parent
        self.table = parent.dataView
        self.set_data(parent.proxy_model)

        # These are used during column resizing
        self.header_being_resized = None
        self.resize_start_position = None
        self.initial_header_size = None
        self._press_position: Qc.QPoint | None = None
        self._pressed_section: int | None = None
        self._dragged_during_press = False

        # Handled by self.eventFilter()
        self.setMouseTracking(True)
        self.viewport().setMouseTracking(True)
        self.viewport().installEventFilter(self)

        # Settings
        self.setSizePolicy(Qw.QSizePolicy(Qw.QSizePolicy.Policy.Maximum, Qw.QSizePolicy.Policy.Maximum))
        self.setWordWrap(False)
        # self.setFont(Qg.QFont("Times", weight=Qg.QFont.Weight.Bold))
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollMode(Qw.QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setVerticalScrollMode(Qw.QAbstractItemView.ScrollMode.ScrollPerPixel)

        # Orientation specific settings
        if orientation == Qt.Orientation.Horizontal:
            self.setHorizontalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAlwaysOff,
            )  # Scrollbar is replaced in DataFrameViewer
            self.horizontalHeader().hide()
            self.horizontalHeader().setFixedHeight(0)
            self.verticalHeader().hide()
            self.verticalHeader().setFixedWidth(0)
            self.verticalHeader().setDisabled(True)
            self.verticalHeader().setHighlightSections(False)  # Selection lags a lot without this

        else:
            self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            self.verticalHeader().hide()
            self.verticalHeader().setFixedWidth(0)
            self.horizontalHeader().hide()
            self.horizontalHeader().setFixedHeight(0)
            self.horizontalHeader().setDisabled(True)

            self.horizontalHeader().setHighlightSections(False)  # Selection lags a lot without this

    def set_data(self, proxy_model: DataFrameProxyModel):
        """Update dataframe."""
        self.df = proxy_model.df
        self.proxy_model = proxy_model
        with contextlib.suppress(Exception):
            self.selectionModel().selectionChanged.disconnect(self.on_selection_changed)
        self.setModel(HeaderModel(proxy_model, self.orientation))
        self.selectionModel().selectionChanged.connect(self.on_selection_changed)
        self.clearSpans()
        self.setSpans()
        self.initSize()
        self._apply_extent()
        self.updateGeometry()

    # Header
    def on_selection_changed(self):
        """Runs when cells are selected in the Header.

        This selects columns in the data table when the header is clicked, and then calls selectAbove().
        """
        # Check focus so we don't get recursive loop, since headers trigger selection of data cells and vice versa
        if self.hasFocus():
            dataView = self.parent.dataView

            # Set selection mode so selecting one row or column at a time adds to selection each time
            if self.orientation == Qt.Orientation.Horizontal:  # This case is for the horizontal header
                # Get the header's selected columns
                selection = self.selectionModel().selection()

                # Removes the higher levels so that only the lowest level of the header affects the data table selection
                last_row_ix = self.df.columns.nlevels - 1
                last_col_ix = self.model().columnCount() - 1
                if last_row_ix <= 0 or last_col_ix < 0:
                    dataView.selectionModel().select(
                        selection,
                        Qc.QItemSelectionModel.SelectionFlag.Columns
                        | Qc.QItemSelectionModel.SelectionFlag.ClearAndSelect,
                    )
                    self.selectAbove()
                    return
                higher_levels = Qc.QItemSelection(
                    self.model().index(0, 0),
                    self.model().index(last_row_ix - 1, last_col_ix),
                )
                selection.merge(higher_levels, Qc.QItemSelectionModel.SelectionFlag.Deselect)

                # Select the cells in the data view
                dataView.selectionModel().select(
                    selection,
                    Qc.QItemSelectionModel.SelectionFlag.Columns | Qc.QItemSelectionModel.SelectionFlag.ClearAndSelect,
                )
            if self.orientation == Qt.Orientation.Vertical:
                selection = self.selectionModel().selection()

                last_row_ix = self.model().rowCount() - 1
                last_col_ix = self.df.index.nlevels - 1
                if last_row_ix < 0 or last_col_ix <= 0:
                    dataView.selectionModel().select(
                        selection,
                        Qc.QItemSelectionModel.SelectionFlag.Rows | Qc.QItemSelectionModel.SelectionFlag.ClearAndSelect,
                    )
                    self.selectAbove()
                    return
                higher_levels = Qc.QItemSelection(
                    self.model().index(0, 0),
                    self.model().index(last_row_ix, last_col_ix - 1),
                )
                selection.merge(higher_levels, Qc.QItemSelectionModel.SelectionFlag.Deselect)

                dataView.selectionModel().select(
                    selection,
                    Qc.QItemSelectionModel.SelectionFlag.Rows | Qc.QItemSelectionModel.SelectionFlag.ClearAndSelect,
                )

        self.selectAbove()

    # Take the current set of selected cells and make it so that any spanning cell above a selected cell is selected too
    # This should happen after every selection change
    def selectAbove(self):
        """Select above."""
        if self.orientation == Qt.Orientation.Horizontal:
            if self.df.columns.nlevels == 1:
                return
        else:
            if self.df.index.nlevels == 1:
                return

        for ix in self.selectedIndexes():
            if self.orientation == Qt.Orientation.Horizontal:
                # Loop over the rows above this one
                for row in range(ix.row()):
                    ix2 = self.model().index(row, ix.column())
                    self.setSelection(self.visualRect(ix2), Qc.QItemSelectionModel.SelectionFlag.Select)
            else:
                # Loop over the columns left of this one
                for col in range(ix.column()):
                    ix2 = self.model().index(ix.row(), col)
                    self.setSelection(self.visualRect(ix2), Qc.QItemSelectionModel.SelectionFlag.Select)

    # Fits columns to contents but with a minimum width and added padding
    def initSize(self):
        """Initialize size."""
        metrics = self.fontMetrics()

        if self.orientation == Qt.Orientation.Horizontal:
            self.verticalHeader().setDefaultSectionSize(DEFAULT_ROW_HEIGHT)
            for col in range(self.model().columnCount()):
                source_column = self.proxy_model.source_column(col)
                width = self.parent._column_widths.get(source_column, self.table.columnWidth(col))
                width = max(DEFAULT_COLUMN_WIDTH, width)
                self.setColumnWidth(col, width)
        else:
            for col in range(self.model().columnCount()):
                width = DEFAULT_COLUMN_WIDTH
                for row in range(_sample_count(self.model().rowCount(), AUTO_SIZE_SAMPLE)):
                    index = self.model().index(row, col)
                    text = self.model().data(index, Qt.ItemDataRole.DisplayRole) or ""
                    width = max(width, _text_width(metrics, text))
                self.setColumnWidth(col, min(width + HEADER_PADDING, MAX_COLUMN_WIDTH))

    def header_extent(self) -> int:
        """Return the visible extent needed by this header."""
        if self.orientation == Qt.Orientation.Horizontal:
            extent = 2 * self.frameWidth()
            for row in range(self.model().rowCount()):
                extent += self.rowHeight(row)
            return extent

        extent = 2 * self.frameWidth()
        for column in range(self.model().columnCount()):
            extent += self.columnWidth(column)
        return extent

    def _apply_extent(self) -> None:
        """Constrain the header widget to its content extent."""
        extent = self.header_extent()
        if self.orientation == Qt.Orientation.Horizontal:
            self.setFixedHeight(extent)
        else:
            self.setFixedWidth(extent)

    # This sets spans to group together adjacent cells with the same values
    def setSpans(self):
        """Set spans."""
        if self.model().rowCount() == 0 or self.model().columnCount() == 0:
            return
        df = self.model().df

        # Find spans for horizontal HeaderView
        if self.orientation == Qt.Orientation.Horizontal:
            if df.columns.empty:
                return
            # Find how many levels the MultiIndex has
            N = len(df.columns[0]) if isinstance(df.columns, pd.MultiIndex) else 1

            for level in range(N):  # Iterates over the levels
                # Find how many segments the MultiIndex has
                if isinstance(df.columns, pd.MultiIndex):
                    arr = [
                        df.columns[self.proxy_model.source_column(i)][level] for i in range(self.model().columnCount())
                    ]
                else:
                    arr = [df.columns[self.proxy_model.source_column(i)] for i in range(self.model().columnCount())]

                # Holds the starting index of a range of equal values.
                # None means it is not currently in a range of equal values.
                match_start = None

                for col in range(1, len(arr)):  # Iterates over cells in row
                    # Check if cell matches cell to its left
                    if arr[col] == arr[col - 1]:
                        if match_start is None:
                            match_start = col - 1
                        # If this is the last cell, need to end it
                        if col == len(arr) - 1:
                            match_end = col
                            span_size = match_end - match_start + 1
                            _set_span_if_needed(self, level, match_start, 1, span_size)
                    else:
                        if match_start is not None:
                            match_end = col - 1
                            span_size = match_end - match_start + 1
                            _set_span_if_needed(self, level, match_start, 1, span_size)
                            match_start = None

        # Find spans for vertical HeaderView
        else:
            if df.index.empty:
                return
            if len(df.index) > MAX_VERTICAL_SPAN_ROWS:
                return
            # Find how many levels the MultiIndex has
            N = len(df.index[0]) if isinstance(df.index, pd.MultiIndex) else 1

            for level in range(N):  # Iterates over the levels
                # Find how many segments the MultiIndex has
                if isinstance(df.index, pd.MultiIndex):
                    arr = [df.index[self.proxy_model.source_row(i)][level] for i in range(self.model().rowCount())]
                else:
                    arr = [df.index[self.proxy_model.source_row(i)] for i in range(self.model().rowCount())]

                # Holds the starting index of a range of equal values.
                # None means it is not currently in a range of equal values.
                match_start = None

                for row in range(1, len(arr)):  # Iterates over cells in column
                    # Check if cell matches cell above
                    if arr[row] == arr[row - 1]:
                        if match_start is None:
                            match_start = row - 1
                        # If this is the last cell, need to end it
                        if row == len(arr) - 1:
                            match_end = row
                            span_size = match_end - match_start + 1
                            _set_span_if_needed(self, match_start, level, span_size, 1)
                    else:
                        if match_start is not None:
                            match_end = row - 1
                            span_size = match_end - match_start + 1
                            _set_span_if_needed(self, match_start, level, span_size, 1)
                            match_start = None

    def over_header_edge(self, mouse_position, margin=3):
        """Return the index of the column or row the mouse is over the edge of, or None if it is not over an edge."""
        # Return the index of the column this x position is on the right edge of
        if self.orientation == Qt.Orientation.Horizontal:
            x = mouse_position
            if self.columnAt(x - margin) != self.columnAt(x + margin):
                if self.columnAt(x + margin) == 0:
                    # We're at the left edge of the first column
                    return None
                return self.columnAt(x - margin)
            return None

        # Return the index of the row this y position is on the top edge of
        if self.orientation == Qt.Orientation.Vertical:
            y = mouse_position
            if self.rowAt(y - margin) != self.rowAt(y + margin):
                if self.rowAt(y + margin) == 0:
                    # We're at the top edge of the first row
                    return None
                return self.rowAt(y - margin)
            return None
        return None

    def eventFilter(self, watched: Qc.QObject, event: Qc.QEvent):
        """Event filter."""
        # If mouse is on an edge, start the drag resize process
        if event.type() == Qc.QEvent.Type.MouseButtonPress:
            self._press_position = event.pos()
            self._pressed_section = None
            self._dragged_during_press = False
            if self.orientation == Qt.Orientation.Horizontal:
                mouse_position = event.pos().x()
                self._pressed_section = self.columnAt(mouse_position)
            elif self.orientation == Qt.Orientation.Vertical:
                mouse_position = event.pos().y()
                self._pressed_section = self.rowAt(mouse_position)

            if self.over_header_edge(mouse_position) is not None:
                self.header_being_resized = self.over_header_edge(mouse_position)
                self.resize_start_position = mouse_position
                if self.orientation == Qt.Orientation.Horizontal:
                    self.initial_header_size = self.columnWidth(self.header_being_resized)
                elif self.orientation == Qt.Orientation.Vertical:
                    self.initial_header_size = self.rowHeight(self.header_being_resized)
                return True
            self.header_being_resized = None

        # End the drag process
        if event.type() == Qc.QEvent.Type.MouseButtonRelease:
            if (
                self.orientation == Qt.Orientation.Horizontal
                and event.button() == Qt.MouseButton.LeftButton
                and self.header_being_resized is None
            ):
                column = self.columnAt(event.pos().x())
                if (
                    column >= 0
                    and self.parent.sortable
                    and not self._dragged_during_press
                    and column == self._pressed_section
                ):
                    self.parent.toggle_sort(self.proxy_model.source_column(column))
                    return True
            if (
                self.orientation == Qt.Orientation.Horizontal
                and event.button() == Qt.MouseButton.RightButton
                and self.header_being_resized is None
            ):
                column = self.columnAt(event.pos().x())
                if column >= 0:
                    self._show_context_menu(self.proxy_model.source_column(column), event.globalPos())
                    return True
            if (
                self.orientation == Qt.Orientation.Vertical
                and event.button() == Qt.MouseButton.RightButton
                and self.header_being_resized is None
            ):
                row = self.rowAt(event.pos().y())
                if row >= 0:
                    self._show_row_context_menu(self.proxy_model.source_row(row), event.globalPos())
                    return True
            self.header_being_resized = None
            self._press_position = None
            self._pressed_section = None
            self._dragged_during_press = False

        # Auto size the column that was double clicked
        if event.type() == Qc.QEvent.Type.MouseButtonDblClick:
            if self.orientation == Qt.Orientation.Horizontal:
                mouse_position = event.pos().x()
            elif self.orientation == Qt.Orientation.Vertical:
                mouse_position = event.pos().y()

            # Find which column or row edge the mouse was over and auto size it
            if self.over_header_edge(mouse_position) is not None:
                header_index = self.over_header_edge(mouse_position)
                if self.orientation == Qt.Orientation.Horizontal:
                    self.parent.auto_size_column(header_index)
                elif self.orientation == Qt.Orientation.Vertical:
                    self.parent.auto_size_row(header_index)
                return True

        # Handle active drag resizing
        if event.type() == Qc.QEvent.Type.MouseMove:
            if self.orientation == Qt.Orientation.Horizontal:
                mouse_position = event.pos().x()
            elif self.orientation == Qt.Orientation.Vertical:
                mouse_position = event.pos().y()

            if self._press_position is not None:
                manhattan_length = (event.pos() - self._press_position).manhattanLength()
                if manhattan_length >= Qw.QApplication.startDragDistance():
                    self._dragged_during_press = True

            # If this is None, there is no drag resize happening
            if self.header_being_resized is not None:
                size = self.initial_header_size + (mouse_position - self.resize_start_position)
                if size > 10:
                    if self.orientation == Qt.Orientation.Horizontal:
                        self.parent._set_column_width(self.header_being_resized, size)
                    if self.orientation == Qt.Orientation.Vertical:
                        self.setRowHeight(self.header_being_resized, size)
                        self.parent.dataView.setRowHeight(self.header_being_resized, size)

                    self.updateGeometry()
                    self.parent.dataView.updateGeometry()
                return True

            # Set the cursor shape
            if self.over_header_edge(mouse_position) is not None:
                if self.orientation == Qt.Orientation.Horizontal:
                    self.viewport().setCursor(Qg.QCursor(Qt.CursorShape.SplitHCursor))
                elif self.orientation == Qt.Orientation.Vertical:
                    self.viewport().setCursor(Qg.QCursor(Qt.CursorShape.SplitVCursor))
            else:
                self.viewport().setCursor(Qg.QCursor(Qt.CursorShape.ArrowCursor))

        return False

    # Return the size of the header needed to match the corresponding DataTableView
    def sizeHint(self):
        """Size hint."""
        return super().sizeHint()

    # This is needed because otherwise when the horizontal header is a single row it will add whitespace to be bigger
    def minimumSizeHint(self):
        """Minimum size hint."""
        if self.orientation == Qt.Orientation.Horizontal:
            return Qc.QSize(0, super().minimumSizeHint().height())
        return Qc.QSize(super().minimumSizeHint().width(), 0)

    def _show_context_menu(self, source_column: int, position: Qc.QPoint) -> None:
        """Show the column actions menu."""
        menu = Qw.QMenu(self)
        column_label = _column_label_to_text(self.proxy_model.df.columns[source_column])

        if self.parent.sortable:
            sort_ascending = menu.addAction(f"Sort {column_label} ascending")
            sort_ascending.triggered.connect(
                lambda _checked=False: self.parent.proxy_model.set_sort(source_column, Qt.SortOrder.AscendingOrder),
            )
            sort_ascending.triggered.connect(self.parent._refresh_after_proxy_change)
            sort_descending = menu.addAction(f"Sort {column_label} descending")
            sort_descending.triggered.connect(
                lambda _checked=False: self.parent.proxy_model.set_sort(source_column, Qt.SortOrder.DescendingOrder),
            )
            sort_descending.triggered.connect(self.parent._refresh_after_proxy_change)
            clear_sort = menu.addAction("Clear sort")
            clear_sort.triggered.connect(self.parent.clear_sorting)
            menu.addSeparator()

        if self.parent.filterable:
            filter_action = menu.addAction(f"Filter {column_label}...")
            filter_action.triggered.connect(lambda _checked=False: self._open_filter_dialog(source_column))
            clear_filter_action = menu.addAction("Clear filter")
            clear_filter_action.triggered.connect(lambda _checked=False: self._clear_filter(source_column))
            clear_all_filters_action = menu.addAction("Clear all filters")
            clear_all_filters_action.triggered.connect(self.parent.clear_filters)
            menu.addSeparator()

        if self.parent.column_visibility_control:
            hide_action = menu.addAction("Hide column")
            hide_action.setEnabled(len(self.parent.visible_columns()) > 1)
            hide_action.triggered.connect(lambda _checked=False: self.parent.set_column_visible(source_column, False))
            columns_action = menu.addAction("Choose columns...")
            columns_action.triggered.connect(self._open_column_visibility_dialog)

        menu.exec(position)

    def _clear_filter(self, source_column: int) -> None:
        """Clear a source column filter."""
        self.parent.proxy_model.clear_filter_for_column(source_column)
        self.parent._refresh_after_proxy_change()

    def _open_filter_dialog(self, source_column: int) -> None:
        """Open the filter dialog for a source column."""
        series = self.proxy_model.df.iloc[:, source_column]
        column_label = _column_label_to_text(self.proxy_model.df.columns[source_column])
        filter_state = self.proxy_model.filter_state_for_column(source_column)

        if _is_numeric_series(series):
            dialog = NumericColumnFilterDialog(self, column_label, ty.cast(NumericColumnFilter | None, filter_state))
            if dialog.exec() != Qw.QDialog.DialogCode.Accepted:
                return
            minimum, maximum, include_blanks = dialog.filter_values()
            self.parent.set_numeric_filter(
                source_column,
                minimum=minimum,
                maximum=maximum,
                include_blanks=include_blanks,
            )
            return

        dialog = StringColumnFilterDialog(
            self,
            column_label,
            self.proxy_model.distinct_values_for_column(source_column),
            ty.cast(StringColumnFilter | None, filter_state),
        )
        if dialog.exec() != Qw.QDialog.DialogCode.Accepted:
            return
        allowed_values, include_blanks = dialog.selected_values()
        self.parent.set_value_filter(source_column, allowed_values, include_blanks=include_blanks)

    def _open_column_visibility_dialog(self) -> None:
        """Open the column chooser dialog."""
        dialog = ColumnVisibilityDialog(self, self.proxy_model)
        if dialog.exec() != Qw.QDialog.DialogCode.Accepted:
            return

        checked_columns = dialog.checked_columns()
        if not checked_columns:
            return

        for column in range(self.proxy_model.df.columns.shape[0]):
            self.parent.proxy_model.set_column_visible(column, column in checked_columns)
        self.parent._refresh_after_proxy_change()

    def _show_row_context_menu(self, source_row: int, position: Qc.QPoint) -> None:
        """Show the row actions menu."""
        menu = Qw.QMenu(self)
        row_label = _row_label_to_text(self.proxy_model.df.index[source_row])
        hide_row_action = menu.addAction(f"Hide row {row_label}")
        hide_row_action.setEnabled(len(self.parent.visible_rows()) > 1)
        hide_row_action.triggered.connect(lambda _checked=False: self.parent.set_row_visible(source_row, False))

        selected_source_rows = self._selected_source_rows()
        hide_selected_rows_action = menu.addAction("Hide selected rows")
        hide_selected_rows_action.setEnabled(
            bool(selected_source_rows) and len(self.parent.visible_rows()) > len(selected_source_rows)
        )
        hide_selected_rows_action.triggered.connect(self._hide_selected_rows)

        choose_rows_action = menu.addAction("Choose rows...")
        choose_rows_action.triggered.connect(self._open_row_visibility_dialog)
        menu.exec(position)

    def _selected_source_rows(self) -> list[int]:
        """Return the currently selected source rows."""
        rows = sorted({index.row() for index in self.selectionModel().selectedIndexes()})
        return [self.proxy_model.source_row(row) for row in rows]

    def _hide_selected_rows(self) -> None:
        """Hide all selected visible rows while keeping at least one row visible."""
        selected_rows = self._selected_source_rows()
        if not selected_rows:
            return
        visible_rows = set(self.parent.visible_rows())
        rows_to_hide = [row for row in selected_rows if row in visible_rows]
        if len(visible_rows) <= len(rows_to_hide):
            rows_to_hide = rows_to_hide[:-1]
        for row in rows_to_hide:
            self.parent.proxy_model.set_row_visible(row, False)
        self.parent._refresh_after_proxy_change()

    def _open_row_visibility_dialog(self) -> None:
        """Open the row chooser dialog."""
        dialog = RowVisibilityDialog(self, self.proxy_model)
        if dialog.exec() != Qw.QDialog.DialogCode.Accepted:
            return
        checked_rows = dialog.checked_rows()
        if not checked_rows:
            return
        for row in range(self.proxy_model.df.index.shape[0]):
            self.parent.proxy_model.set_row_visible(row, row in checked_rows)
        self.parent._refresh_after_proxy_change()


# This is a fixed size widget with a size that tracks some other widget
class TrackingSpacer(Qw.QFrame):
    """Tracking spacer."""

    def __init__(self, ref_x=None, ref_y=None):
        super().__init__()
        self.ref_x = ref_x
        self.ref_y = ref_y
        self.setSizePolicy(Qw.QSizePolicy.Policy.Fixed, Qw.QSizePolicy.Policy.Fixed)

    def minimumSizeHint(self):
        """Minimize size hint."""
        width = 0
        height = 0
        if self.ref_x:
            width = self.ref_x.width()
        if self.ref_y:
            height = self.ref_y.height()

        return Qc.QSize(width, height)

    def sizeHint(self):
        """Keep the spacer aligned with the tracked widgets."""
        return self.minimumSizeHint()


# Examples
if __name__ == "__main__":  # pragma: no cover

    def _get_new_data() -> pd.DataFrame:
        shape = np.random.default_rng().integers(100, 10000, 2)
        df = pd.DataFrame(np.random.default_rng().integers(-255, 255, shape) / 255)
        df.columns = ["Column " + str(i) for i in range(df.shape[1])]
        frame.setWindowTitle(f"Shape {shape}")
        return df

    import sys

    from qtextra.utils.dev import qframe

    app, frame, va = qframe(False)
    frame.setMinimumSize(600, 600)

    df = _get_new_data()

    widget = QtDataFrameWidget(None, df)
    va.addWidget(widget, stretch=True)

    btn = Qw.QPushButton("Press me to change data")

    def _refresh_demo_data() -> None:
        widget.set_data(_get_new_data())

    btn.clicked.connect(_refresh_demo_data)
    va.addWidget(btn)

    frame.show()
    sys.exit(app.exec_())
