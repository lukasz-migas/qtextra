"""Table view of numpy or pandas array."""

from __future__ import annotations

import typing as ty

import numpy as np
import pandas as pd
from koyo.timer import MeasureTimer
from koyo.utilities import find_nearest_index_single
from loguru import logger
from qtpy.QtCore import QAbstractTableModel, QModelIndex, QRect, Qt, Signal  # type: ignore[attr-defined]
from qtpy.QtGui import QBrush, QColor, QKeyEvent
from qtpy.QtWidgets import QAbstractItemView, QHeaderView, QTableView, QWidget

from qtextra.utils.color import get_text_color

if ty.TYPE_CHECKING:
    from matplotlib.colors import Normalize

TEXT_COLOR: str = "#000000"
N_COLORS = 256
BATCH_SIZE = 50
INITIAL_SIZE = 100


class QtRotatedHeaderView(QHeaderView):
    """Horizontal header where the view is rotated by 90 degrees."""

    def __init__(self, parent=None):
        super().__init__(Qt.Orientation.Horizontal, parent)
        self.setMinimumSectionSize(20)

    def paintSection(self, painter, rect, logicalIndex):
        """Paint section."""
        painter.save()
        # translate the painter such that rotate will rotate around the correct point
        painter.translate(rect.x() + rect.width(), rect.y())
        painter.rotate(90)
        # and have parent code paint at this location
        newrect = QRect(0, 0, rect.height(), rect.width())
        super().paintSection(painter, newrect, logicalIndex)
        painter.restore()

    def minimumSizeHint(self) -> Qt.SizeHint:
        """Minimum size hint."""
        size = super().minimumSizeHint()
        size.transpose()
        return size

    def sectionSizeFromContents(self, logicalIndex):
        """Section size from contents."""
        size = super().sectionSizeFromContents(logicalIndex)
        size.transpose()
        return size


class QtArrayTableModel(QAbstractTableModel):
    """Model for the table."""

    df: pd.DataFrame
    base_df: pd.DataFrame
    colors: dict[int, QColor] | None = None
    color_list: np.ndarray | None = None
    normalizer: Normalize | None = None
    max_color: QColor = None
    n_total: int = 0
    n_loaded: int = 0
    fmt: str = "{}"

    def __init__(self, parent: QWidget, data: ty.Union[np.ndarray, pd.DataFrame]):
        super().__init__(parent)
        self.set_data(data)

    def set_data(self, data: ty.Union[np.ndarray, pd.DataFrame]) -> None:
        """Set data in model."""
        if isinstance(data, np.ndarray):
            data = pd.DataFrame(data)
        assert data.ndim == 2, "The table can only display arrays with two-dimensions."
        self.df = data.iloc[:BATCH_SIZE, :]
        self.base_df = data
        self.colors = None
        self.color_list = None
        self.n_total = len(self.base_df)
        self.n_loaded = len(self.df)
        self.reset()

    def set_formatting(self, fmt: str) -> None:
        """Text formatter."""
        self.fmt = fmt

    def set_colormap(self, colormap: str, min_val: float | None = None, max_val: float | None = None) -> None:
        """Set colormap."""
        import matplotlib.cm
        import matplotlib.colors

        with MeasureTimer() as timer:
            if colormap:
                colormap = matplotlib.cm.get_cmap(colormap, lut=N_COLORS)
                if min_val is None:
                    min_val = self.base_df.min().min()
                if max_val is None:
                    max_val = self.base_df.max().max()
                normalizer = matplotlib.colors.Normalize(min_val, max_val, clip=True)

                colors = {}
                step_size = (abs(min_val) + abs(max_val)) / N_COLORS
                value_list = np.arange(min_val, max_val + step_size, step_size)
                # value_list = np.linspace(min_val, max_val, N_COLORS)
                for i, value in enumerate(value_list):
                    color = np.asarray(colormap(normalizer(value)))
                    colors[i] = QColor(*(255 * color).astype("int"))
                self.color_list = np.linspace(0, 1, N_COLORS)
                self.max_color = colors[i]
                self.colors = colors
                self.normalizer = normalizer
            else:
                self.colors, self.color_list = None, None
        logger.trace(f"Set colormap in {timer()}.")

    def reset(self) -> None:
        """Reset model."""
        self.beginResetModel()
        self.endResetModel()

    def reset_data(self) -> None:
        """Reset data."""
        with MeasureTimer() as timer:
            self.df = self.df.iloc[0:0]
            self.base_df = self.base_df.iloc[0:0]
            self.reset()
        logger.trace(f"Reset data in {timer()}.")

    def data(self, index: QModelIndex, role: Qt.ItemDataRole | None = None) -> ty.Any:
        """Parse data."""
        if not index.isValid():
            return None
        # background color
        if role == Qt.ItemDataRole.BackgroundRole:
            if self.colors and self.normalizer:
                value = self.normalizer(self.df.iloc[index.row(), index.column()])
                index = find_nearest_index_single(self.color_list, value)
                color = self.colors.get(index, self.max_color)
                return QBrush(color)
            return QBrush()
        # text color
        elif role == Qt.ItemDataRole.ForegroundRole:
            if self.colors and self.normalizer:
                value = self.normalizer(self.df.iloc[index.row(), index.column()])
                index = find_nearest_index_single(self.color_list, value)
                color = self.colors.get(index, self.max_color)
                return QBrush(get_text_color(color))
            return QBrush(QColor(TEXT_COLOR))
        # display value
        elif role == Qt.ItemDataRole.DisplayRole:
            value = self.df.iloc[index.row(), index.column()]
            return self.fmt.format(value)
        # check alignment role
        elif role == Qt.ItemDataRole.TextAlignmentRole:
            return Qt.AlignmentFlag.AlignCenter

    def headerData(
        self, index: QModelIndex, orientation: Qt.Orientation, role: Qt.ItemDataRole | None = None
    ) -> str | None:
        """Get header data."""
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return str(self.df.columns[index])
        if orientation == Qt.Orientation.Vertical and role == Qt.ItemDataRole.DisplayRole:
            return str(self.df.index[index])
        return None

    def rowCount(self, parent: QWidget | None = None, **kwargs: ty.Any) -> int:
        """Return number of rows."""
        return self.df.shape[0] if self.df is not None else 0

    def columnCount(self, parent: QWidget | None = None, **kwargs: ty.Any) -> int:
        """Return number of columns."""
        return self.df.shape[1] if self.df is not None else 0

    def canFetchMore(self, parent: QWidget | None = None) -> bool:
        """Check whether you can fetch more data."""
        return self.n_total >= self.n_loaded

    def fetchMore(self, index: QModelIndex) -> None:
        """Fetch more data."""
        with MeasureTimer() as timer:
            reminder = self.n_total - self.n_loaded
            items_to_fetch = min(reminder, BATCH_SIZE)
            self.beginInsertRows(QModelIndex(), self.n_loaded, self.n_loaded + items_to_fetch - 1)
            self.n_loaded += items_to_fetch
            self.df = self.base_df.iloc[: self.n_loaded, :]
            self.endInsertRows()
        logger.trace(f"Fetched {items_to_fetch} items in {timer()}.")

    def sort(self, column: int, order: Qt.SortOrder = ...) -> None:
        """Sort data."""
        self.beginResetModel()
        try:
            self.df = self.df.sort_values(self.df.columns[column], ascending=order == Qt.SortOrder.AscendingOrder)
        except TypeError:
            pass
        self.endResetModel()


class QtArrayTableView(QTableView):
    """Array table."""

    evt_key_release = Signal(QKeyEvent)

    model: ty.Callable[[], QtArrayTableModel]

    def __init__(self, *args: ty.Any, sortable: bool = False, **kwargs: ty.Any):
        super().__init__(*args, **kwargs)
        self.sortable = sortable
        if self.sortable:
            self.horizontalHeader().sectionClicked.connect(self.sortByColumn)
            self.horizontalHeader().setSortIndicatorShown(True)

    def sortByColumn(self, index: int) -> None:
        """Override method."""
        order = self.horizontalHeader().sortIndicatorOrder()
        return QTableView.sortByColumn(self, index, order)

    def keyReleaseEvent(self, event) -> None:
        """Process key event press."""
        super().keyReleaseEvent(event)
        row = self.currentIndex().row()
        col = self.currentIndex().column()
        event.row = lambda: row  # make row retrieval a function so its compatible with other methods
        event.column = lambda: col  # make row retrieval a function so its compatible with other methods
        self.evt_key_release.emit(event)

    def set_data(
        self,
        data: ty.Union[np.ndarray, pd.DataFrame],
        fmt: str = "{:d}",
        colormap: str | None = None,
        min_val: float | None = None,
        max_val: float | None = None,
    ) -> None:
        """Set data."""
        model = QtArrayTableModel(self, data)
        model.set_colormap(colormap, min_val, max_val)
        if fmt:
            model.set_formatting(fmt)
        self.setModel(model)
        self.init()

    def set_formatting(self, fmt: str) -> None:
        """Text formatter."""
        # let's perform simple test to make sure value can be rendered
        fmt.format(42.0)

        # set value on model
        model = self.model()
        if model:
            model.set_formatting(fmt)
            model.reset()

    def set_colormap(self, colormap: str, min_val: float | None = None, max_val: float | None = None) -> None:
        """Set colormap."""
        model: QtArrayTableModel = self.model()
        if model:
            model.set_colormap(colormap, min_val, max_val)
            model.reset()

    def init(self) -> None:
        """Initialize table to ensure correct visuals."""
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setDragEnabled(True)
        header = self.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        # self.setHorizontalHeader(QtRotatedHeaderView(self))

    def reset_data(self) -> None:
        """Reset data."""
        model = self.model()
        if model:
            model.reset_data()


if __name__ == "__main__":  # pragma: no cover
    import sys

    from qtextra.utils.dev import qframe

    app, frame, va = qframe(False)
    frame.setMinimumSize(400, 400)

    table = QtArrayTableView()
    va.addWidget(table)
    table.set_data(
        np.asarray([[-1, 0, 1], [1, 0, -1]]),
        # np.random.randint(-255, 255, (5, 5)) / 255,
        fmt="{:.2f}",
        colormap="coolwarm",
        min_val=-1,
        max_val=1,
    )

    frame.show()
    sys.exit(app.exec_())
