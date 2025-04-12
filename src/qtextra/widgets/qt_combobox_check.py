"""Checkable combobox."""

import typing as ty
from functools import partial

from qtpy.QtCore import QModelIndex, Qt, Signal
from qtpy.QtGui import QStandardItemModel
from qtpy.QtWidgets import QComboBox

from qtextra.helpers import call_later, qt_signals_blocked


class CheckableAbstractModel(QStandardItemModel):
    """Abstract model."""

    evt_checked = Signal(int, bool)

    def setData(self, index: QModelIndex, value: ty.Any, role: int = ...) -> bool:
        """Set data."""
        if role == Qt.ItemDataRole.CheckStateRole:
            # self.evt_checked.emit(index.row(), not value)
            call_later(self, partial(self.evt_checked.emit, index.row(), not value), delay=50)
        elif role == Qt.ItemDataRole.DisplayRole:
            pass
        return super().setData(index, value, role)


class QtCheckableComboBox(QComboBox):
    """Checkable combobox."""

    def __init__(self, *args: ty.Any, **kwargs: ty.Any):
        super().__init__(*args, **kwargs)
        self.setModel(CheckableAbstractModel(self))
        self.evt_checked = self.model().evt_checked

    def addItem(self, item: str, data: ty.Any = None):
        """Add item."""
        super().addItem(item, data)
        item = self.model().item(self.count() - 1, 0)
        item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
        item.setCheckState(Qt.CheckState.Unchecked)

    def addItems(self, texts: ty.Sequence[str]) -> None:
        """Add items."""
        current = self.count()
        super().addItems(texts)
        for index in range(current, self.count()):
            item = self.model().item(index, 0)
            item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            item.setCheckState(Qt.CheckState.Unchecked)

    def itemChecked(self, index):
        """Item is checked."""
        item = self.model().item(index, 0)
        return item.checkState() == Qt.CheckState.Checked

    def setItemChecked(self, index: int, checked: bool) -> bool:
        """Set item checked."""
        item = self.model().item(index, 0)
        item.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)

    def get_checked(self) -> ty.List[int]:
        """Get all checked items."""
        return [index for index in range(self.count()) if self.itemChecked(index)]

    def checked_texts(self) -> ty.List[str]:
        """Get text for all checked items."""
        return [self.itemText(index) for index in self.get_checked()]

    def checked_data(self):
        """Get data for all checked items."""
        return [self.itemData(index) for index in self.get_checked()]

    def set_checked_texts(self, texts: ty.List[str]):
        """Set checked texts."""
        with qt_signals_blocked(self):
            [self.setItemChecked(index, False) for index in range(self.count())]
            for text in texts:
                index = self.findText(text)
                if index != -1:
                    self.setItemChecked(index, True)

    # Alias methods to offer Qt-like interface
    checkedData = checked_data
    checkedTexts = checked_texts
    getChecked = get_checked
    setCheckedTexts = set_checked_texts


if __name__ == "__main__":  # pragma: no cover
    import sys

    from qtextra.utils.dev import qframe

    app, frame, ha = qframe(False)
    frame.setLayout(ha)
    frame.setMinimumSize(400, 400)

    wdg = QtCheckableComboBox()
    wdg.addItems(["Option 1", "Option 2", "Option 3"])
    ha.addWidget(wdg)

    frame.show()
    sys.exit(app.exec_())
