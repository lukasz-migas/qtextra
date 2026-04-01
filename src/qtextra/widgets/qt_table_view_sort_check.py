"""Alternative checkable table view using proxy-based sorting."""

from __future__ import annotations

import typing as ty
from numbers import Number

from natsort import natsort_keygen
from qtpy.QtCore import QModelIndex, QSortFilterProxyModel, Qt
from qtpy.QtWidgets import QTableView

from qtextra.utils.table_config import TableConfig
from qtextra.widgets.qt_table_view_check import (
    MultiColumnSingleValueProxyModel,
    QtCheckableItemModel,
    QtCheckableTableView,
)

__all__ = ("ProxySortFilterProxyModel", "QtProxySortCheckableTableView", "TableConfig")

_NATURAL_KEY = natsort_keygen()


class ProxySortFilterProxyModel(MultiColumnSingleValueProxyModel):
    """Filter proxy with proxy-based sorting for checkable tables."""

    def _raw_value(self, index: QModelIndex) -> ty.Any:
        source = self.sourceModel()
        return source.get_data()[index.row()][index.column()]

    def _sort_key(self, value: ty.Any) -> tuple[int, ty.Any]:
        if value is None:
            return (2, "")
        if isinstance(value, bool):
            return (0, int(value))
        if isinstance(value, Number) and not isinstance(value, complex):
            return (0, float(value))
        if isinstance(value, str):
            if any(char.isdigit() for char in value):
                return (1, _NATURAL_KEY(value))
            return (1, value.casefold())
        return (1, _NATURAL_KEY(str(value)))

    def lessThan(self, left: QModelIndex, right: QModelIndex) -> bool:
        """Check whether two indexes are sorted."""
        return self._sort_key(self._raw_value(left)) < self._sort_key(self._raw_value(right))


class QtProxySortCheckableTableView(QtCheckableTableView):
    """Alternative checkable table view that leaves source rows unsorted."""

    _proxy_model: ProxySortFilterProxyModel | QSortFilterProxyModel | None

    def __init__(self, *args: ty.Any, **kwargs: ty.Any):
        self._proxy_model = None
        super().__init__(*args, **kwargs)

    def visible_model(self) -> QtCheckableItemModel | QSortFilterProxyModel | None:
        """Return the model installed on the view."""
        return QTableView.model(self)

    def proxy_model(self) -> ProxySortFilterProxyModel | QSortFilterProxyModel | None:
        """Return the proxy model installed on the view, if any."""
        model = self.visible_model()
        return model if isinstance(model, QSortFilterProxyModel) else None

    def proxy_or_model(self) -> QtCheckableItemModel | QSortFilterProxyModel:
        """Return the active visible model."""
        model = self.visible_model()
        if model is None:
            return self.model()
        return model

    def is_proxy(self) -> bool:
        """Return True if a proxy model is installed."""
        return isinstance(self.visible_model(), QSortFilterProxyModel)

    def _source_row_from_view_row(self, row: int) -> int:
        proxy = self.proxy_model()
        if proxy is None:
            return row
        proxy_index = proxy.index(row, 0)
        if not proxy_index.isValid():
            return row
        return proxy.mapToSource(proxy_index).row()

    def _view_row_from_source_row(self, row: int) -> int:
        proxy = self.proxy_model()
        if proxy is None:
            return row
        source_index = self.model().index(row, 0)
        proxy_index = proxy.mapFromSource(source_index)
        return proxy_index.row() if proxy_index.isValid() else row

    def _visible_rows(self) -> list[int]:
        proxy = self.proxy_model()
        if proxy is None:
            return list(range(self.n_rows))
        return [self._source_row_from_view_row(row) for row in range(proxy.rowCount())]

    def _resolve_row_for_update(self, row: int, match_to_sort: bool) -> int:
        if not self.is_proxy():
            return row
        return row if match_to_sort else self._source_row_from_view_row(row)

    def set_proxy_model(self, proxy: QSortFilterProxyModel | None = None) -> None:
        """Install a proxy model for sorting/filtering."""
        source_model = self.model()
        if proxy is None:
            proxy = ProxySortFilterProxyModel(self)
        proxy.setSourceModel(source_model)
        source_model.table_proxy = proxy  # used by bulk row actions
        self._proxy_model = proxy
        QTableView.setModel(self, proxy)

    def set_model(self, model: QtCheckableItemModel) -> None:
        """Set source model and install a sorting proxy."""
        if self._config:
            model.icon_columns = self._config.icon_columns
            model.color_columns = self._config.color_columns
            model.html_columns = self._config.html_columns
            model.no_sort_columns = self._config.no_sort_columns
            model.hidden_columns = self._config.hidden_columns
            model.checkable_columns = self._config.checkable_columns
            model.text_alignment = {
                "left": Qt.AlignmentFlag.AlignLeft,
                "center": Qt.AlignmentFlag.AlignCenter,
                "right": Qt.AlignmentFlag.AlignRight,
            }[self._config.text_alignment]
        if self._sortable:
            self._proxy_model = ProxySortFilterProxyModel(self)
            self._proxy_model.setSourceModel(model)
            model.table_proxy = self._proxy_model
            QTableView.setModel(self, self._proxy_model)
            return
        model.table_proxy = None
        self._proxy_model = None
        QTableView.setModel(self, model)

    def get_data(self) -> list[list]:
        """Get current data in visible row order."""
        source = self.model()
        return [source.get_data()[row] for row in self._visible_rows()]

    def get_col_data(self, col_id: int) -> list[ty.Any]:
        """Get visible column data in the current sort/filter order."""
        if col_id >= self.n_cols:
            return self.get_data()
        source = self.model().get_data()
        return [source[row][col_id] for row in self._visible_rows()]

    def get_row_data(self, row_id: int) -> list:
        """Get visible row data."""
        rows = self._visible_rows()
        if row_id >= len(rows):
            return self.model().get_data()
        return self.model().get_data()[rows[row_id]]

    def get_value(self, col_id: int, row_id: int) -> ty.Any:
        """Get a visible cell value."""
        rows = self._visible_rows()
        if row_id >= len(rows) or col_id >= self.n_cols:
            return self.model().get_data()
        return self.model().get_data()[rows[row_id]][col_id]

    def set_value(self, col_id: int, row_id: int, value: ty.Any) -> None:
        """Set value using visible row indexing."""
        self.model().update_value(self._source_row_from_view_row(row_id), col_id, value)

    def select_row(self, row: int, match_to_sort: bool = True) -> None:
        """Select row."""
        if self.is_proxy() and match_to_sort:
            row = self._view_row_from_source_row(row)
        self.selectRow(row)

    def update_value(self, row: int, col: int, value: ty.Any, match_to_sort: bool = True) -> None:
        """Update value in the model."""
        self.model().update_value(self._resolve_row_for_update(row, match_to_sort), col, value)

    def update_values(
        self,
        row: int,
        column_value: dict[int, str | int | float | bool],
        match_to_sort: bool = True,
    ) -> None:
        """Update multiple columns for a particular row."""
        self.model().update_values(self._resolve_row_for_update(row, match_to_sort), column_value)

    def update_row(self, row: int, value: list, match_to_sort: bool = True) -> None:
        """Update entire row."""
        self.model().update_row(self._resolve_row_for_update(row, match_to_sort), value)

    def remove_row(self, row_id: int, match_to_sort: bool = False) -> None:
        """Remove row from the model."""
        self.model().removeRow(self._resolve_row_for_update(row_id, match_to_sort))

    def remove_rows(self, rows: list[int], match_to_sort: bool = False) -> None:
        """Remove rows from the model."""
        resolved_rows = sorted((self._resolve_row_for_update(row, match_to_sort) for row in rows), reverse=True)
        for row in resolved_rows:
            self.model().removeRow(row)
