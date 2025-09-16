"""Table view."""

from __future__ import annotations

import operator
import typing as ty
from contextlib import contextmanager, suppress
from enum import Enum

import numpy as np
from loguru import logger
from natsort.natsort import index_natsorted, order_by_index
from qtpy.QtCore import (  # type: ignore[attr-defined]
    QAbstractTableModel,
    QModelIndex,
    QSize,
    QSortFilterProxyModel,
    Qt,
    Signal,
    Slot,
)
from qtpy.QtGui import QBrush, QColor, QKeyEvent, QPainter, QTextDocument
from qtpy.QtWidgets import QAbstractItemView, QHeaderView, QStyledItemDelegate, QStyleOptionViewItem, QTableView
from superqt.utils import ensure_main_thread

from qtextra.config import THEMES
from qtextra.helpers import make_qta_icon, qt_signals_blocked
from qtextra.utils.color import get_text_color
from qtextra.utils.table_config import TableConfig
from qtextra.utils.utilities import connect

TEXT_COLOR: str = "#000000"
LINK_COLOR: str = "#0000FF"

__all__ = (
    "MultiColumnMultiValueProxyModel",
    "MultiColumnSingleValueProxyModel",
    "QtCheckableItemModel",
    "QtCheckableTableView",
    "SingleColumnMultiValueProxyModel",
    "TableConfig",
)


class WrapTextDelegate(QStyledItemDelegate):
    """Wrap text delegate."""

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index) -> None:
        """Paint."""
        text = index.model().data(index)
        document = QTextDocument()
        document.setTextWidth(option.rect.width())  # Set text width to cell width
        document.setDefaultFont(option.font)
        document.setHtml(str(text))

        painter.save()
        painter.translate(option.rect.topLeft())
        document.drawContents(painter)
        painter.restore()

    def sizeHint(self, option: QStyleOptionViewItem, index) -> QSize:
        """Size hint."""
        text = index.model().data(index)
        document = QTextDocument()
        document.setTextWidth(option.rect.width())  # Set text width to option's width
        document.setDefaultFont(option.font)
        document.setHtml(text)
        return QSize(document.idealWidth(), int(document.size().height() / 4.5))


class MultiFilterMode(str, Enum):
    """Multi filter mode."""

    OR = "OR"
    AND = "AND"


class FilterProxyModelBase(QSortFilterProxyModel):
    """Base class for filters."""

    compare_func: ty.Callable[[ty.Iterable[bool]], bool]
    is_multi_or: bool
    sourceModel: ty.Callable[[], QtCheckableItemModel]

    evt_filtered = Signal()

    def __init__(self, *args: ty.Any, mode: MultiFilterMode = MultiFilterMode.AND, **kwargs: ty.Any):
        QSortFilterProxyModel.__init__(self, *args, **kwargs)
        self._multi_filter_mode = mode
        self.multi_filter_mode = mode

    @property
    def multi_filter_mode(self) -> MultiFilterMode:
        """Return multi filter mode."""
        return self._multi_filter_mode

    @multi_filter_mode.setter
    def multi_filter_mode(self, value: MultiFilterMode) -> None:
        self._multi_filter_mode = value
        self.is_multi_or = self.multi_filter_mode == MultiFilterMode.OR
        self.compare_func = any if self.is_multi_or else all

    def sort(self, column: int, order: Qt.SortOrder | None = None) -> None:
        """Sort table."""
        if self.sourceModel().no_sort_columns and column in self.sourceModel().no_sort_columns:
            return
        super().sort(column, order)

    def setFilterByColumn(self, *args: ty.Any) -> None:
        """Set filter by column."""
        raise NotImplementedError("Must implement method")

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        """Filter rows."""
        raise NotImplementedError("Must implement method")

    def find_visible_rows(self) -> tuple[list[int], list[int]]:
        """Find visible rows."""
        visible_rows = []
        hidden_rows = []
        source_model = self.sourceModel()
        for row in range(source_model.rowCount()):
            source_index = source_model.index(row, 0)
            proxy_index = self.mapFromSource(source_index)
            if proxy_index.isValid():
                visible_rows.append(row)
            else:
                hidden_rows.append(row)
        return visible_rows, hidden_rows


class MultiColumnSingleValueProxyModel(FilterProxyModelBase):
    """Proxy model to filter by."""

    def __init__(self, *args: ty.Any, mode: MultiFilterMode = MultiFilterMode.AND, **kwargs: ty.Any):
        super().__init__(*args, mode=mode, **kwargs)
        self.filters_by_text: dict[int, str] = {}
        self.filters_by_state: dict[int, Qt.CheckState] = {}

    def setFilterByColumn(self, text: str, column: int) -> None:
        """Set filter by column."""
        if not text and column in self.filters_by_text:
            del self.filters_by_text[column]
        self.filters_by_text[column] = str(text).lower()
        self.invalidateFilter()
        self.evt_filtered.emit()

    def setFilterByState(self, value: bool | None, column: int) -> None:
        """Set filter by value."""
        if value is None and column in self.filters_by_state:
            del self.filters_by_state[column]
        else:
            self.filters_by_state[column] = Qt.CheckState.Checked if value else Qt.CheckState.Unchecked
        self.invalidateFilter()
        self.evt_filtered.emit()

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        """Filter rows."""
        if not self.filters_by_text and not self.filters_by_state:
            return True

        results: list[bool] = []
        for column, state in self.filters_by_state.items():
            index = self.sourceModel().index(source_row, column, source_parent)
            if index.isValid():
                value = self.sourceModel().data(index, Qt.ItemDataRole.CheckStateRole)
                results.append(value == state)

        for column, text in self.filters_by_text.items():
            value = ""
            index = self.sourceModel().index(source_row, column, source_parent)
            if index.isValid():
                value = self.sourceModel().data(index, Qt.ItemDataRole.DisplayRole)
                if not value:
                    return True
            results.append(text in value.lower())
        return self.compare_func(results)


class MultiColumnMultiValueProxyModel(FilterProxyModelBase):
    """Proxy model to filter by."""

    def __init__(
        self,
        *args: ty.Any,
        mode: MultiFilterMode = MultiFilterMode.AND,
        column_mode: MultiFilterMode = MultiFilterMode.OR,
        **kwargs: ty.Any,
    ):
        super().__init__(*args, mode=mode, **kwargs)
        self.column_mode = column_mode
        # self.column_compare_func = any if column_mode == MultiFilterMode.OR else all
        self.filters_by_text: dict[int, list[str]] = {}
        self.column_compare_funcs: dict[int, ty.Callable[[ty.Iterable[bool]], bool]] = {}

    def column_compare_func(self, column: int) -> ty.Callable:
        """Return instance of callable for specific column."""
        if column in self.column_compare_funcs:
            return self.column_compare_funcs[column]
        return any if self.column_mode == MultiFilterMode.OR else all

    def setFilterByColumn(self, filters: list[str], column: int, column_mode: MultiFilterMode | None = None) -> None:
        """Set filter by column."""
        if not filters:
            if column in self.filters_by_text:
                del self.filters_by_text[column]
            if column in self.column_compare_funcs:
                del self.column_compare_funcs[column]
        if not isinstance(filters, list):
            filters = [filters]
        if filters:
            self.filters_by_text[column] = [filt.lower() for filt in filters]
            if column_mode:
                self.column_compare_funcs[column] = any if column_mode == MultiFilterMode.OR else all
        self.invalidateFilter()
        self.evt_filtered.emit()

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        """Filter rows."""
        if not self.filters_by_text:
            return True
        results: list[bool] = []
        for column, _texts in self.filters_by_text.items():
            value = ""
            index = self.sourceModel().index(source_row, column, source_parent)
            if index.isValid():
                value = self.sourceModel().data(index, Qt.ItemDataRole.DisplayRole)
                if not value:
                    return True
            results.append(self.column_compare_func(column)(text in value.lower() for text in _texts))
        return self.compare_func(results)


class SingleColumnMultiValueProxyModel(FilterProxyModelBase):
    """Proxy model to filter by."""

    def __init__(self, *args: ty.Any, column: int, mode: MultiFilterMode = MultiFilterMode.AND, **kwargs: ty.Any):
        super().__init__(*args, mode=mode, **kwargs)
        self.column = column
        self.filters: list[str] = []

    def setFilterByColumn(self, filters: list[str], column: int | None = None) -> None:
        """Set filter by column."""
        if column is not None:
            self.column = column
        if not isinstance(filters, list):
            filters = [filters]

        self.filters = [filt.lower() for filt in filters]
        self.invalidateFilter()
        self.evt_filtered.emit()

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        """Filter rows."""
        if not self.filters:
            return True
        # if not source_parent.isValid():
        #     return True

        results: list[bool] = []
        for text in self.filters:
            value = ""
            index = self.sourceModel().index(source_row, self.column, source_parent)
            if index.isValid():
                value = self.sourceModel().data(index, Qt.ItemDataRole.DisplayRole)
                if not value:
                    return True
            results.append(text in value.lower())
        return self.compare_func(results)


class QtCheckableItemModel(QAbstractTableModel):
    """Checkable item model."""

    evt_checked = Signal(int, bool)
    evt_value_checked = Signal(int, int, bool)

    table_proxy: MultiColumnSingleValueProxyModel | SingleColumnMultiValueProxyModel | None = None

    def __init__(
        self,
        parent: QtCheckableTableView,
        data: list[list],
        header: list[str] | None = None,
        no_sort_columns: list[int] | None = None,
        hidden_columns: list[int] | None = None,
        color_columns: list[int] | None = None,
        html_columns: list[int] | None = None,
        icon_columns: list[int] | None = None,
        checkable_columns: list[int] | None = None,
        text_alignment: Qt.AlignmentFlag | None = None,
    ):
        QAbstractTableModel.__init__(self, parent)
        self._table: list[list[ty.Any]] = data
        self.state = None
        self.original_index = list(range(len(self._table)))
        self.header = header or []
        self.no_sort_columns = no_sort_columns or []
        self.hidden_columns = hidden_columns or []
        self.color_columns = color_columns or []
        self.html_columns = html_columns or []
        self.icon_columns = icon_columns or []
        self.checkable_columns = checkable_columns or []
        self.text_alignment = text_alignment or Qt.AlignmentFlag.AlignCenter

    def flags(self, index):
        """Return flags."""
        fl = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        column = index.column()
        if column == 0 or column in self.checkable_columns:
            fl |= Qt.ItemFlag.ItemIsUserCheckable
        else:
            fl |= Qt.ItemFlag.ItemIsEditable
        return fl

    @property
    def n_checked(self) -> int:
        """Return of checked elements."""
        return [row[0] for row in self._table].count(True)

    @property
    def n_unchecked(self) -> int:
        """Return count of unchecked elements."""
        return [row[0] for row in self._table].count(False)

    def rowCount(self, parent: QModelIndex | None = None, **kwargs: ty.Any) -> int:
        """Return number of rows."""
        return len(self._table) if self._table else 0

    def columnCount(self, parent: QModelIndex | None = None, **kwargs: ty.Any) -> int:
        """Return number of columns."""
        return len(self._table[0]) if self._table else 0

    def removeRow(self, row: int, parent: QModelIndex | None = None) -> bool:
        """Remove row."""
        if parent is None:
            parent = QModelIndex()
        self.beginRemoveRows(parent, row, row)
        self._table.pop(row)
        self.original_index.pop(row)
        self.endRemoveRows()
        return True

    def data(self, index: QModelIndex, role: Qt.ItemDataRole | None = None) -> ty.Any:
        """Parse data."""
        if not index.isValid():
            return None

        row = index.row()
        column = index.column()
        is_color = column in self.color_columns

        # check the background color
        if role == Qt.ItemDataRole.BackgroundRole:
            if is_color:
                color = self._table[row][column]
                if isinstance(color, str) and "#" in color:
                    return QBrush(QColor(color))
                elif isinstance(color, np.ndarray):
                    return QBrush(QColor(*(255 * color).astype("int")))
                if isinstance(color, QColor):
                    return QBrush(color)
            return QBrush()
        # check text color
        elif role == Qt.ItemDataRole.ForegroundRole:
            if is_color:
                bg_color = self._table[row][column]
                if isinstance(bg_color, str) and "#" in bg_color:
                    return QBrush(get_text_color(QColor(bg_color)))
            # let's use slightly different color html
            if column in self.html_columns:
                return QBrush(QColor(LINK_COLOR))
            return QBrush(QColor(TEXT_COLOR))
        # check value
        elif role == Qt.ItemDataRole.DisplayRole:
            if column not in self.icon_columns and column not in self.checkable_columns and not is_color:
                value = self._table[row][column]
                return value
        # check the alignment role
        elif role == Qt.ItemDataRole.TextAlignmentRole:
            return self.text_alignment
        # check state
        elif role == Qt.ItemDataRole.CheckStateRole and column in self.checkable_columns:
            return Qt.CheckState.Checked if self._table[row][column] else Qt.CheckState.Unchecked
        # icon state
        elif role == Qt.ItemDataRole.DecorationRole:
            if column in self.icon_columns:
                value = self._table[row][column]
                return make_qta_icon(value)

    def headerData(self, col: int, orientation: Qt.Orientation, role: Qt.ItemDataRole | None = None) -> str | None:
        """Get header data."""
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self.header[col]
        return None

    def sort(self, column: int, order: Qt.SortOrder | None = None) -> None:
        """Sort table."""
        if self.no_sort_columns and column in self.no_sort_columns:
            return

        # emit signal about upcoming change
        self.layoutAboutToBeChanged.emit()

        # get sort index
        new_index = index_natsorted(self._table, key=operator.itemgetter(column))

        # sort
        self._table = order_by_index(self._table, new_index)
        self.original_index = order_by_index(self.original_index, new_index)

        if order == Qt.SortOrder.DescendingOrder:
            self._table.reverse()
            self.original_index.reverse()

        # indicate that change to data has been made
        self.layoutChanged.emit()

    def setData(self, index: QModelIndex, value: ty.Any, role=Qt.ItemDataRole.EditRole) -> bool:
        """Set data in the model."""
        row = index.row()
        column = index.column()

        if role == Qt.ItemDataRole.CheckStateRole:
            old_value = index.data()
            # value = not old_value
            # change = True
            value = bool(value)
            change = old_value != value
        else:
            old_value = index.data()
            if isinstance(old_value, np.ndarray):
                change = np.any(old_value != value)
            else:
                change = old_value != value

        self._table[row][column] = value
        if change:
            self.dataChanged.emit(index, index)
            if column == 0:
                self.evt_checked.emit(row, value)
            elif column in self.checkable_columns:
                self.evt_value_checked.emit(row, column, value)
            return True
        return False

    def update_value(self, row: int, column: int, value: ty.Any, role=Qt.ItemDataRole.EditRole) -> None:
        """Update value."""
        index = self.createIndex(row, column)

        # setup role
        if column == 0 or column in self.checkable_columns:
            role = Qt.ItemDataRole.CheckStateRole

        if index.isValid():
            self.setData(index, value, role=role)

    def update_values(self, row, column_value) -> None:
        """Update values."""
        for column, value in column_value.items():
            self.update_value(row, column, value)

    def update_row(self, row: int, value: ty.Any) -> None:
        """Update row."""
        if len(value) != len(self.header):
            raise ValueError("Cannot update row as length of the values does not match header length")

        for column in range(len(self.header)):
            index = self.createIndex(row, column)
            if index.isValid():
                self.setData(index, value[column])

    def update_column(self, col, values, match_to_sort: bool = True) -> None:
        """Update column."""
        if col > self.columnCount():
            raise ValueError("Cannot update column as its outside of the boundaries")

        if len(values) > self.rowCount():
            raise ValueError("Cannot update column as the length of the values does not match the number of rows")

        for row, value in enumerate(values):
            if match_to_sort:
                row = self.get_sort_index(row)
            index = self.createIndex(row, col)
            if index.isValid():
                self.setData(index, value)

    def toggle_all_rows(self) -> None:
        """Check all rows in the table."""
        if self.state is None:
            self.state = self.n_checked == self.rowCount()
        self.state = not self.state
        for row, __ in enumerate(self._table):
            if self.table_proxy and not self.table_proxy.filterAcceptsRow(row, QModelIndex()):
                continue
            self._table[row][0] = self.state
            index = self.createIndex(row, 0)
            self.dataChanged.emit(index, index)
        self.evt_checked.emit(-1, self.state)

    def check_all_rows(self) -> None:
        """Check all rows in the table."""
        for row, __ in enumerate(self._table):
            if self.table_proxy and not self.table_proxy.filterAcceptsRow(row, QModelIndex()):
                continue
            self._table[row][0] = True
            index = self.createIndex(row, 0)
            self.dataChanged.emit(index, index)
        self.evt_checked.emit(-1, True)

    def uncheck_all_rows(self) -> None:
        """Uncheck all rows."""
        for row, __ in enumerate(self._table):
            if self.table_proxy and not self.table_proxy.filterAcceptsRow(row, QModelIndex()):
                continue
            self._table[row][0] = False
            index = self.createIndex(row, 0)
            self.dataChanged.emit(index, index)
        self.evt_checked.emit(-1, False)

    def get_all_checked(self) -> list[int]:
        """Get all checked items."""
        return self._get_all_state(True)

    def get_all_unchecked(self) -> list[int]:
        """Get all unchecked items."""
        return self._get_all_state(False)

    def _get_all_state(self, state: bool) -> list[int]:
        """Get all checked items."""
        checked = []
        for i, row in enumerate(self._table):
            if row[0] is state:
                checked.append(i)
        return checked

    def roleNames(self):
        """Return role names."""
        roles = QAbstractTableModel.roleNames(self)
        roles[hash("Checked")] = Qt.ItemDataRole.CheckStateRole
        return roles

    def reset(self):
        """Reset model."""
        self.beginResetModel()
        self.endResetModel()

    def get_initial_index(self, row: int) -> int:
        """Get the index of the initial array, regardless of whether it was sorted."""
        return self.original_index[row]

    def get_initial_indices(self, index: list) -> list:
        """Get list of all initial indices."""
        return [self.get_initial_index(row) for row in index]

    def get_sort_index(self, row: int) -> int:
        """Get the index inside the sorted array as matched from the not-sorted array."""
        return self.original_index.index(row)

    def get_sort_indices(self, index: list) -> list:
        """Get list of all sort indices."""
        return [self.get_sort_index(row) for row in index]

    def get_data(self) -> list[list]:
        """Get data from model."""
        return self._table

    def get_row_id(self, col_id: int, value: str) -> int:
        """Find value index."""
        for row_id, row in enumerate(self._table):
            if row[col_id] == value:
                return row_id
        return -1

    def get_row_id_for_values(self, *column_and_values: ty.Tuple[int, ty.Union[str, int, float]]) -> int:
        """Find value index."""
        for row_id, row in enumerate(self._table):
            for col_id, value in column_and_values:
                if row[col_id] != value:
                    break
                if all(row[col_id] == value for col_id, value in column_and_values):
                    return row_id
        return -1

    @ensure_main_thread
    def add_data(self, data: list) -> None:
        """Add data."""
        self._table.extend(data)
        self.original_index = list(range(len(self._table)))
        # indicate that change to data has been made
        self.layoutAboutToBeChanged.emit()
        self.layoutChanged.emit()

    @ensure_main_thread
    def reset_data(self) -> None:
        """Reset data."""
        self._table.clear()
        self.original_index.clear()
        self.layoutAboutToBeChanged.emit()
        self.layoutChanged.emit()

    def data_changed(self) -> None:
        """Emit an event when there has been change to the model."""
        self.layoutChanged.emit()


class QtCheckableTableView(QTableView):
    """Checkbox table."""

    model: ty.Callable[[], QtCheckableItemModel]

    # events
    # triggered whenever item is checked/unchecked. It returns the index and check state when its triggered.
    # It behaves slightly differently when user clicks on the header and -1 is emitted rather than actual index
    evt_checked = Signal(int, bool)
    evt_value_checked = Signal(int, int, bool)
    # keyboard event
    evt_keypress = Signal(QKeyEvent)
    # value changed
    evt_changed = Signal()
    evt_double_clicked = Signal(int)
    evt_reset = Signal()

    def __init__(
        self,
        *args: ty.Any,
        config: TableConfig | None = None,
        enable_all_check: bool = True,
        double_click_to_check: bool = False,
        sortable: bool = True,
        checkable: bool = False,
        drag: bool = False,
        selection: QAbstractItemView.SelectionMode = QAbstractItemView.SelectionMode.ExtendedSelection,
        **kwargs: ty.Any,
    ):
        super().__init__(*args, **kwargs)

        # setup config
        self._config = config
        self._header_columns = None
        self._is_init = False
        self.enable_all_check = enable_all_check
        self.checkable = checkable

        self._double_click_to_check = double_click_to_check
        self._sortable = sortable
        self._drag = drag
        self._selection = selection

        # register events
        self.doubleClicked.connect(lambda v: self.evt_double_clicked.emit(v.row()))
        self.clicked.connect(self.on_table_clicked)
        if self._sortable:
            self.header.sectionClicked.connect(self.sortByColumn)
        if self._double_click_to_check:
            self.doubleClicked.connect(self._on_check_row)
        if isinstance(self._config, TableConfig):
            self.init_from_config()
        connect(THEMES.evt_theme_changed, self._update_color_theme, state=True)
        self._update_color_theme()
        self.setCornerButtonEnabled(False)

    def closeEvent(self, event) -> None:
        """Close event."""
        connect(THEMES.evt_theme_changed, self._update_color_theme, state=False)
        return super().closeEvent(event)

    def activate_word_wrap(self) -> None:
        """Set word wrap."""
        self.setWordWrap(True)
        self.setItemDelegate(WrapTextDelegate())  # Use the custom delegate

    def resize_wrapped_rows(self) -> None:
        """Resize wrapped rows."""
        # This is a simplistic approach to dynamically calculate row height.
        # You might need a more sophisticated calculation based on your content.
        for row in range(self.model().rowCount()):
            new_height = 0
            for column in range(self.model().columnCount()):
                index = self.model().index(row, column)
                height = self.itemDelegate().sizeHint(QStyleOptionViewItem(), index).height()
                if height > new_height:
                    new_height = height
            self.setRowHeight(row, new_height)

    @Slot()
    def _update_color_theme(self):
        """Update global color theme."""
        global TEXT_COLOR, LINK_COLOR
        TEXT_COLOR = THEMES.get_theme_color()
        LINK_COLOR = THEMES.get_hex_color("highlight")
        with suppress(RuntimeError):
            self.update(QModelIndex())

    def _on_check_row(self, evt):
        """Event triggers check/uncheck of row."""
        row_id = evt.row()
        self.update_value(row_id, 0, not self.is_checked(row_id))

    @property
    def n_rows(self) -> int:
        """Return the number of rows in the table."""
        return self.row_count()

    @property
    def n_cols(self) -> int:
        """Return the number of columns in the table."""
        return self.column_count()

    def column_count(self) -> int:
        """Return the number columns."""
        return self.model().columnCount(self) if self.model() else 0

    def row_count(self) -> int:
        """Return the number of rows."""
        return self.model().rowCount(self) if self.model() else 0

    def row_visible_count(self) -> int:
        """Return the number of rows that are actually visible."""
        model = self.model()
        if model:
            if hasattr(model, "table_proxy"):
                return model.table_proxy.rowCount()
            return model.rowCount()
        return 0

    @property
    def header(self):
        """Return header."""
        return self.horizontalHeader()

    @property
    def index(self) -> QHeaderView:
        """Return index."""
        return self.verticalHeader()

    def model(self) -> QtCheckableItemModel:
        """Return instance of model."""
        model: QtCheckableItemModel = super().model()
        if hasattr(model, "sourceModel"):
            return model.sourceModel()
        return model

    def is_proxy(self) -> bool:
        """Return True if model is a proxy model."""
        return isinstance(super().model(), MultiColumnSingleValueProxyModel)

    def proxy_or_model(self) -> QtCheckableItemModel | MultiColumnSingleValueProxyModel:
        """Return instance of model."""
        model: QtCheckableItemModel = super().model()
        if isinstance(model, MultiColumnSingleValueProxyModel):
            return model
        return model

    def on_table_clicked(self, index: ty.Optional[QModelIndex] = None) -> None:
        """Imitate row selection."""
        if index is None:
            index = QModelIndex()
        if not index.isValid():
            return
        row = index.row()
        self.selectRow(row)

    def init(self) -> None:
        """Initialize table to ensure correct visuals."""
        sizing = {
            "stretch": QHeaderView.ResizeMode.Stretch,
            "fixed": QHeaderView.ResizeMode.Fixed,
            "contents": QHeaderView.ResizeMode.ResizeToContents,
        }
        # Get hook for the header
        config: TableConfig | None = self._config
        n_cols = self.column_count()
        header = self.header
        # 25 px is the optimal size for checkbox
        header.setMinimumSectionSize(25)

        resizable = []
        for column_id in range(n_cols):
            if config:
                column_metadata = config.get(column_id)
                if not column_metadata:
                    continue
                sizing_ = column_metadata["sizing"]
                mode = sizing.get(
                    sizing_, QHeaderView.ResizeMode.Stretch if column_id else QHeaderView.ResizeMode.Fixed
                )
            else:
                # The first column should always be a QCheckbox
                mode = QHeaderView.ResizeMode.Fixed if column_id == 0 else QHeaderView.ResizeMode.Stretch
            header.setSectionResizeMode(column_id, mode)
            if config:
                if mode == QHeaderView.ResizeMode.Fixed:
                    header.resizeSection(column_id, config.get_width(column_id))
                elif mode == QHeaderView.ResizeMode.Stretch and column_metadata["resizeable"]:
                    resizable.append(column_id)

        # set column width for the first column (checkbox)
        self.setColumnWidth(0, 25)
        # disable editing
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        # enable sorting
        self.setSortingEnabled(self._sortable)
        # disable drag
        self.setDragEnabled(self._drag)
        if self._drag:
            self.setDropIndicatorShown(True)
        # set selection mode
        self.setSelectionMode(self._selection)

        # hide columns
        model = self.model()
        for n_col in model.hidden_columns:
            self.setColumnHidden(n_col, True)

        self._is_init = True
        for col in resizable:
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Interactive)
        model.data_changed()

    def set_column_resize_mode(self, index: int, mode: QHeaderView.ResizeMode = QHeaderView.ResizeMode.Stretch):
        """Set column resize mode."""
        if self._is_init:
            self.header.setSectionResizeMode(index, mode)

    def on_check(self, row: int, value: bool) -> None:
        """Check."""
        self.evt_checked.emit(row, value)

    def init_from_config(self) -> None:
        """Initialize based on config."""
        self.set_data(
            [],
            self._config.header,
            self._config.no_sort_columns,
            self._config.hidden_columns,
            icon_columns=self._config.icon_columns,
        )

    def set_model(self, model: QtCheckableItemModel) -> None:
        """Set model."""
        if self._config:
            model.icon_columns = self._config.icon_columns
            model.color_columns = self._config.color_columns
            model.html_columns = self._config.html_columns
            model.no_sort_columns = self._config.no_sort_columns
            model.hidden_columns = self._config.hidden_columns
            model.checkable_columns = self._config.checkable_columns
            # model.text_alignment = {
            #     "left": Qt.AlignmentFlag.AlignLeft,
            #     "center": Qt.AlignmentFlag.AlignCenter,
            #     "right": Qt.AlignmentFlag.AlignRight,
            # }[self._config.text_alignment]
        self.setModel(model)

    def setup_model_from_config(self, config: TableConfig):
        """Setup model from config."""
        self.setup_model(
            config.header,
            config.no_sort_columns,
            config.hidden_columns,
            config.html_columns,
            config.icon_columns,
            config.checkable_columns,
            text_alignment={
                "left": Qt.AlignmentFlag.AlignLeft,
                "center": Qt.AlignmentFlag.AlignCenter,
                "right": Qt.AlignmentFlag.AlignRight,
            }[config.text_alignment],
        )

    def setup_model(
        self,
        header: list[str],
        no_sort_columns: list[int] | None = None,
        hidden_columns: list[int] | None = None,
        html_columns: list[int] | None = None,
        icon_columns: list[int] | None = None,
        checkable_columns: list[int] | None = None,
        text_alignment: Qt.AlignmentFlag | None = None,
    ) -> None:
        """Setup model in the table."""
        self.set_data(
            [],
            header,
            no_sort_columns,
            hidden_columns,
            html_columns,
            icon_columns,
            checkable_columns,
            text_alignment=text_alignment,
        )

    def reset_data(self) -> None:
        """Clear table."""
        model = self.model()
        if hasattr(model, "reset_data"):
            model.reset_data()
        self.evt_reset.emit()

    def set_data(
        self,
        data: list,
        header: list[str],
        no_sort_columns: list[int] | None = None,
        hidden_columns: list[int] | None = None,
        html_columns: list[int] | None = None,
        icon_columns: list[int] | None = None,
        color_columns: list[int] | None = None,
        checkable_columns: list[int] | None = None,
        text_alignment: Qt.AlignmentFlag | None = None,
        checkable: bool | str = "auto",
    ) -> None:
        """Set data."""
        self._header_columns = header
        if checkable == "auto" and header:
            checkable = header[0] == ""  # empty column usually indicates that that the first column is checkable
        else:
            checkable = checkable
        self._validate_data(data, len(header))
        model = QtCheckableItemModel(
            self,
            data=data,
            header=header,
            no_sort_columns=no_sort_columns or [],
            hidden_columns=hidden_columns or [],
            color_columns=color_columns or [],
            html_columns=html_columns or [],
            icon_columns=icon_columns or [],
            checkable_columns=checkable_columns or [],
            text_alignment=text_alignment,
        )
        self.checkable = bool(checkable)
        model.evt_checked.connect(self.evt_checked.emit)
        model.evt_value_checked.connect(self.evt_value_checked.emit)
        self.set_model(model)
        self.init()

    def add_row(self, data: list) -> None:
        """ADd row to the data."""
        self.add_data([data])

    def append_data(self, data: list) -> None:
        """Append data."""
        self.add_data(data)

    def add_data(self, data: list[list]) -> None:
        """Add data."""
        n_items = self.n_rows
        self._validate_data(data)
        self.model().add_data(data)
        if n_items == 0:
            self.init()

    def add_index(self, rows: list[str]):
        """Add vertical index."""
        # header.set
        # for i, row in enumerate(rows):
        #     header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        #     header.item

    def add_data_without_set(self, data: list[list]) -> None:
        """Add data."""
        n_items = self.n_rows
        self._validate_data(data)
        self.model().add_data(data)
        if n_items == 0:
            self.init()

    def _validate_data(self, data: list, n_cols: ty.Optional[int] = None) -> None:
        """Validate data."""
        if n_cols is None:
            if self._header_columns is not None:
                n_cols = len(self._header_columns)
            else:
                n_cols = self.n_cols
        for _data in data:
            if len(_data) != n_cols:
                logger.warning("Data is of incorrect size")

    def get_data(self) -> list[list]:
        """Get data from model.

        This returns the native data that is stored in the model.
        """
        data = self.model().get_data()
        return data

    def get_all_checked(self) -> list[int]:
        """Get all checked."""
        return self.model().get_all_checked()

    def get_all_shown(self) -> list[int]:
        """Get all checked."""
        model = self.model()
        proxy = model.table_proxy
        if proxy:
            return proxy.find_visible_rows()[0]
        shown = []
        for index in range(model.rowCount()):
            if not self.isRowHidden(index):
                shown.append(index)
        return shown

    def get_all_unchecked(self) -> list[int]:
        """Get all unchecked.

        Returns
        -------
        list of ints
            List of all rows that are currently unchecked.
        """
        return self.model().get_all_unchecked()

    def toggle_all_rows(self) -> None:
        """Uncheck all values."""
        self.model().toggle_all_rows()

    def check_all_rows(self) -> None:
        """Uncheck all values."""
        self.model().check_all_rows()

    def uncheck_all_rows(self) -> None:
        """Uncheck all values."""
        self.model().uncheck_all_rows()

    def get_initial_index(self, indices: list) -> list[int]:
        """Get initial index."""
        return self.model().get_initial_indices(indices)

    def get_row_id(self, col_id: int, value: ty.Any) -> int:
        """Get the id of a value."""
        return self.model().get_row_id(col_id, value)

    def get_row_id_for_values(self, *column_and_values: ty.Tuple[int, ty.Any]) -> int:
        """Get the id of a value."""
        return self.model().get_row_id_for_values(*column_and_values)

    def get_col_data(self, col_id: int) -> list[ty.Any]:
        """Get data from model."""
        data = self.model().get_data()
        if col_id <= self.n_cols:
            data = [row[col_id] for row in data]
        return data

    def get_row_data(self, row_id: int) -> list:
        """Get data from model."""
        data = self.model().get_data()
        if row_id <= self.n_rows:
            data = data[row_id]
        return data

    def is_checked(self, row_id: int) -> bool:
        """Get check state of value."""
        value = self.get_value(0, row_id)
        if value == "":
            return False
        return bool(value)

    def get_value(self, col_id: int, row_id: int) -> ty.Any:
        """Get data from model."""
        data = self.model().get_data()
        if row_id <= self.n_rows and col_id <= self.n_cols:
            data = data[row_id][col_id]
        return data

    def set_value(self, col_id: int, row_id: int, value: ty.Any) -> None:
        """Set value in the data model."""
        self.model().update_value(row_id, col_id, value)

    def select_row(self, row: int, match_to_sort: bool = True) -> None:
        """Select row."""
        if match_to_sort:
            row = self.model().get_sort_index(row)
        self.selectRow(row)

    def update_value(self, row: int, col: int, value: ty.Any, match_to_sort: bool = True) -> None:
        """Update value in the model."""
        if match_to_sort:
            row = self.model().get_sort_index(row)
        self.model().update_value(row, col, value)

    def remove_row(self, row_id: int) -> None:
        """Remove row from the model."""
        self.model().removeRow(row_id)

    def remove_rows(self, rows: list[int]) -> None:
        """Remove rows from the model."""
        rows = sorted(rows, reverse=True)
        for row in rows:
            self.remove_row(row)

    def update_row(self, row: int, value: list, match_to_sort: bool = True) -> None:
        """Update entire row."""
        if match_to_sort:
            row = self.model().get_sort_index(row)
        self.model().update_row(row, value)

    @contextmanager
    def block_model(self) -> ty.Generator[None, None, None]:
        """Block model signals."""
        with qt_signals_blocked(self.model(), block_signals=True):
            yield
        self.model().reset()

    def update_column(self, col: int, values: list, match_to_sort: bool = True, block_signals: bool = False) -> None:
        """Update entire row."""
        assert len(values) == self.n_rows, (
            f"Tried to set incorrect number of rows. Expected {self.n_rows} - got {len(values)}"
        )
        model = self.model()
        with qt_signals_blocked(model, block_signals=block_signals):
            model.update_column(col, values, match_to_sort)

    def update_values(
        self, row: int, column_value: ty.Dict[int, ty.Union[str, int, float, bool]], match_to_sort: bool = True
    ) -> None:
        """Update multiple columns for a particular row."""
        if match_to_sort:
            row = self.model().get_sort_index(row)
        self.model().update_values(row, column_value)

    def sort_by_column(self, column: int, direction: ty.Union[Qt.SortOrder, str] = "ascending") -> None:
        """Sort table by column."""
        if isinstance(direction, str):
            direction = Qt.SortOrder.AscendingOrder if direction == "ascending" else Qt.SortOrder.DescendingOrder
        self.model().sort(column, direction)

    def find_index_of(self, col_id: int, value: ty.Any) -> int:
        """Find index of value. Return -1 if not found."""
        col_data = self.get_col_data(col_id)
        try:
            return col_data.index(value)
        except ValueError:
            return -1

    def find_indices_of(self, col_id: int, value: ty.Any) -> list[int]:
        """Find index of value. Return -1 if not found."""
        col_data = self.get_col_data(col_id)
        indices = [i for i, x in enumerate(col_data) if x == value]
        return indices

    def find_index_of_value_with_indices(self, col_id: int, value: ty.Any, indices: list[int]) -> int:
        """Find index of value. Return -1 if not found."""
        col_data = self.get_col_data(col_id)
        for i in indices:
            if col_data[i] == value:
                return i
        return -1

    def sortByColumn(self, index: int) -> None:
        """Override method."""
        if index == 0 and self.checkable:
            self.header.setSortIndicatorShown(False)
            if self.enable_all_check:
                self.model().toggle_all_rows()
            return
        else:
            self.header.setSortIndicatorShown(True)
        order = self.horizontalHeader().sortIndicatorOrder()
        return QTableView.sortByColumn(self, index, order)

    def keyPressEvent(self, event):
        """Process key event press."""
        super().keyPressEvent(event)
        row = self.currentIndex().row()
        self.selectRow(row)
        event.row = lambda: row  # make row retrieval a function so its compatible with other methods
        self.evt_keypress.emit(event)

    #         # take into account change of order
    #         idx = self.model().get_initial_index(row) if row >= 0 else -1
    #         self.keyPressSignal.emit(idx)

    def create_index(self, row: int = 0, column: int = 0) -> QModelIndex:
        """Create index."""
        return self.model().createIndex(row, column)
