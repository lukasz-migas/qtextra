"""Table view of numpy or pandas array."""
import typing as ty

import numpy as np
import pandas as pd
from imimspy.processing.utilities import find_nearest_index_batch
from qtpy.QtCore import QAbstractTableModel, QModelIndex, QRect, Qt, Signal
from qtpy.QtGui import QBrush, QColor, QKeyEvent
from qtpy.QtWidgets import QAbstractItemView, QHeaderView, QTableView

from qtextra.utils.utilities import get_text_color

TEXT_COLOR: str = "#000000"
N_COLORS = 256
BATCH_SIZE = 25
INITIAL_SIZE = 100


class QtRotatedHeaderView(QHeaderView):
    """Horizontal header where the view is rotated by 90 degrees."""

    def __init__(self, parent=None):
        super().__init__(Qt.Horizontal, parent)
        self.setMinimumSectionSize(20)

    def paintSection(self, painter, rect, logicalIndex):
        painter.save()
        # translate the painter such that rotate will rotate around the correct point
        painter.translate(rect.x() + rect.width(), rect.y())
        painter.rotate(90)
        # and have parent code paint at this location
        newrect = QRect(0, 0, rect.height(), rect.width())
        super().paintSection(painter, newrect, logicalIndex)
        painter.restore()

    def minimumSizeHint(self):
        size = super().minimumSizeHint()
        size.transpose()
        return size

    def sectionSizeFromContents(self, logicalIndex):
        size = super().sectionSizeFromContents(logicalIndex)
        size.transpose()
        return size


class QtArrayTableModel(QAbstractTableModel):
    """Model for the table."""

    df: pd.DataFrame
    base_df: pd.DataFrame
    colors, color_list, normalizer = None, None, None
    max_color: QColor = None
    n_total: int = 0
    n_loaded: int = 0
    fmt: str = "{}"

    def __init__(self, parent, data: ty.Union[np.ndarray, pd.DataFrame]):
        super().__init__(parent)
        self.set_data(data)

    def set_data(self, data: ty.Union[np.ndarray, pd.DataFrame]):
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

    def set_formatting(self, fmt: str):
        """Text formatter."""
        self.fmt = fmt

    def set_colormap(self, colormap: str, min_val: float = None, max_val: float = None):
        """Set colormap."""
        import matplotlib.cm
        import matplotlib.colors

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

    def reset(self):
        """Reset model."""
        self.beginResetModel()
        self.endResetModel()

    def reset_data(self):
        """Reset data."""
        self.df = self.df.iloc[0:0]
        self.base_df = self.base_df.iloc[0:0]
        self.reset()

    def data(self, index, role=None):
        """Parse data."""
        if not index.isValid():
            return None
        # background color
        if role == Qt.BackgroundRole:
            if self.colors:
                color = self.colors.get(
                    find_nearest_index_batch(
                        self.color_list, self.normalizer(self.df.iloc[index.row(), index.column()])
                    ),
                    self.max_color,
                )
                return QBrush(color)
            return QBrush()
        # text color
        elif role == Qt.ForegroundRole:
            if self.colors:
                color = self.colors.get(
                    find_nearest_index_batch(
                        self.color_list, self.normalizer(self.df.iloc[index.row(), index.column()])
                    ),
                    self.max_color,
                )
                return QBrush(get_text_color(color))
            return QBrush(QColor(TEXT_COLOR))
        # display value
        elif role == Qt.DisplayRole:
            value = self.df.iloc[index.row(), index.column()]
            return self.fmt.format(value)
        # check alignment role
        elif role == Qt.TextAlignmentRole:
            return Qt.AlignCenter

    def headerData(self, index, orientation, role=None):
        """Get header data."""
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return str(self.df.columns[index])
        if orientation == Qt.Vertical and role == Qt.DisplayRole:
            return str(self.df.index[index])
        return None

    def rowCount(self, parent=None, **kwargs):
        """Return number of rows."""
        return self.df.shape[0] if self.df is not None else 0

    def columnCount(self, parent=None, **kwargs):
        """Return number of columns."""
        return self.df.shape[1] if self.df is not None else 0

    def canFetchMore(self, parent=None) -> bool:
        """Check whether can fetch more data."""
        return self.n_total >= self.n_loaded

    def fetchMore(self, index=QModelIndex()):
        """Fetch more data."""
        reminder = self.n_total - self.n_loaded
        items_to_fetch = min(reminder, BATCH_SIZE)
        self.beginInsertRows(QModelIndex(), self.n_loaded, self.n_loaded + items_to_fetch - 1)
        self.n_loaded += items_to_fetch
        self.df = self.base_df.iloc[: self.n_loaded, :]
        self.endInsertRows()


class QtArrayTableView(QTableView):
    """Array table."""

    evt_key_release = Signal(QKeyEvent)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def keyReleaseEvent(self, event):
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
        colormap: str = None,
        min_val: float = None,
        max_val: float = None,
    ) -> None:
        """Set data."""
        model = QtArrayTableModel(self, data)
        model.set_colormap(colormap, min_val, max_val)
        if fmt:
            model.set_formatting(fmt)
        self.setModel(model)
        self.init()

    def set_formatting(self, fmt: str):
        """Text formatter."""
        # let's perform simple test to make sure value can be rendered
        fmt.format(42.0)

        # set value on model
        model = self.model()
        if model:
            model.set_formatting(fmt)
            model.reset()

    def set_colormap(self, colormap: str, min_val: float = None, max_val: float = None):
        """Set colormap."""
        model = self.model()
        if model:
            model.set_colormap(colormap, min_val, max_val)
            model.reset()

    def init(self) -> None:
        """Initialize table to ensure correct visuals."""
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setDragEnabled(True)
        # self.setHorizontalHeader(QtRotatedHeaderView(self))

    def reset_data(self):
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
