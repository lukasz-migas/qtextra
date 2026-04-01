# ruff: noqa: D102
"""
Defines the DataFrameViewer class to display DataFrames as a table. The DataFrameViewer is made up of three separate
QTableWidgets... DataTableView for the DataFrame's contents, and two HeaderView widgets for the column and index
 headers.
"""

from __future__ import annotations

import contextlib
import typing as ty

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
    ):
        super().__init__(parent)
        df = _normalize_tabular_data(df, inplace=inplace)

        # Indicates whether the widget has been shown yet. Set to True in
        self._loaded = False
        self.editable = editable

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
        """Set data header."""
        df = _normalize_tabular_data(df)
        self._loaded = False
        self.setUpdatesEnabled(False)
        try:
            self.dataView.set_data(df)
            self.columnHeader.set_data(df)
            self.indexHeader.set_data(df)
            self.cornerView.set_data(df)
            self._init_sizes()
            self._update_scrollbar_visibility()
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

    def _sync_vertical_scrollbar_visibility(self, _min: int, max_value: int) -> None:
        """Update vertical scrollbar visibility."""
        self.dataView.verticalScrollBar().setVisible(max_value > 0)

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
        self.columnHeader._apply_extent()
        self.indexHeader._apply_extent()
        self._sync_corner_view()

    def auto_size_column(self, column_index):
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

        self.columnHeader.setColumnWidth(column_index, width)
        self.dataView.setColumnWidth(column_index, width)

    def auto_size_row(self, row_index):
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

    def set_data(self, df):
        """Set data model."""
        df = _normalize_tabular_data(df)
        with contextlib.suppress(Exception):
            self.selectionModel().selectionChanged.disconnect(self.on_selection_changed)
        model = DataTableModel(df)
        self.setModel(model)
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
        # from threading import Thread
        #
        # # Get the bounds using the top left and bottom right selected cells
        # indexes = self.selectionModel().selection().indexes()
        #
        # rows = [ix.row() for ix in indexes]
        # cols = [ix.column() for ix in indexes]
        #
        # df = self.model().df.iloc[min(rows) : max(rows) + 1, min(cols) : max(cols) + 1]
        #
        # # If I try to use Pyperclip without starting new thread large values give access denied error
        # def thread_function(df):
        #     df.to_clipboard(index=False, header=False)
        #
        # Thread(target=thread_function, args=(df,)).start()
        #
        # clipboard = Qg.QGuiApplication.clipboard()
        # clipboard.setText(text)

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

    def __init__(self, df, orientation, parent=None):
        super().__init__(parent)
        self.df = _normalize_tabular_data(df)
        self.orientation = orientation

    def columnCount(self, parent=None):
        """Number of columns."""
        if self.orientation == Qt.Orientation.Horizontal:
            return self.df.columns.shape[0]
        # Vertical
        return self.df.index.nlevels

    def rowCount(self, parent=None):
        """Number of rows."""
        if self.orientation == Qt.Orientation.Horizontal:
            return self.df.columns.nlevels
        if self.orientation == Qt.Orientation.Vertical:
            return self.df.index.shape[0]
        return None

    def data(self, index, role=None):
        """Data."""
        row = index.row()
        col = index.column()

        if role == Qt.ItemDataRole.DisplayRole or role == Qt.ItemDataRole.ToolTipRole:
            if self.orientation == Qt.Orientation.Horizontal:
                if isinstance(self.df.columns, pd.MultiIndex):
                    return str(self.df.columns.values[col][row])
                return str(self.df.columns.values[col])

            if self.orientation == Qt.Orientation.Vertical:
                if isinstance(self.df.index, pd.MultiIndex):
                    return str(self.df.index.values[row][col])
                return str(self.df.index.values[row])
            return None
        if role == Qt.ItemDataRole.FontRole:
            bold_font = Qg.QFont()
            bold_font.setBold(True)
            return bold_font
        return None

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

    def __init__(self, df, parent=None):
        super().__init__(parent)
        self.df = _normalize_tabular_data(df)

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

    def data(self, index, role=None):
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
        self.set_data(df)

    def set_data(self, df) -> None:
        """Update corner model."""
        self.setModel(CornerModel(df, self))
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
            self.setSpan(0, 0, rows - 1, cols - 1)


class HeaderView(Qw.QTableView):
    """Displays the DataFrame index or columns depending on orientation."""

    df = None

    def __init__(self, parent: QtDataFrameWidget, df: pd.DataFrame, orientation: Qt.Orientation):
        super().__init__(parent)

        # Setup
        self.orientation = orientation
        self.parent = parent
        self.table = parent.dataView
        self.set_data(df)

        # These are used during column resizing
        self.header_being_resized = None
        self.resize_start_position = None
        self.initial_header_size = None

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

    def set_data(self, df):
        """Update dataframe."""
        df = _normalize_tabular_data(df)
        self.df = df
        with contextlib.suppress(Exception):
            self.selectionModel().selectionChanged.disconnect(self.on_selection_changed)
        self.setModel(HeaderModel(df, self.orientation))
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
                width = max(DEFAULT_COLUMN_WIDTH, self.table.columnWidth(col))
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
                    arr = [df.columns[i][level] for i in range(len(df.columns))]
                else:
                    arr = df.columns

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
                            self.setSpan(level, match_start, 1, span_size)
                    else:
                        if match_start is not None:
                            match_end = col - 1
                            span_size = match_end - match_start + 1
                            self.setSpan(level, match_start, 1, span_size)
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
                    arr = [df.index[i][level] for i in range(len(df.index))]
                else:
                    arr = df.index

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
                            self.setSpan(match_start, level, span_size, 1)
                    else:
                        if match_start is not None:
                            match_end = row - 1
                            span_size = match_end - match_start + 1
                            self.setSpan(match_start, level, span_size, 1)
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
            if self.orientation == Qt.Orientation.Horizontal:
                mouse_position = event.pos().x()
            elif self.orientation == Qt.Orientation.Vertical:
                mouse_position = event.pos().y()

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
            self.header_being_resized = None

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

            # If this is None, there is no drag resize happening
            if self.header_being_resized is not None:
                size = self.initial_header_size + (mouse_position - self.resize_start_position)
                if size > 10:
                    if self.orientation == Qt.Orientation.Horizontal:
                        self.setColumnWidth(self.header_being_resized, size)
                        self.parent.dataView.setColumnWidth(self.header_being_resized, size)
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
    btn.clicked.connect(lambda: widget.set_data(_get_new_data()))
    va.addWidget(btn)

    frame.show()
    sys.exit(app.exec_())
