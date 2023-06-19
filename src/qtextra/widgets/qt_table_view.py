"""Table view."""
import operator
import typing as ty
from contextlib import suppress

import numpy as np
from loguru import logger
from natsort.natsort import index_natsorted, order_by_index
from qtpy.QtCore import QAbstractTableModel, QModelIndex, Qt, Signal, Slot
from qtpy.QtGui import QBrush, QColor, QKeyEvent
from qtpy.QtWidgets import QAbstractItemView, QHeaderView, QTableView

from qtextra.config import THEMES
from qtextra.helpers import make_qta_icon
from qtextra.utils.table_config import TableConfig
from qtextra.utils.utilities import connect, get_text_color

TEXT_COLOR: str = "#000000"
LINK_COLOR: str = "#0000FF"


class QtCheckableItemModel(QAbstractTableModel):
    """Checkable item model."""

    evt_checked = Signal(int, bool)

    def __init__(
        self,
        parent,
        data: ty.List[ty.List],
        header=None,
        no_sort_col=None,
        hidden_col=None,
        color_col: ty.Optional[ty.List[int]] = None,
        html_col: ty.Optional[ty.List[int]] = None,
        icon_col: ty.Optional[ty.List[int]] = None,
    ):
        QAbstractTableModel.__init__(self, parent)

        # attributes
        if hidden_col is None:
            hidden_col = []
        if no_sort_col is None:
            no_sort_col = []
        if header is None:
            header = []
        if color_col is None:
            color_col = []
        if html_col is None:
            html_col = []
        if icon_col is None:
            icon_col = []

        self._table = data
        self._no_sort_col = no_sort_col
        self._hidden_col = hidden_col
        self.state = False
        self.original_index = list(range(len(self._table)))
        self.header = header
        self.color_column = color_col
        self.html_column = html_col
        self.icon_column = icon_col

    def flags(self, index):
        """Return flags."""
        fl = Qt.ItemIsEnabled | Qt.ItemIsSelectable
        if index.column() == 0:
            fl |= Qt.ItemIsUserCheckable
        else:
            fl |= Qt.ItemIsEditable
        return fl

    @property
    def n_checked(self) -> int:
        """Return of checked elements."""
        return [row[0] for row in self._table].count(True)

    @property
    def n_unchecked(self) -> int:
        """Return count of unchecked elements."""
        return [row[0] for row in self._table].count(False)

    def rowCount(self, parent=None, **kwargs):
        """Return number of rows."""
        return len(self._table) if self._table else 0

    def columnCount(self, parent=None, **kwargs):
        """Return number of columns."""
        return len(self._table[0]) if self._table else 0

    def removeRow(self, row: int, parent: QModelIndex = QModelIndex()) -> bool:
        """Remove row."""
        self.beginRemoveRows(parent, row, row)
        self._table.pop(row)
        self.original_index.pop(row)
        self.endRemoveRows()

    def data(self, index, role=None):
        """Parse data."""
        if not index.isValid():
            return None

        row = index.row()
        column = index.column()

        # check background color role
        if role == Qt.BackgroundRole:
            if column in self.color_column:
                color = self._table[row][column]
                if isinstance(color, str) and "#" in color:
                    return QBrush(QColor(color))
                elif isinstance(color, np.ndarray):
                    return QBrush(QColor(*(255 * color).astype("int")))
                if isinstance(color, QColor):
                    return QBrush(color)
            return QBrush()
        # check text color
        elif role == Qt.ForegroundRole:
            if column == self.color_column:
                bg_color = self._table[row][column]
                if isinstance(bg_color, str) and "#" in bg_color:
                    return QBrush(get_text_color(QColor(bg_color)))
            # let's use slightly different color html
            if column in self.html_column:
                return QBrush(QColor(LINK_COLOR))
            return QBrush(QColor(TEXT_COLOR))
        # check value
        elif role == Qt.DisplayRole:
            if column not in self.icon_column:
                value = self._table[row][column]
                return value
        # check alignment role
        elif role == Qt.TextAlignmentRole:
            return Qt.AlignCenter
        # check state
        elif role == Qt.CheckStateRole and column == 0:
            return Qt.Checked if self._table[row][column] else Qt.Unchecked
        # icon state
        elif role == Qt.DecorationRole:
            if column in self.icon_column:
                value = self._table[row][column]
                return make_qta_icon(value)

    def headerData(self, col, orientation, role=None):
        """Get header data."""
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.header[col]
        return None

    def sort(self, column: int, order=None):
        """Sort table."""
        if self._no_sort_col and column in self._no_sort_col:
            return

        # emit signal about upcoming change
        self.layoutAboutToBeChanged.emit()

        # get sort index
        new_index = index_natsorted(self._table, key=operator.itemgetter(column))

        # sort
        self._table = order_by_index(self._table, new_index)
        self.original_index = order_by_index(self.original_index, new_index)

        if order == Qt.DescendingOrder:
            self._table.reverse()
            self.original_index.reverse()

        # indicate that change to data has been made
        self.layoutChanged.emit()

    def setData(self, index, value, role=Qt.EditRole):
        """Set data in the model."""
        row = index.row()
        column = index.column()

        if role == Qt.CheckStateRole:
            value = value != Qt.Unchecked
            change = True
        else:
            old_value = index.data()
            if isinstance(old_value, np.ndarray):
                change = np.any(old_value != value)
            else:
                change = old_value != value

        if change:
            self._table[row][column] = value
            self.dataChanged.emit(row, column)
            if column == 0:
                self.evt_checked.emit(row, value)
            return True
        return False

    def update_value(self, row, column, value, role=Qt.EditRole):
        """Update value."""
        index = self.createIndex(row, column)

        # setup role
        if column == 0:
            role = Qt.CheckStateRole

        if index.isValid():
            self.setData(index, value, role=role)

    def update_values(self, row, column_value):
        """Update values."""
        for column, value in column_value.items():
            self.update_value(row, column, value)

    def update_row(self, row, value):
        """Update row."""
        if len(value) != len(self.header):
            raise ValueError("Cannot update row as length of the values does not match header length")

        for column in range(len(self.header)):
            index = self.createIndex(row, column)
            if index.isValid():
                self.setData(index, value[column])

    def update_column(self, col, values, match_to_sort: bool = True):
        """Update column."""
        if col > self.columnCount():
            raise ValueError("Cannot update column as its outside of the boundaries")

        if col > self.rowCount():
            raise ValueError("Cannot update column as the length of the values does not match the number of rows")

        for row, value in enumerate(values):
            if match_to_sort:
                row = self.get_sort_index(row)
            index = self.createIndex(row, col)
            if index.isValid():
                self.setData(index, value)

    def check_all_rows(self):
        """Check all rows in the table."""
        self.state = not self.state
        for row, __ in enumerate(self._table):
            self._table[row][0] = self.state
            self.dataChanged.emit(row, 0)
        self.evt_checked.emit(-1, self.state)

    def uncheck_all_rows(self):
        """Uncheck all rows."""
        for row, __ in enumerate(self._table):
            self._table[row][0] = False
            self.dataChanged.emit(row, 0)
        self.evt_checked.emit(-1, False)

    def get_all_checked(self) -> ty.List[int]:
        """Get all checked items."""
        return self._get_all_state(True)

    def get_all_unchecked(self) -> ty.List[int]:
        """Get all unchecked items."""
        return self._get_all_state(False)

    def _get_all_state(self, state: bool) -> ty.List[int]:
        """Get all checked items."""
        checked = []
        for i, row in enumerate(self._table):
            if row[0] is state:
                checked.append(i)
        return checked

    def roleNames(self):
        """Return role names."""
        roles = QAbstractTableModel.roleNames(self)
        roles["Checked"] = Qt.CheckStateRole
        return roles

    def reset(self):
        """Reset model."""
        self.beginResetModel()
        self.endResetModel()

    def get_initial_index(self, row: int):
        """Get the index of the initial array, regardless of whether it was sorted."""
        return self.original_index[row]

    def get_initial_indices(self, index: list):
        """Get list of all initial indices."""
        return [self.get_initial_index(row) for row in index]

    def get_sort_index(self, row: int):
        """Get the index inside the sorted array as matched from the not-sorted array."""
        return self.original_index.index(row)

    def get_sort_indices(self, index: list):
        """Get list of all sort indices."""
        return [self.get_sort_index(row) for row in index]

    def get_data(self):
        """Get data from model."""
        return self._table

    def get_row_id(self, col_id: int, value: str) -> int:
        """Find value index."""
        for row_id, row in enumerate(self._table):
            if row[col_id] == value:
                return row_id
        return -1

    def add_data(self, data: ty.List):
        """Add data."""
        self._table.extend(data)
        self.original_index = list(range(len(self._table)))
        # indicate that change to data has been made
        self.layoutChanged.emit()

    def reset_data(self):
        """Reset data."""
        self._table.clear()
        self.original_index.clear()
        self.layoutChanged.emit()

    def data_changed(self):
        """Emit an event when there has been change to the model."""
        self.layoutChanged.emit()


class QtCheckableTableView(QTableView):
    """Checkbox table."""

    # events
    # triggered whenever item is checked/unchecked. It returns the index and check state when its triggered.
    # It behaves slightly differently when user clicks on the header and -1 is emitted rather than actual index
    evt_checked = Signal(int, bool)
    # keyboard event
    evt_keypress = Signal(QKeyEvent)
    # value changed
    evt_changed = Signal()

    def __init__(
        self,
        *args,
        config: TableConfig = None,
        enable_all_check: bool = True,
        double_click_to_check: bool = False,
        sortable: bool = True,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        # setup config
        self._color_column = [-1]
        self._config = config
        self._header_columns = None
        self._is_init = False
        self._enable_all_check = enable_all_check
        self._double_click_to_check = double_click_to_check
        self._sortable = sortable

        # register events
        self.clicked.connect(self.on_table_clicked)
        if self._sortable:
            self.header.sectionClicked.connect(self.sortByColumn)
        if self._double_click_to_check:
            self.doubleClicked.connect(self._on_check_row)

        if isinstance(self._config, TableConfig):
            self.init_from_config()

        connect(THEMES.evt_theme_changed, self._update_color_theme, state=True)

    def closeEvent(self, event) -> None:
        """Close event."""
        connect(THEMES.evt_theme_changed, self._update_color_theme, state=False)
        return super().closeEvent(event)

    @Slot()
    def _update_color_theme(self):
        """Update global color theme."""
        global TEXT_COLOR, LINK_COLOR
        TEXT_COLOR = THEMES.get_theme_color()
        LINK_COLOR = THEMES.get_hex_color("highlight")
        with suppress(RuntimeError):
            self.update()

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

    def column_count(self):
        """Return the number columns."""
        return self.model().columnCount(self) if self.model() else 0

    def row_count(self):
        """Return the number of rows."""
        return self.model().rowCount(self) if self.model() else 0

    @property
    def header(self):
        """Return header."""
        return self.horizontalHeader()

    def on_table_clicked(self, index: QModelIndex = None) -> None:
        """Imitate row selection."""
        if index is None:
            index = QModelIndex()
        if not index.isValid():
            return
        row = index.row()
        self.selectRow(row)

    def init(self) -> None:
        """Initialize table to ensure correct visuals."""
        # Get hook for the header
        n_cols = self.column_count()
        header = self.header
        # 25 px is optimal size for checkbox
        header.setMinimumSectionSize(25)
        for n_col in range(n_cols):
            # The first column should always be a QCheckbox
            mode = QHeaderView.Fixed if n_col == 0 else QHeaderView.Stretch
            header.setSectionResizeMode(n_col, mode)

        # set column width for the first column (checkbox)
        self.setColumnWidth(0, 25)

        # disable editing
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)

        # enable sorting
        self.setSortingEnabled(self._sortable)
        # disable drag
        self.setDragEnabled(False)

        # hide columns
        model = self.model()
        for n_col in model._hidden_col:
            self.setColumnHidden(n_col, True)

        self._is_init = True
        model.data_changed()

    def set_column_resize_mode(self, index: int, mode: QHeaderView.ResizeMode = QHeaderView.Stretch):
        """Set column resize mode."""
        if self._is_init:
            self.header.setSectionResizeMode(index, mode)

    @Slot(int, bool)
    def on_check(self, row: int, value: bool):
        """Check."""
        self.evt_checked.emit(row, value)

    def init_from_config(self):
        """Initialize based on config."""
        self._color_column = [self._config.color_column]
        self.set_data(
            [],
            self._config.header,
            self._config.no_sort_columns,
            self._config.hidden_columns,
            icon_col=self._config.icon_columns,
        )

    def set_model(self, model):
        """Set model."""
        self.setModel(model)

    def setup_model(
        self,
        header: ty.List[str],
        no_sort_col: ty.List[int] = None,
        hidden_col: ty.List[int] = None,
        html_col: ty.List[int] = None,
        icon_col: ty.List[int] = None,
    ):
        """Setup model in the table."""
        if hidden_col is None:
            hidden_col = []
        if no_sort_col is None:
            no_sort_col = []
        self.set_data([], header, no_sort_col, hidden_col, html_col, icon_col)

    def reset_data(self):
        """Clear table."""
        self.model().reset_data()

    def set_data(
        self,
        data: ty.List,
        header: ty.List[str],
        no_sort_col: ty.List[int] = None,
        hidden_col: ty.List[int] = None,
        html_col: ty.List[int] = None,
        icon_col: ty.List[int] = None,
    ) -> None:
        """Set data."""
        if hidden_col is None:
            hidden_col = []
        if no_sort_col is None:
            no_sort_col = []
        self._header_columns = header
        self._validate_data(data, len(header))
        model = QtCheckableItemModel(
            self,
            data,
            header,
            no_sort_col,
            hidden_col,
            color_col=self._color_column,
            html_col=html_col,
            icon_col=icon_col,
        )
        model.evt_checked.connect(self.on_check)
        self.set_model(model)
        self.init()

    def add_row(self, data: ty.List):
        """ADd row to the data."""
        self.add_data([data])

    def add_data(self, data: ty.List[ty.List]):
        """Add data."""
        n_items = self.n_rows
        self._validate_data(data)
        self.model().add_data(data)
        if n_items == 0:
            self.init()

    def _validate_data(self, data: ty.List, n_cols=None):
        """Validate data."""
        if n_cols is None:
            if self._header_columns is not None:
                n_cols = len(self._header_columns)
            else:
                n_cols = self.n_cols
        for _data in data:
            if len(_data) != n_cols:
                logger.warning("Data is of incorrect size")

    def get_data(self) -> ty.List[ty.List]:
        """Get data from model.

        This returns the native data that is stored in the model.
        """
        data = self.model().get_data()
        return data

    def get_all_checked(self) -> ty.List[int]:
        """Get all checked.

        Returns
        -------
        list of ints
            List of all rows that are currently checked.
        """
        return self.model().get_all_checked()

    def get_all_unchecked(self) -> ty.List[int]:
        """Get all unchecked.

        Returns
        -------
        list of ints
            List of all rows that are currently unchecked.
        """
        return self.model().get_all_unchecked()

    def uncheck_all_rows(self):
        """Uncheck all values."""
        self.model().uncheck_all_rows()

    def get_initial_index(self, indices: ty.List) -> ty.List[int]:
        """Get initial index."""
        return self.model().get_initial_indices(indices)

    def get_row_id(self, col_id: int, value: str) -> int:
        """Get the id of a value."""
        return self.model().get_row_id(col_id, value)

    def get_col_data(self, col_id: int) -> ty.List[ty.List]:
        """Get data from model."""
        data = self.model().get_data()
        if col_id <= self.n_cols:
            data = [row[col_id] for row in data]
        return data

    def get_row_data(self, row_id: int) -> ty.List:
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

    def get_value(self, col_id: int, row_id: int) -> str:
        """Get data from model."""
        data = self.model().get_data()
        if row_id <= self.n_rows and col_id <= self.n_cols:
            data = data[row_id][col_id]
        return data

    def set_value(self, col_id: int, row_id: int, value: ty.Union[str, int, float, bool]):
        """Set value in the data model."""
        self.model().update_value(row_id, col_id, value)

    def select_row(self, row: int, match_to_sort: bool = True) -> None:
        """Select row."""
        if match_to_sort:
            row = self.model().get_sort_index(row)
        self.selectRow(row)

    def update_value(
        self, row: int, col: int, value: ty.Union[str, int, float, bool], match_to_sort: bool = True
    ) -> None:
        """Update value in the model."""
        if match_to_sort:
            row = self.model().get_sort_index(row)
        self.model().update_value(row, col, value)

    def remove_row(self, row_id: int):
        """Remove row from the model."""
        self.model().removeRow(row_id)

    def update_row(self, row: int, value: ty.List, match_to_sort: bool = True) -> None:
        """Update entire row."""
        if match_to_sort:
            row = self.model().get_sort_index(row)
        self.model().update_row(row, value)

    def update_column(self, col: int, values: ty.List, match_to_sort: bool = True) -> None:
        """Update entire row."""
        assert len(values) == self.n_rows, "Tried to set incorrect number of rows."
        self.model().update_column(col, values, match_to_sort)

    def update_values(
        self, row: int, column_value: ty.Dict[int, ty.Union[str, int, float, bool]], match_to_sort: bool = True
    ) -> None:
        """Update multiple columns for a particular row."""
        if match_to_sort:
            row = self.model().get_sort_index(row)
        self.model().update_values(row, column_value)

    def sort_by_column(self, column: int, direction: ty.Union[Qt.SortOrder, str]) -> None:
        """Sort table by column."""
        if isinstance(direction, str):
            direction = Qt.AscendingOrder if direction == "ascending" else Qt.DescendingOrder
        self.model().sort(column, direction)

    def find_index_of(self, col_id: int, value: ty.Any):
        """Find index of value. Return -1 if not found."""
        col_data = self.get_col_data(col_id)
        try:
            return col_data.index(value)
        except ValueError:
            return -1

    def sortByColumn(self, index):
        """Override method."""
        if index == 0 and self._enable_all_check:
            self.header.setSortIndicatorShown(False)
            self.model().check_all_rows()
            return
        else:
            self.header.setSortIndicatorShown(True)
        return QTableView.sortByColumn(self, index)

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
