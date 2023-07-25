"""Checkable combobox."""
import typing as ty

from qtpy.QtGui import QStandardItemModel
from qtpy.QtWidgets import QComboBox
from qtpy.QtCore import Qt, Signal, QModelIndex


class CheckableAbstractModel(QStandardItemModel):
    """Abstract model."""
    evt_checked = Signal(int, bool)

    def setData(self, index: QModelIndex, value: ty.Any, role: int = ...) -> bool:
        """Set data."""
        if role == Qt.CheckStateRole:
            self.evt_checked.emit(index.row(), value)
        return super().setData(index, value, role)


class QtCheckableComboBox(QComboBox):
    """Checkable combobox."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setModel(CheckableAbstractModel(self))
        self.evt_checked = self.model().evt_checked

    def addItem(self, item):
        """Add item."""
        super().addItem(item)
        item = self.model().item(self.count() - 1, 0)
        item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
        item.setCheckState(Qt.Unchecked)

    def addItems(self, texts: ty.Sequence[str]) -> None:
        """Add items."""
        current = self.count()
        super().addItems(texts)
        for index in range(current, self.count()):
            item = self.model().item(index, 0)
            item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            item.setCheckState(Qt.Unchecked)

    def itemChecked(self, index):
        """Item is checked."""
        item = self.model().item(index, 0)
        return item.checkState() == Qt.Checked

    def setItemChecked(self, index: int, checked: bool) -> bool:
        """Set item checked."""
        item = self.model().item(index, 0)
        item.setCheckState(Qt.Checked if checked else Qt.Unchecked)

    def get_checked(self) -> ty.List[int]:
        """Get all checked items."""
        return [index for index in range(self.count()) if self.itemChecked(index)]


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
