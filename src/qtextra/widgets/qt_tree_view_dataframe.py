"""Grouped (tree) view of a pandas DataFrame with sortable, filterable and colourable columns.

`QtDataFrameTreeWidget` is the tree counterpart of `QtDataFrameWidget`. Rows of the DataFrame are the leaves of the tree
and are grouped by one or more columns. Group rows show values aggregated from their *visible* children, so they always
agree with the active filters. Filters, sorting, column visibility and cell colours behave like in `QtDataFrameWidget`
and reuse its dialogs.

The model keeps no Python objects per leaf: visibility, sorting and aggregation are computed with numpy/pandas on
every refresh, which keeps the widget responsive for 10^5 rows.
"""

from __future__ import annotations

import contextlib
import typing as ty
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
import qtpy.QtCore as Qc
import qtpy.QtGui as Qg
import qtpy.QtWidgets as Qw
from qtpy.QtCore import QModelIndex, Qt, Signal

from qtextra.widgets._qt_table_models import is_float_like
from qtextra.widgets.qt_table_view_dataframe import (
    ASCENDING_SORT_INDICATOR,
    DESCENDING_SORT_INDICATOR,
    ColumnFormatters,
    ColumnVisibilityDialog,
    NumericColumnFilter,
    NumericColumnFilterDialog,
    StringColumnFilter,
    StringColumnFilterDialog,
    _column_label_to_text,
    _foreground_from_background,
    _format_cell_value,
    _is_numeric_series,
    _normalize_tabular_data,
    _rgba_array_from_colormap,
)

TREE_COLUMN = -1  # model-level identifier of the first (tree) column
DEFAULT_TREE_COLUMN_WIDTH = 280
DEFAULT_COLUMN_WIDTH = 100
MAX_INITIAL_COLUMN_WIDTH = 260
Aggregation = str | ty.Callable[[pd.Series], ty.Any]
_UNSET: ty.Any = object()  # "keep the current grouping"
AGGREGATIONS = ("mean", "median", "min", "max", "sum", "first", "last", "count", "nunique", "join", "std")


@dataclass(slots=True)
class _Node:
    """Group node; the root has id 0 and depth 0."""

    id: int
    parent: int
    depth: int
    key: tuple
    groups: list[int] = field(default_factory=list)
    leaves: np.ndarray = field(default_factory=lambda: np.empty(0, dtype=np.intp))
    visible: np.ndarray = field(default_factory=lambda: np.empty(0, dtype=np.intp))
    row: int = 0

    @property
    def has_group_children(self) -> bool:
        return bool(self.groups)


@dataclass(slots=True, frozen=True)
class TreeSelection:
    """Item of the tree: a leaf (one source row) or a group (all of its visible source rows)."""

    is_group: bool
    source_rows: np.ndarray
    group_key: tuple | None = None
    depth: int = 0

    @property
    def source_row(self) -> int | None:
        """Source row of a leaf, or `None` for a group."""
        return None if self.is_group or self.source_rows.size == 0 else int(self.source_rows[0])


@dataclass(slots=True)
class _ColorRule:
    kind: ty.Literal["numeric", "categorical"]
    cmap: ty.Any
    norm: ty.Any = None
    mapping: dict[str, np.ndarray] = field(default_factory=dict)


class DataFrameTreeModel(Qc.QAbstractItemModel):
    """Tree model over a DataFrame with grouping, leaf filters, sorting, aggregation and colours.

    Column 0 is the tree column (group keys or the leaf label); the following columns are the visible DataFrame
    columns. Filters always apply to leaves; a group is shown when any descendant leaf is shown and its values are
    aggregated from the visible descendants.
    """

    evt_refreshed = Signal()

    def __init__(
        self,
        df: pd.DataFrame | None = None,
        *,
        group_by: ty.Sequence[str] | str | None = None,
        aggregations: ty.Mapping[str, Aggregation] | None = None,
        label_column: str | None = None,
        group_label_column: str | None = None,
        column_formatters: ColumnFormatters | None = None,
        tree_column_title: str | None = None,
        parent: Qc.QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._df = pd.DataFrame()
        self._values = np.empty((0, 0), dtype=object)
        self._group_by: list[str] = []
        self._aggregations: dict[str, Aggregation] = dict(aggregations or {})
        self._label_column = label_column
        self._group_label_column = group_label_column
        self._formatters_spec: ColumnFormatters = dict(column_formatters or {})
        self._formatters: dict[int, ty.Any] = {}
        self._tree_column_title = tree_column_title

        self._nodes: list[_Node] = [_Node(0, -1, 0, ())]
        self._leaf_parent = np.empty(0, dtype=np.intp)
        self._leaf_ancestors: list[np.ndarray] = []  # per depth (1..L): ancestor node id of every row
        self._depth_nodes: list[np.ndarray] = []  # per depth (1..L): node ids
        self._node_parent = np.zeros(1, dtype=np.intp)

        self._column_filters: dict[int, NumericColumnFilter | StringColumnFilter] = {}
        self._row_mask: np.ndarray | None = None
        self._hidden_rows: set[int] = set()
        self._visible_columns: list[int] = []
        self._sort_column: int | None = None  # source column, TREE_COLUMN or None
        self._sort_order: Qt.SortOrder | None = None

        self._leaf_mask = np.empty(0, dtype=bool)
        self._counts = np.zeros(1, dtype=np.intp)
        self._aggregates: dict[int, np.ndarray] = {}
        self._color_rules: dict[int, _ColorRule] = {}
        self._leaf_colors: dict[int, tuple[np.ndarray, np.ndarray]] = {}
        self._group_colors: dict[int, tuple[np.ndarray, np.ndarray]] = {}
        self._row_background: tuple[np.ndarray, np.ndarray] | None = None
        self._bold_font = Qg.QFont()
        self._bold_font.setBold(True)
        self._filtered_header_font = Qg.QFont()
        self._filtered_header_font.setItalic(True)
        self._filtered_header_font.setBold(True)

        self.set_data(df if df is not None else pd.DataFrame(), group_by=group_by)

    # ----------------------------------------------------------------------------------------------------------------
    # Data and structure
    # ----------------------------------------------------------------------------------------------------------------
    @property
    def df(self) -> pd.DataFrame:
        """Source DataFrame."""
        return self._df

    @property
    def group_by(self) -> list[str]:
        """Grouping columns, outermost first."""
        return list(self._group_by)

    @property
    def sort_column(self) -> int | None:
        """Sorted source column, `TREE_COLUMN` for the tree column, or `None`."""
        return self._sort_column

    @property
    def sort_order(self) -> Qt.SortOrder | None:
        """Active sort order."""
        return self._sort_order

    def set_data(
        self,
        df: ty.Any,
        *,
        group_by: ty.Sequence[str] | str | None = _UNSET,
        aggregations: ty.Mapping[str, Aggregation] | None = None,
        column_formatters: ColumnFormatters | None = None,
        keep_state: bool = True,
    ) -> None:
        """Replace the DataFrame.

        View state (filters, sorting, visible columns and colour rules) is kept when `keep_state` is True and the
        columns are unchanged. Omitting `group_by` keeps the current grouping; `None` shows a flat list.
        """
        df = _normalize_tabular_data(df).reset_index(drop=True)
        same_columns = keep_state and list(df.columns) == list(self._df.columns)
        if aggregations is not None:
            self._aggregations = dict(aggregations)
        if column_formatters is not None:
            self._formatters_spec = dict(column_formatters)
        previous_rules = {
            _column_label_to_text(self._df.columns[column]): rule for column, rule in self._color_rules.items()
        }

        self.beginResetModel()
        self._df = df
        self._values = df.to_numpy(copy=False) if df.shape[1] else np.empty((len(df), 0), dtype=object)
        self._formatters = self._resolve_formatters()
        self._row_mask = None
        self._hidden_rows = set()
        self._row_background = None
        if not same_columns:
            self._column_filters = {}
            self._sort_column = None
            self._sort_order = None
            self._visible_columns = []
        self._build_structure((self._group_by if keep_state else None) if group_by is _UNSET else group_by)
        if not same_columns:
            self._visible_columns = self._default_visible_columns()
        self._color_rules = {}
        self._leaf_colors = {}
        for name, rule in previous_rules.items():
            if same_columns and name in self._column_names():
                self._apply_rule(self._column_names().index(name), rule)
        self._refresh(reset=False)
        self.endResetModel()
        self.evt_refreshed.emit()

    def set_group_by(self, group_by: ty.Sequence[str] | str | None) -> None:
        """Regroup the rows, keeping filters, sorting and colours."""
        self.beginResetModel()
        hidden_before = set(self._group_by) | ({self._label_column} if self._label_column else set())
        self._build_structure(group_by)
        hidden_now = set(self._group_by) | ({self._label_column} if self._label_column else set())
        names = self._column_names()
        visible = {names[column] for column in self._visible_columns}
        visible |= {name for name in hidden_before - hidden_now if name in names}
        visible -= hidden_now
        self._visible_columns = [index for index, name in enumerate(names) if name in visible] or self._visible_columns
        self._refresh(reset=False)
        self.endResetModel()
        self.evt_refreshed.emit()

    def _column_names(self) -> list[str]:
        return [_column_label_to_text(column) for column in self._df.columns]

    def _column_index(self, column: int | str) -> int:
        if isinstance(column, str):
            names = self._column_names()
            if column not in names:
                raise KeyError(f"Unknown column '{column}'.")
            return names.index(column)
        return int(column)

    def _resolve_formatters(self) -> dict[int, ty.Any]:
        resolved: dict[int, ty.Any] = {}
        names = self._column_names()
        for column, formatter in self._formatters_spec.items():
            if isinstance(column, str):
                if column in names:
                    resolved[names.index(column)] = formatter
            elif 0 <= column < len(names):
                resolved[int(column)] = formatter
        return resolved

    def _default_visible_columns(self) -> list[int]:
        hidden = set(self._group_by) | ({self._label_column} if self._label_column else set())
        visible = [index for index, name in enumerate(self._column_names()) if name not in hidden]
        return visible or list(range(self._df.shape[1]))

    def _build_structure(self, group_by: ty.Sequence[str] | str | None) -> None:
        """Build group nodes for `group_by` columns."""
        if isinstance(group_by, str):
            group_by = [group_by]
        names = self._column_names()
        self._group_by = [column for column in (group_by or []) if column in names]
        n_rows = len(self._df)
        root = _Node(0, -1, 0, ())
        self._nodes = [root]
        self._leaf_ancestors = []
        self._depth_nodes = []
        if not self._group_by or n_rows == 0:
            root.leaves = np.arange(n_rows, dtype=np.intp)
            self._leaf_parent = np.zeros(n_rows, dtype=np.intp)
            self._node_parent = np.full(1, -1, dtype=np.intp)
            return

        previous = np.zeros(n_rows, dtype=np.intp)
        for depth in range(1, len(self._group_by) + 1):
            keys = self._group_by[:depth]
            codes = self._df.groupby(keys, sort=False, dropna=False).ngroup().to_numpy()
            n_groups = int(codes.max()) + 1 if codes.size else 0
            offset = len(self._nodes)
            first_rows = np.full(n_groups, -1, dtype=np.intp)
            # first row of every group (first appearance)
            order = np.argsort(codes, kind="stable")
            starts = np.r_[0, np.flatnonzero(np.diff(codes[order])) + 1]
            first_rows[codes[order[starts]]] = order[starts]
            key_values = self._df[keys].to_numpy(dtype=object)
            ids = np.arange(offset, offset + n_groups, dtype=np.intp)
            for code in range(n_groups):
                row = first_rows[code]
                parent_id = int(previous[row])
                node = _Node(int(ids[code]), parent_id, depth, tuple(key_values[row]))
                self._nodes.append(node)
                self._nodes[parent_id].groups.append(node.id)
            ancestors = ids[codes]
            self._leaf_ancestors.append(ancestors)
            self._depth_nodes.append(ids)
            previous = ancestors
        self._leaf_parent = previous
        order = np.argsort(previous, kind="stable")
        sorted_parents = previous[order]
        boundaries = np.flatnonzero(np.diff(sorted_parents)) + 1
        for chunk in np.split(order, boundaries):
            if chunk.size:
                self._nodes[int(previous[chunk[0]])].leaves = chunk.astype(np.intp)
        self._node_parent = np.asarray([node.parent for node in self._nodes], dtype=np.intp)

    # ----------------------------------------------------------------------------------------------------------------
    # Filtering, sorting, aggregation
    # ----------------------------------------------------------------------------------------------------------------
    def refresh(self) -> None:
        """Recompute visibility, order, aggregates and colours."""
        self._refresh(reset=True)

    def _refresh(self, reset: bool = True) -> None:
        if reset:
            self.beginResetModel()
        n_rows = len(self._df)
        self._leaf_mask = self._filtered_mask()
        visible_rows = np.flatnonzero(self._leaf_mask)
        n_nodes = len(self._nodes)

        # counts of visible descendants
        counts = np.zeros(n_nodes, dtype=np.intp)
        counts[0] = visible_rows.size
        for ancestors in self._leaf_ancestors:
            counts += np.bincount(ancestors[visible_rows], minlength=n_nodes) if visible_rows.size else 0
        self._counts = counts

        # aggregates of the visible descendants (only for columns that are shown, sorted or coloured)
        self._aggregates = {}
        if self._leaf_ancestors:
            needed = set(self._visible_columns) | set(self._color_rules)
            if self._sort_column is not None and self._sort_column != TREE_COLUMN:
                needed.add(self._sort_column)
            for column in sorted(needed):
                self._aggregates[column] = self._aggregate_column(column, visible_rows, n_nodes)

        # leaf order inside each parent
        if visible_rows.size and self._sort_column is not None and self._sort_order is not None:
            keys = self._sort_keys_for_rows(visible_rows)
            order = keys.sort_values(
                ascending=self._sort_order == Qt.SortOrder.AscendingOrder, kind="mergesort", na_position="last"
            ).index.to_numpy()
            visible_rows = visible_rows[order]
        parents = self._leaf_parent[visible_rows] if n_rows else np.empty(0, dtype=np.intp)
        grouped = visible_rows[np.argsort(parents, kind="stable")]
        sorted_parents = self._leaf_parent[grouped]
        for node in self._nodes:
            if not node.groups:
                node.visible = np.empty(0, dtype=np.intp)
        if grouped.size:
            boundaries = np.flatnonzero(np.diff(sorted_parents)) + 1
            for chunk in np.split(grouped, boundaries):
                self._nodes[int(self._leaf_parent[chunk[0]])].visible = chunk

        # group order inside each parent
        for ids in self._depth_nodes:
            shown = ids[counts[ids] > 0]
            if shown.size and self._sort_column is not None and self._sort_order is not None:
                keys = self._sort_keys_for_groups(shown)
                order = keys.sort_values(
                    ascending=self._sort_order == Qt.SortOrder.AscendingOrder, kind="mergesort", na_position="last"
                ).index.to_numpy()
                shown = shown[order]
            shown = shown[np.argsort(self._node_parent[shown], kind="stable")]
            parent_ids = {self._nodes[int(node_id)].parent for node_id in ids}
            for parent_id in parent_ids:
                self._nodes[parent_id].visible = np.empty(0, dtype=np.intp)
            if shown.size:
                boundaries = np.flatnonzero(np.diff(self._node_parent[shown])) + 1
                for chunk in np.split(shown, boundaries):
                    parent = self._nodes[int(self._node_parent[chunk[0]])]
                    parent.visible = chunk
                    for position, node_id in enumerate(chunk):
                        self._nodes[int(node_id)].row = position

        self._group_colors = {column: self._group_rgba(column, rule) for column, rule in self._color_rules.items()}
        if reset:
            self.endResetModel()
            self.evt_refreshed.emit()

    def _filtered_mask(self, exclude_column: int | None = None) -> np.ndarray:
        """Return the leaf rows passing column filters, the row mask and row hiding."""
        n_rows = len(self._df)
        mask = np.ones(n_rows, dtype=bool)
        for column, state in self._column_filters.items():
            if column == exclude_column:
                continue
            series = self._df.iloc[:, column]
            blank = series.isna().to_numpy()
            if isinstance(state, NumericColumnFilter):
                column_mask = np.ones(n_rows, dtype=bool)
                values = pd.to_numeric(series, errors="coerce")
                if state.minimum is not None:
                    column_mask &= (values >= state.minimum).fillna(False).to_numpy(dtype=bool)
                if state.maximum is not None:
                    column_mask &= (values <= state.maximum).fillna(False).to_numpy(dtype=bool)
            elif state.allowed_values:
                column_mask = np.zeros(n_rows, dtype=bool)
                column_mask[~blank] = series[~blank].astype(str).isin(state.allowed_values).to_numpy(dtype=bool)
            else:
                column_mask = np.ones(n_rows, dtype=bool)
            column_mask = (column_mask | blank) if state.include_blanks else (column_mask & ~blank)
            mask &= column_mask
        if self._row_mask is not None:
            mask &= self._row_mask
        if self._hidden_rows:
            hidden = np.fromiter((row for row in self._hidden_rows if row < n_rows), dtype=np.intp)
            mask[hidden] = False
        return mask

    def _sort_keys_for_rows(self, rows: np.ndarray) -> pd.Series:
        column = self._sort_column
        if column == TREE_COLUMN:
            column = self._label_index()
        if column is None:
            return pd.Series(np.arange(rows.size))
        return self._df.iloc[rows, column].reset_index(drop=True)

    def _sort_keys_for_groups(self, node_ids: np.ndarray) -> pd.Series:
        if self._sort_column == TREE_COLUMN:
            return pd.Series([self._group_text(self._nodes[int(node_id)]) for node_id in node_ids]).str.casefold()
        values = self._aggregates.get(ty.cast(int, self._sort_column))
        if values is None:
            return pd.Series(np.arange(node_ids.size))
        series = pd.Series(values[node_ids])
        numeric = pd.to_numeric(series, errors="coerce")
        return numeric if numeric.notna().any() or series.isna().all() else series.astype(str).str.casefold()

    def _aggregate_column(self, column: int, rows: np.ndarray, n_nodes: int) -> np.ndarray:
        """Aggregate one column over the visible descendants of every group node."""
        series = self._df.iloc[:, column]
        numeric = _is_numeric_series(series)
        name = self._column_names()[column]
        func = self._aggregations.get(name, "mean" if numeric else None)
        out = np.full(n_nodes, None, dtype=object)
        if rows.size:
            values = series.iloc[rows].reset_index(drop=True)
            for ancestors in self._leaf_ancestors:
                grouped = values.groupby(ancestors[rows], sort=False)
                result = self._apply_aggregation(grouped, func, numeric)
                out[result.index.to_numpy(dtype=np.intp)] = result.to_numpy(dtype=object)
        filled = out[out != None]  # noqa: E711 - element-wise comparison
        is_number = [isinstance(value, (int, float, np.number)) and not isinstance(value, bool) for value in filled]
        is_integer = [isinstance(value, (int, np.integer)) and not isinstance(value, bool) for value in filled]
        if all(is_number) and not all(is_integer):  # counts stay integers (object array, `None` for empty groups)
            return np.asarray([np.nan if value is None else value for value in out], dtype=float)
        return out

    @staticmethod
    def _apply_aggregation(grouped: ty.Any, func: Aggregation | None, numeric: bool) -> pd.Series:
        if callable(func):
            return grouped.agg(func)
        if func == "join":
            return grouped.agg(
                lambda values: "; ".join(dict.fromkeys(str(value) for value in values if not pd.isna(value)))
            )
        if func in AGGREGATIONS:
            try:
                return getattr(grouped, func)()
            except (TypeError, ValueError):
                pass
        if numeric and func is None:
            return grouped.mean()
        unique = grouped.nunique(dropna=True)
        first = grouped.first()
        return pd.Series(
            np.where(unique.to_numpy() <= 1, first.to_numpy(dtype=object), [f"{n} values" for n in unique.to_numpy()]),
            index=first.index,
            dtype=object,
        )

    # ----------------------------------------------------------------------------------------------------------------
    # Public view-state API (mirrors DataFrameProxyModel)
    # ----------------------------------------------------------------------------------------------------------------
    def set_row_mask(self, mask: np.ndarray | None) -> None:
        """Show only leaves where `mask` is True (an additional, external filter)."""
        if mask is not None:
            mask = np.asarray(mask, dtype=bool)
            if mask.shape != (len(self._df),):
                raise ValueError("Row mask must have one value per DataFrame row.")
        self._row_mask = mask
        self.refresh()

    def set_sort(self, column: int | None, order: Qt.SortOrder | None) -> None:
        """Sort by a source column (`TREE_COLUMN` for the tree column) or clear sorting with `None`."""
        self._sort_column = column if order is not None else None
        self._sort_order = order if column is not None else None
        self.refresh()

    def toggle_sort(self, column: int) -> None:
        """Cycle ascending, descending and unsorted for a column."""
        if self._sort_column != column:
            self.set_sort(column, Qt.SortOrder.AscendingOrder)
        elif self._sort_order == Qt.SortOrder.AscendingOrder:
            self.set_sort(column, Qt.SortOrder.DescendingOrder)
        else:
            self.set_sort(None, None)

    def clear_sorting(self) -> None:
        """Restore the source order."""
        self.set_sort(None, None)

    def set_numeric_filter(
        self,
        column: int | str,
        *,
        minimum: float | None = None,
        maximum: float | None = None,
        include_blanks: bool = True,
    ) -> None:
        """Filter leaves by a numeric range."""
        column = self._column_index(column)
        state = NumericColumnFilter(minimum=minimum, maximum=maximum, include_blanks=include_blanks)
        self._set_filter(column, state)

    def set_string_filter(
        self, column: int | str, *, allowed_values: ty.Iterable[str] | None = None, include_blanks: bool = True
    ) -> None:
        """Filter leaves by a set of allowed values."""
        column = self._column_index(column)
        state = StringColumnFilter(
            allowed_values={str(value) for value in allowed_values or []}, include_blanks=include_blanks
        )
        self._set_filter(column, state)

    def _set_filter(self, column: int, state: NumericColumnFilter | StringColumnFilter) -> None:
        if state.is_active():
            self._column_filters[column] = state
        else:
            self._column_filters.pop(column, None)
        self.refresh()

    def clear_filter_for_column(self, column: int | str) -> None:
        """Remove the filter of one column."""
        self._column_filters.pop(self._column_index(column), None)
        self.refresh()

    def clear_filters(self) -> None:
        """Remove all column filters (the row mask is kept)."""
        self._column_filters.clear()
        self.refresh()

    def is_column_filtered(self, column: int) -> bool:
        """Return whether a source column has an active filter."""
        state = self._column_filters.get(column)
        return state.is_active() if state is not None else False

    def filter_state_for_column(self, column: int) -> NumericColumnFilter | StringColumnFilter | None:
        """Return the filter state of a source column."""
        return self._column_filters.get(column)

    def distinct_values_for_column(self, column: int) -> list[str]:
        """Return distinct non-blank values of a column among rows passing the other filters."""
        rows = np.flatnonzero(self._filtered_mask(exclude_column=column))
        series = self._df.iloc[rows, column]
        return sorted({str(value) for value in series if not pd.isna(value)}, key=str.casefold)

    def is_column_visible(self, column: int) -> bool:
        """Return whether a source column is shown."""
        return column in self._visible_columns

    @property
    def visible_columns(self) -> list[int]:
        """Shown source columns, in display order."""
        return list(self._visible_columns)

    def set_visible_columns(self, columns: ty.Iterable[int | str]) -> None:
        """Show exactly `columns` (source order is kept)."""
        wanted = {self._column_index(column) for column in columns}
        self._visible_columns = [column for column in range(self._df.shape[1]) if column in wanted]
        self.refresh()

    def set_column_visible(self, column: int | str, visible: bool) -> bool:
        """Show or hide one source column; the last visible column cannot be hidden."""
        column = self._column_index(column)
        if visible and column not in self._visible_columns:
            self._visible_columns = sorted([*self._visible_columns, column])
        elif not visible and column in self._visible_columns:
            if len(self._visible_columns) <= 1:
                return False
            self._visible_columns.remove(column)
        else:
            return True
        self.refresh()
        return True

    def set_row_hidden(self, row: int, hidden: bool) -> None:
        """Hide or show one source row."""
        if hidden:
            self._hidden_rows.add(int(row))
        else:
            self._hidden_rows.discard(int(row))
        self.refresh()

    # ----------------------------------------------------------------------------------------------------------------
    # Colours
    # ----------------------------------------------------------------------------------------------------------------
    def color_numeric(
        self,
        column: int | str,
        colormap: str = "RdBu_r",
        vmin: float | None = None,
        vmax: float | None = None,
        vcenter: float | None = 0.0,
        log: bool = False,
    ) -> None:
        """Colour a numeric column; leaves and groups share one normalization computed from the leaves.

        With `log=True` the colours follow log10 of the values (useful for intensities spanning orders of
        magnitude); non-positive values are left uncoloured and `vcenter` is ignored.
        """
        import matplotlib.colors
        from matplotlib.pyplot import get_cmap

        column = self._column_index(column)
        values = pd.to_numeric(self._df.iloc[:, column], errors="coerce").to_numpy(np.float64)
        valid = values[np.isfinite(values) & (values > 0)] if log else values[np.isfinite(values)]
        if valid.size == 0:
            self.clear_colors(column)
            return
        low = float(valid.min()) if vmin is None else float(vmin)
        high = float(valid.max()) if vmax is None else float(vmax)
        if low == high:
            low, high = low - 1.0, high + 1.0
        if log:
            low = max(low, float(valid.min()))
            norm = matplotlib.colors.LogNorm(vmin=low, vmax=max(high, low * 10), clip=True)
        elif vcenter is not None:
            norm = matplotlib.colors.TwoSlopeNorm(
                vmin=low, vcenter=float(np.clip(vcenter, low + 1e-9, high - 1e-9)), vmax=high
            )
        else:
            norm = matplotlib.colors.Normalize(vmin=low, vmax=high, clip=True)
        self._apply_rule(column, _ColorRule("numeric", get_cmap(colormap), norm=norm))
        self._update_colors(column)

    def color_categorical(self, column: int | str, colormap: str = "tab20") -> None:
        """Give every distinct value of a column its own colour."""
        from matplotlib.pyplot import get_cmap

        column = self._column_index(column)
        cmap = get_cmap(colormap)
        series = self._df.iloc[:, column]
        unique = list(pd.unique(series[series.notna()].astype(str)))
        positions = np.linspace(0.0, 1.0, max(len(unique), 2))[: len(unique)]
        mapping = {
            value: (np.asarray(cmap(position)) * 255).astype(np.uint8) for value, position in zip(unique, positions)
        }
        self._apply_rule(column, _ColorRule("categorical", cmap, mapping=mapping))
        self._update_colors(column)

    def color_table(self, colormap_numeric: str = "RdBu_r", colormap_categorical: str = "tab20") -> None:
        """Colour every visible column."""
        for column in self._visible_columns:
            if _is_numeric_series(self._df.iloc[:, column]):
                self.color_numeric(column, colormap=colormap_numeric)
            else:
                self.color_categorical(column, colormap=colormap_categorical)

    def clear_colors(self, column: int | str | None = None) -> None:
        """Remove the colours of one column or of all columns."""
        columns = list(self._color_rules) if column is None else [self._column_index(column)]
        for index in columns:
            self._color_rules.pop(index, None)
            self._leaf_colors.pop(index, None)
            self._group_colors.pop(index, None)
        self._emit_all_changed()

    def set_row_background(self, rgba: np.ndarray | None) -> None:
        """Paint whole leaf rows (e.g. by state) with an (N, 4) uint8 RGBA array; alpha 0 means no colour."""
        if rgba is None:
            self._row_background = None
        else:
            rgba = np.asarray(rgba, dtype=np.uint8)
            if rgba.shape != (len(self._df), 4):
                raise ValueError("Row colours must be an (n_rows, 4) RGBA array.")
            self._row_background = (rgba, _foreground_from_background(rgba))
        self._emit_all_changed()

    def leaf_colors(self, column: int | str) -> np.ndarray | None:
        """Background RGBA of every leaf in a coloured column."""
        colors = self._leaf_colors.get(self._column_index(column))
        return None if colors is None else colors[0]

    def group_colors(self, column: int | str) -> np.ndarray | None:
        """Background RGBA of every group node in a coloured column (indexed by node id)."""
        colors = self._group_colors.get(self._column_index(column))
        return None if colors is None else colors[0]

    def _apply_rule(self, column: int, rule: _ColorRule) -> None:
        self._color_rules[column] = rule
        background = self._rgba(rule, self._df.iloc[:, column].to_numpy())
        self._leaf_colors[column] = (background, _foreground_from_background(background))

    def _update_colors(self, column: int) -> None:
        if self._leaf_ancestors and column not in self._aggregates:
            self.refresh()
            return
        self._group_colors[column] = self._group_rgba(column, self._color_rules[column])
        self._emit_all_changed()

    def _group_rgba(self, column: int, rule: _ColorRule) -> tuple[np.ndarray, np.ndarray]:
        values = self._aggregates.get(column)
        if values is None:
            empty = np.zeros((len(self._nodes), 4), dtype=np.uint8)
            return empty, empty
        background = self._rgba(rule, values)
        return background, _foreground_from_background(background)

    @staticmethod
    def _rgba(rule: _ColorRule, values: np.ndarray) -> np.ndarray:
        if rule.kind == "numeric":
            floats = pd.to_numeric(pd.Series(values), errors="coerce").to_numpy(np.float64)
            return _rgba_array_from_colormap(floats, rule.norm, rule.cmap)
        background = np.zeros((len(values), 4), dtype=np.uint8)
        for index, value in enumerate(values):
            if value is not None and not (isinstance(value, float) and np.isnan(value)):
                color = rule.mapping.get(str(value))
                if color is not None:
                    background[index] = color
        return background

    def _emit_all_changed(self) -> None:
        """Repaint every cell after a colour change (the structure is unchanged)."""
        self.layoutAboutToBeChanged.emit()
        self.layoutChanged.emit()

    # ----------------------------------------------------------------------------------------------------------------
    # Mapping helpers
    # ----------------------------------------------------------------------------------------------------------------
    def _resolve(self, index: QModelIndex) -> tuple[bool, int]:
        """Return `(is_group, node_id_or_source_row)` for a valid index."""
        parent = self._nodes[int(index.internalId())]
        value = int(parent.visible[index.row()])
        return (True, value) if parent.has_group_children else (False, value)

    def is_group(self, index: QModelIndex) -> bool:
        """Return whether `index` is a group row."""
        return index.isValid() and self._resolve(index)[0]

    def source_rows(self, index: QModelIndex) -> np.ndarray:
        """Source row of a leaf, or all visible descendant rows of a group (in display order)."""
        if not index.isValid():
            return np.empty(0, dtype=np.intp)
        is_group, value = self._resolve(index)
        return self._descendant_rows(value) if is_group else np.asarray([value], dtype=np.intp)

    def selection(self, index: QModelIndex) -> TreeSelection | None:
        """Describe the item at `index`."""
        if not index.isValid():
            return None
        is_group, value = self._resolve(index)
        if is_group:
            node = self._nodes[value]
            return TreeSelection(True, self._descendant_rows(value), node.key, node.depth)
        return TreeSelection(False, np.asarray([value], dtype=np.intp), None, len(self._group_by))

    def _descendant_rows(self, node_id: int) -> np.ndarray:
        node = self._nodes[node_id]
        if not node.has_group_children:
            return np.asarray(node.visible, dtype=np.intp)
        parts = [self._descendant_rows(int(child)) for child in node.visible]
        return np.concatenate(parts) if parts else np.empty(0, dtype=np.intp)

    def visible_leaf_rows(self) -> np.ndarray:
        """All visible source rows in display order."""
        return self._descendant_rows(0)

    def index_for_node(self, node_id: int, column: int = 0) -> QModelIndex:
        """Model index of a group node (invalid for the root)."""
        if node_id <= 0:
            return QModelIndex()
        node = self._nodes[node_id]
        return self.createIndex(node.row, column, node.parent)

    def index_for_source_row(self, row: int, column: int = 0) -> QModelIndex:
        """Model index of a visible leaf, or an invalid index when the row is filtered out."""
        if not (0 <= row < len(self._df)) or not self._leaf_mask[row]:
            return QModelIndex()
        parent = self._nodes[int(self._leaf_parent[row])]
        positions = np.flatnonzero(parent.visible == row)
        if not positions.size:
            return QModelIndex()
        return self.createIndex(int(positions[0]), column, parent.id)

    def node_for_key(self, key: tuple) -> int | None:
        """Return the id of the group node with the full key path `key`."""
        node = self._nodes[0]
        for depth in range(1, len(key) + 1):
            match = next((child for child in node.groups if self._nodes[child].key == tuple(key[:depth])), None)
            if match is None:
                return None
            node = self._nodes[match]
        return node.id or None

    def group_count(self, index: QModelIndex) -> int:
        """Number of visible descendant leaves of a group index."""
        is_group, value = self._resolve(index)
        return int(self._counts[value]) if is_group else 1

    def group_value(self, node_id: int, column: int | str) -> ty.Any:
        """Aggregated value of a group node."""
        values = self._aggregates.get(self._column_index(column))
        return None if values is None else values[node_id]

    # ----------------------------------------------------------------------------------------------------------------
    # QAbstractItemModel
    # ----------------------------------------------------------------------------------------------------------------
    def index(self, row: int, column: int, parent: QModelIndex = QModelIndex()) -> QModelIndex:  # noqa: B008
        """Create an index whose internal id is the id of its parent node."""
        if row < 0 or column < 0 or column >= self.columnCount():
            return QModelIndex()
        if not parent.isValid():
            node = self._nodes[0]
        else:
            is_group, value = self._resolve(parent)
            if not is_group:
                return QModelIndex()
            node = self._nodes[value]
        if row >= node.visible.size:
            return QModelIndex()
        return self.createIndex(row, column, node.id)

    def parent(self, index: QModelIndex | None = None) -> ty.Any:  # type: ignore[override]
        """Return the parent index (or the parent QObject when called without arguments)."""
        if index is None:
            return Qc.QObject.parent(self)
        if not index.isValid():
            return QModelIndex()
        parent_id = int(index.internalId())
        if parent_id == 0:
            return QModelIndex()
        node = self._nodes[parent_id]
        return self.createIndex(node.row, 0, node.parent)

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: B008
        """Return the number of visible children."""
        if not parent.isValid():
            return int(self._nodes[0].visible.size)
        if parent.column() > 0:
            return 0
        is_group, value = self._resolve(parent)
        return int(self._nodes[value].visible.size) if is_group else 0

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: B008
        """Return the tree column plus the visible DataFrame columns."""
        return 1 + len(self._visible_columns)

    def hasChildren(self, parent: QModelIndex = QModelIndex()) -> bool:  # noqa: B008
        """Return whether `parent` has visible children."""
        return self.rowCount(parent) > 0

    def source_column(self, column: int) -> int:
        """Map a model column to a source column (`TREE_COLUMN` for column 0)."""
        return TREE_COLUMN if column == 0 else self._visible_columns[column - 1]

    def model_column(self, source_column: int) -> int | None:
        """Map a source column to a model column, `None` when hidden."""
        if source_column == TREE_COLUMN:
            return 0
        return self._visible_columns.index(source_column) + 1 if source_column in self._visible_columns else None

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole) -> ty.Any:
        """Return column titles with sort indicators; filtered columns use a bold italic font."""
        if orientation != Qt.Orientation.Horizontal or section >= self.columnCount():
            return None
        source = self.source_column(section)
        if role == Qt.ItemDataRole.DisplayRole:
            text = self._tree_title() if source == TREE_COLUMN else self._column_names()[source]
            if self._sort_column == source and self._sort_order is not None:
                indicator = (
                    ASCENDING_SORT_INDICATOR
                    if self._sort_order == Qt.SortOrder.AscendingOrder
                    else DESCENDING_SORT_INDICATOR
                )
                text = f"{text}{indicator}"
            return text
        if role == Qt.ItemDataRole.FontRole and source != TREE_COLUMN and self.is_column_filtered(source):
            return self._filtered_header_font
        if role == Qt.ItemDataRole.ToolTipRole:
            if source == TREE_COLUMN:
                return " > ".join(self._group_by) if self._group_by else self._tree_title()
            return self._column_names()[source]
        return None

    def _tree_title(self) -> str:
        if self._tree_column_title:
            return self._tree_column_title
        if self._group_by:
            return " > ".join(self._group_by)
        return self._label_column or "row"

    def _label_index(self) -> int | None:
        names = self._column_names()
        if self._label_column and self._label_column in names:
            return names.index(self._label_column)
        return None

    def _group_text(self, node: _Node) -> str:
        names = self._column_names()
        if self._group_label_column in names and node.depth == len(self._group_by):
            row = self._first_leaf(node)
            if row is not None:
                return str(self._values[row, names.index(self._group_label_column)])
        value = node.key[-1] if node.key else ""
        return "(blank)" if value is None or (isinstance(value, float) and np.isnan(value)) else str(value)

    def _first_leaf(self, node: _Node) -> int | None:
        while node.groups:
            node = self._nodes[node.groups[0]]
        return int(node.leaves[0]) if node.leaves.size else None

    def _display(self, value: ty.Any, column: int | None) -> str:
        if value is None:
            return ""
        if isinstance(value, float) and np.isnan(value):
            return ""
        with contextlib.suppress(TypeError, ValueError):
            if pd.isna(value):
                return ""
        formatter = self._formatters.get(column) if column is not None else None
        if formatter is not None:
            with contextlib.suppress(TypeError, ValueError):
                return _format_cell_value(value, formatter)
        if is_float_like(value):
            return f"{value:.4f}"
        return str(value)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> ty.Any:
        """Return cell data for display, tooltip, font and colour roles."""
        if not index.isValid():
            return None
        is_group, value = self._resolve(index)
        source = self.source_column(index.column())
        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.ToolTipRole):
            if is_group:
                node = self._nodes[value]
                if source == TREE_COLUMN:
                    return f"{self._group_text(node)} ({int(self._counts[value])})"
                aggregated = self._aggregates.get(source)
                return "" if aggregated is None else self._display(aggregated[value], source)
            if source == TREE_COLUMN:
                label = self._label_index()
                return self._display(self._values[value, label], label) if label is not None else str(value)
            return self._display(self._values[value, source], source)
        if role == Qt.ItemDataRole.FontRole and is_group:
            return self._bold_font
        if role in (Qt.ItemDataRole.BackgroundRole, Qt.ItemDataRole.ForegroundRole):
            position = 0 if role == Qt.ItemDataRole.BackgroundRole else 1
            colors = None
            if source != TREE_COLUMN:
                colors = (self._group_colors if is_group else self._leaf_colors).get(source)
            rgba = colors[position][value] if colors is not None and value < len(colors[position]) else None
            if (rgba is None or rgba[3] == 0) and not is_group and self._row_background is not None:
                rgba = self._row_background[position][value]
            if rgba is not None and rgba[3] != 0:
                return Qg.QBrush(Qg.QColor(int(rgba[0]), int(rgba[1]), int(rgba[2]), int(rgba[3])))
            return None
        return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        """Items are selectable but not editable."""
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable


class DataFrameTreeHeader(Qw.QHeaderView):
    """Horizontal header with click-to-sort and the column menu of `QtDataFrameWidget`."""

    def __init__(self, widget: QtDataFrameTreeWidget) -> None:
        super().__init__(Qt.Orientation.Horizontal, widget)
        self._widget = widget
        self.setSectionsClickable(True)
        self.setSectionsMovable(False)
        self.setStretchLastSection(True)
        self.setSortIndicatorShown(False)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._on_menu_requested)
        self.sectionClicked.connect(self._on_section_clicked)

    @property
    def tree_model(self) -> DataFrameTreeModel:
        """Model of the owning widget."""
        return self._widget.model

    def _on_section_clicked(self, section: int) -> None:
        if self._widget.sortable:
            self.tree_model.toggle_sort(self.tree_model.source_column(section))

    def _on_menu_requested(self, position: Qc.QPoint) -> None:
        section = self.logicalIndexAt(position)
        if section < 0:
            return
        self.show_column_menu(self.tree_model.source_column(section), self.mapToGlobal(position))

    def show_column_menu(self, source: int, position: Qc.QPoint) -> None:
        """Show sort, filter, visibility and colour actions for a source column."""
        model = self.tree_model
        menu = Qw.QMenu(self)
        label = model._tree_title() if source == TREE_COLUMN else model._column_names()[source]
        if self._widget.sortable:
            menu.addAction(f"Sort {label} ascending", lambda: model.set_sort(source, Qt.SortOrder.AscendingOrder))
            menu.addAction(f"Sort {label} descending", lambda: model.set_sort(source, Qt.SortOrder.DescendingOrder))
            menu.addAction("Clear sort", model.clear_sorting)
            menu.addSeparator()
        if source != TREE_COLUMN:
            if self._widget.filterable:
                menu.addAction(f"Filter {label}...", lambda: self.open_filter_dialog(source))
                menu.addAction("Clear filter", lambda: model.clear_filter_for_column(source))
                menu.addAction("Clear all filters", model.clear_filters)
                menu.addSeparator()
            if self._widget.column_visibility_control:
                hide = menu.addAction("Hide column", lambda: model.set_column_visible(source, False))
                hide.setEnabled(len(model.visible_columns) > 1)
            self._add_color_menu(menu, source)
        if self._widget.column_visibility_control:
            menu.addAction("Choose columns...", self.open_column_dialog)
        menu.addSeparator()
        menu.addAction("Expand all", self._widget.expand_all)
        menu.addAction("Collapse all", self._widget.collapse_all)
        menu.exec(position)

    def _add_color_menu(self, menu: Qw.QMenu, source: int) -> None:
        model = self.tree_model
        color_menu = menu.addMenu("Color")
        if _is_numeric_series(model.df.iloc[:, source]):
            color_menu.addAction(
                "This column - numeric (diverging, center=0)", lambda: model.color_numeric(source, vcenter=0.0)
            )
            color_menu.addAction(
                "This column - numeric (sequential)",
                lambda: model.color_numeric(source, colormap="viridis", vcenter=None),
            )
        else:
            color_menu.addAction("This column - categorical (unique values)", lambda: model.color_categorical(source))
        color_menu.addAction("Clear this column", lambda: model.clear_colors(source))
        color_menu.addSeparator()
        color_menu.addAction("Color entire table (auto)", model.color_table)
        color_menu.addAction("Clear all colors", lambda: model.clear_colors())

    def open_filter_dialog(self, source: int) -> None:
        """Open the numeric or value filter dialog of a column."""
        model = self.tree_model
        label = model._column_names()[source]
        state = model.filter_state_for_column(source)
        if _is_numeric_series(model.df.iloc[:, source]):
            dialog = NumericColumnFilterDialog(self, label, ty.cast(NumericColumnFilter | None, state))
            if dialog.exec() == Qw.QDialog.DialogCode.Accepted:
                minimum, maximum, include_blanks = dialog.filter_values()
                model.set_numeric_filter(source, minimum=minimum, maximum=maximum, include_blanks=include_blanks)
            return
        dialog = StringColumnFilterDialog(
            self, label, model.distinct_values_for_column(source), ty.cast(StringColumnFilter | None, state)
        )
        if dialog.exec() == Qw.QDialog.DialogCode.Accepted:
            allowed, include_blanks = dialog.selected_values()
            model.set_string_filter(source, allowed_values=allowed, include_blanks=include_blanks)

    def open_column_dialog(self) -> None:
        """Open the column chooser."""
        dialog = ColumnVisibilityDialog(self, self.tree_model)  # type: ignore[arg-type]
        if dialog.exec() == Qw.QDialog.DialogCode.Accepted and dialog.checked_columns():
            self.tree_model.set_visible_columns(dialog.checked_columns())


class QtDataFrameTreeWidget(Qw.QWidget):
    """DataFrame shown as a tree grouped by one or more columns.

    Parameters
    ----------
    parent : QWidget, optional
        Parent widget.
    df : DataFrame, optional
        Data; every row becomes a leaf.
    group_by : str or sequence of str, optional
        Grouping columns, outermost first. `None` shows a flat list.
    aggregations : mapping, optional
        Aggregation of group rows per column name: one of `AGGREGATIONS` or a callable taking a Series. Numeric
        columns default to `mean`; other columns show the shared value or `"<n> values"`.
    label_column : str, optional
        Column shown in the tree column for leaves.
    group_label_column : str, optional
        Column whose value (of the first row of a group) labels the group instead of its key.
    column_formatters : mapping, optional
        Format strings or callables per column name or index.
    auto_expand : int
        Expand every group when at most this many groups are shown at the top level.
    """

    evt_current_changed = Signal(object)
    evt_activated = Signal(object)
    evt_menu_requested = Signal(Qc.QPoint)

    def __init__(
        self,
        parent: Qw.QWidget | None = None,
        df: ty.Any = None,
        *,
        group_by: ty.Sequence[str] | str | None = None,
        aggregations: ty.Mapping[str, Aggregation] | None = None,
        label_column: str | None = None,
        group_label_column: str | None = None,
        column_formatters: ColumnFormatters | None = None,
        tree_column_title: str | None = None,
        sortable: bool = True,
        filterable: bool = True,
        column_visibility_control: bool = True,
        auto_expand: int = 0,
    ) -> None:
        super().__init__(parent)
        self.sortable = sortable
        self.filterable = filterable
        self.column_visibility_control = column_visibility_control
        self.auto_expand = auto_expand
        self._expanded: set[tuple] = set()
        self._column_widths: dict[str, int] = {}
        self._restoring = False

        self.model = DataFrameTreeModel(
            df,
            group_by=group_by,
            aggregations=aggregations,
            label_column=label_column,
            group_label_column=group_label_column,
            column_formatters=column_formatters,
            tree_column_title=tree_column_title,
            parent=self,
        )
        self.tree_view = Qw.QTreeView(self)
        self.tree_view.setUniformRowHeights(True)
        self.tree_view.setAlternatingRowColors(True)
        self.tree_view.setSelectionBehavior(Qw.QAbstractItemView.SelectionBehavior.SelectRows)
        self.tree_view.setSelectionMode(Qw.QAbstractItemView.SelectionMode.ExtendedSelection)
        self.tree_view.setEditTriggers(Qw.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tree_view.setHorizontalScrollMode(Qw.QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.tree_view.setVerticalScrollMode(Qw.QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.tree_view.setAllColumnsShowFocus(True)
        self.tree_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree_view.customContextMenuRequested.connect(
            lambda position: self.evt_menu_requested.emit(self.tree_view.viewport().mapToGlobal(position))
        )
        self.header = DataFrameTreeHeader(self)
        self.tree_view.setHeader(self.header)
        self.tree_view.setModel(self.model)
        self.header.setSectionsClickable(True)  # QTreeView.setModel turns clicking off
        self.tree_view.expanded.connect(self._on_expanded)
        self.tree_view.collapsed.connect(self._on_collapsed)
        self.tree_view.activated.connect(self._on_activated)
        self.tree_view.selectionModel().currentChanged.connect(self._on_current_changed)
        self.header.sectionResized.connect(self._on_section_resized)
        self.model.modelAboutToBeReset.connect(self._remember_state)
        self.model.modelReset.connect(self._restore_state)
        self._pending_current: tuple[bool, ty.Any] | None = None

        layout = Qw.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.tree_view)
        self._restore_state()

    # data -----------------------------------------------------------------------------------------------------------
    @property
    def df(self) -> pd.DataFrame:
        """Source DataFrame."""
        return self.model.df

    def set_data(self, df: ty.Any, **kwargs: ty.Any) -> None:
        """Replace the data (see `DataFrameTreeModel.set_data`)."""
        self.model.set_data(df, **kwargs)

    def set_group_by(self, group_by: ty.Sequence[str] | str | None) -> None:
        """Regroup the rows."""
        self._expanded.clear()
        self.model.set_group_by(group_by)

    def set_row_mask(self, mask: np.ndarray | None) -> None:
        """Additional external filter of the leaves."""
        self.model.set_row_mask(mask)

    # delegates to the model -----------------------------------------------------------------------------------------
    def set_numeric_filter(self, column: int | str, **kwargs: ty.Any) -> None:
        """Filter a column by numeric range."""
        self.model.set_numeric_filter(column, **kwargs)

    def set_value_filter(
        self, column: int | str, allowed_values: ty.Iterable[str], include_blanks: bool = True
    ) -> None:
        """Filter a column by allowed values."""
        self.model.set_string_filter(column, allowed_values=allowed_values, include_blanks=include_blanks)

    def clear_filter(self, column: int | str) -> None:
        """Remove the filter of one column."""
        self.model.clear_filter_for_column(column)

    def clear_filters(self) -> None:
        """Remove every column filter."""
        self.model.clear_filters()

    def set_sort(self, column: int | str | None, order: Qt.SortOrder | None = Qt.SortOrder.AscendingOrder) -> None:
        """Sort by a column name/index (`TREE_COLUMN` for the tree column) or clear with `None`."""
        source = None if column is None else (column if column == TREE_COLUMN else self.model._column_index(column))
        self.model.set_sort(source, order)

    def clear_sorting(self) -> None:
        """Restore the source order."""
        self.model.clear_sorting()

    def color_numeric(self, column: int | str, **kwargs: ty.Any) -> None:
        """Colour a numeric column."""
        self.model.color_numeric(column, **kwargs)

    def color_categorical(self, column: int | str, colormap: str = "tab20") -> None:
        """Colour a categorical column."""
        self.model.color_categorical(column, colormap=colormap)

    def clear_colors(self, column: int | str | None = None) -> None:
        """Remove column colours."""
        self.model.clear_colors(column)

    def set_column_visible(self, column: int | str, visible: bool) -> None:
        """Show or hide a column."""
        self.model.set_column_visible(column, visible)

    def set_visible_columns(self, columns: ty.Iterable[int | str]) -> None:
        """Show exactly these columns."""
        self.model.set_visible_columns(columns)

    def visible_columns(self) -> list[int]:
        """Shown source columns."""
        return self.model.visible_columns

    # navigation -----------------------------------------------------------------------------------------------------
    def expand_all(self) -> None:
        """Expand every group."""
        self.tree_view.expandAll()

    def collapse_all(self) -> None:
        """Collapse every group."""
        self.tree_view.collapseAll()
        self._expanded.clear()

    def current_selection(self) -> TreeSelection | None:
        """Describe the current item."""
        return self.model.selection(self.tree_view.currentIndex())

    def current_source_rows(self) -> np.ndarray:
        """Source rows of the current item."""
        return self.model.source_rows(self.tree_view.currentIndex())

    def selected_source_rows(self) -> np.ndarray:
        """Unique source rows of every selected leaf and of all leaves under selected groups."""
        rows = [self.model.source_rows(index) for index in self.tree_view.selectionModel().selectedRows(0)]
        if not rows:
            return np.empty(0, dtype=np.intp)
        return np.asarray(list(dict.fromkeys(np.concatenate(rows).tolist())), dtype=np.intp)

    def visible_dataframe(self) -> pd.DataFrame:
        """Visible leaf rows in display order."""
        return self.model.df.iloc[self.model.visible_leaf_rows()]

    def visible_count(self) -> int:
        """Number of visible leaves."""
        return int(self.model._leaf_mask.sum())

    def select_source_row(self, row: int, emit: bool = True) -> bool:
        """Expand to, select and scroll to a visible leaf."""
        index = self.model.index_for_source_row(row)
        return self._select_index(index, emit)

    def select_group(self, key: tuple, emit: bool = True) -> bool:
        """Select a group by its full key path."""
        node_id = self.model.node_for_key(tuple(key))
        if node_id is None or self.model._counts[node_id] == 0:
            return False
        return self._select_index(self.model.index_for_node(node_id), emit)

    def _select_index(self, index: QModelIndex, emit: bool) -> bool:
        if not index.isValid():
            return False
        parent = index.parent()
        while parent.isValid():
            self.tree_view.expand(parent)
            parent = parent.parent()
        selection = self.tree_view.selectionModel()
        flags = Qc.QItemSelectionModel.SelectionFlag.ClearAndSelect | Qc.QItemSelectionModel.SelectionFlag.Rows
        if emit:
            selection.setCurrentIndex(index, flags)
        else:
            with Qc.QSignalBlocker(selection):
                selection.setCurrentIndex(index, flags)
            self.tree_view.viewport().update()
        self.tree_view.scrollTo(index, Qw.QAbstractItemView.ScrollHint.EnsureVisible)
        return True

    # state handling -------------------------------------------------------------------------------------------------
    def _path(self, index: QModelIndex) -> tuple | None:
        selection = self.model.selection(index)
        return None if selection is None or not selection.is_group else selection.group_key

    def _on_expanded(self, index: QModelIndex) -> None:
        if not self._restoring and (key := self._path(index)) is not None:
            self._expanded.add(key)

    def _on_collapsed(self, index: QModelIndex) -> None:
        if not self._restoring and (key := self._path(index)) is not None:
            self._expanded.discard(key)

    def _on_section_resized(self, section: int, _old: int, new: int) -> None:
        if self._restoring or section >= self.model.columnCount():
            return
        self._column_widths[
            self.model.headerData(section, Qt.Orientation.Horizontal, Qt.ItemDataRole.ToolTipRole) or ""
        ] = new

    def _remember_state(self) -> None:
        current = self.model.selection(self.tree_view.currentIndex()) if self.tree_view.model() else None
        if current is None:
            self._pending_current = None
        elif current.is_group:
            self._pending_current = (True, current.group_key)
        else:
            self._pending_current = (False, current.source_row)

    def _restore_state(self) -> None:
        self._restoring = True
        self.header.setSectionsClickable(True)
        try:
            for section in range(self.model.columnCount()):
                key = self.model.headerData(section, Qt.Orientation.Horizontal, Qt.ItemDataRole.ToolTipRole) or ""
                width = self._column_widths.get(key)
                if width is None:
                    if section == 0:
                        width = DEFAULT_TREE_COLUMN_WIDTH
                    else:
                        text = str(self.model.headerData(section, Qt.Orientation.Horizontal) or "")
                        width = min(
                            MAX_INITIAL_COLUMN_WIDTH,
                            max(DEFAULT_COLUMN_WIDTH, self.fontMetrics().horizontalAdvance(text) + 30),
                        )
                self.header.resizeSection(section, width)
            top = self.model.rowCount()
            if self.model.group_by and 0 < top <= self.auto_expand:
                self.tree_view.expandAll()
            else:
                for key in list(self._expanded):
                    node_id = self.model.node_for_key(key)
                    if node_id is not None and self.model._counts[node_id] > 0:
                        self.tree_view.expand(self.model.index_for_node(node_id))
            if self._pending_current is not None:
                is_group, value = self._pending_current
                if is_group:
                    self.select_group(value, emit=False)
                elif value is not None:
                    self.select_source_row(int(value), emit=False)
        finally:
            self._restoring = False

    def _on_current_changed(self, current: QModelIndex, _previous: QModelIndex) -> None:
        selection = self.model.selection(current)
        if selection is not None:
            self.evt_current_changed.emit(selection)

    def _on_activated(self, index: QModelIndex) -> None:
        selection = self.model.selection(index)
        if selection is not None:
            self.evt_activated.emit(selection)


# Examples
if __name__ == "__main__":  # pragma: no cover
    import sys

    from qtextra.utils.dev import qframe

    def _get_demo_data(n_rows: int = 20_000) -> pd.DataFrame:
        rng = np.random.default_rng()
        compounds = [f"PC {30 + i % 12}:{i % 4}" for i in range(400)]
        return pd.DataFrame(
            {
                "compound": rng.choice(compounds, n_rows),
                "dataset": rng.choice([f"dataset {i}" for i in range(8)], n_rows),
                "adduct": rng.choice(["[M+H]+", "[M+Na]+", "[M+K]+"], n_rows),
                "ppm": rng.normal(0, 2, n_rows),
                "fdr": rng.choice([0.01, 0.05, 0.1, 0.2, 0.5], n_rows),
                "score": rng.random(n_rows),
            }
        )

    app, frame, va = qframe(False)
    frame.setMinimumSize(900, 700)
    widget = QtDataFrameTreeWidget(
        None,
        _get_demo_data(),
        group_by="compound",
        aggregations={"fdr": "min", "score": "max", "dataset": "nunique"},
        label_column="dataset",
        column_formatters={"ppm": "{:+.2f}", "score": "{:.3f}"},
    )
    widget.color_numeric("ppm", vmin=-5, vmax=5, vcenter=0.0)
    widget.color_numeric("score", colormap="Greens", vcenter=None)
    va.addWidget(widget, stretch=True)
    group_combo = Qw.QComboBox()
    group_combo.addItems(["compound", "compound > adduct", "dataset", "(flat)"])
    group_combo.currentTextChanged.connect(
        lambda text: widget.set_group_by(None if text == "(flat)" else [part.strip() for part in text.split(">")])
    )
    va.addWidget(group_combo)
    frame.show()
    sys.exit(app.exec_())
