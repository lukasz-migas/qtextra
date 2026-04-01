"""Shared table models for 2D tabular widgets."""

from __future__ import annotations

import typing as ty

import numpy as np
import pandas as pd
from qtpy.QtCore import QAbstractTableModel, QModelIndex, Qt


class BaseTabularTableModel(QAbstractTableModel):
    """Shared base model for 2D tabular data."""

    fmt: str = "{}"

    def __init__(self, parent=None, *, editable: bool = False):
        super().__init__(parent)
        self._editable = editable
        self._row_count = 0
        self._column_count = 0

    def set_shape(self, row_count: int, column_count: int) -> None:
        """Update the exposed model shape."""
        self._row_count = row_count
        self._column_count = column_count

    def set_formatting(self, fmt: str) -> None:
        """Text formatter."""
        self.fmt = fmt

    def reset_model(self) -> None:
        """Reset model."""
        self.beginResetModel()
        self.endResetModel()

    def rowCount(self, parent=None, **kwargs: ty.Any) -> int:
        """Return number of rows."""
        return self._row_count

    def columnCount(self, parent=None, **kwargs: ty.Any) -> int:
        """Return number of columns."""
        return self._column_count

    def headerData(self, section, orientation, role=None):
        """Return header data. Subclasses can override."""
        return

    def _value_at(self, row: int, column: int) -> ty.Any:
        """Return raw value at index."""
        raise NotImplementedError

    def _set_value_at(self, row: int, column: int, value: ty.Any) -> None:
        """Set value at index."""
        raise NotImplementedError

    def _is_null(self, value: ty.Any) -> bool:
        """Check whether value should render as empty."""
        return pd.isnull(value)

    def _display_value(self, value: ty.Any) -> str:
        """Return string representation for display/edit roles."""
        if self._is_null(value):
            return ""
        return str(value)

    def _tooltip_value(self, value: ty.Any) -> str:
        """Return string representation for tooltip role."""
        if self._is_null(value):
            return "NaN"
        return str(value)

    def data(self, index: QModelIndex, role=Qt.ItemDataRole.DisplayRole):
        """Return data for supported roles."""
        if not index.isValid():
            return None

        if role not in (
            Qt.ItemDataRole.DisplayRole,
            Qt.ItemDataRole.EditRole,
            Qt.ItemDataRole.ToolTipRole,
        ):
            return None

        value = self._value_at(index.row(), index.column())

        if role == Qt.ItemDataRole.ToolTipRole:
            return self._tooltip_value(value)
        return self._display_value(value)

    def flags(self, index):
        """Set the item flags at the given index."""
        flags = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        if self._editable:
            flags |= Qt.ItemFlag.ItemIsEditable
        return flags

    def setData(self, index, value, role=None):
        """Set the data at the given index."""
        if self._editable and role == Qt.ItemDataRole.EditRole:
            self._set_value_at(index.row(), index.column(), value)
            self.dataChanged.emit(index, index)
            return True
        return None


def is_float_like(value: ty.Any) -> bool:
    """Fast helper for numpy/pandas float scalars."""
    return isinstance(value, (float, np.floating))
