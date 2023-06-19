"""Checkable combobox."""
import typing as ty

from qtpy import QtCore, QtWidgets


class QtCheckableComboBox(QtWidgets.QComboBox):
    """Checkable combobox."""

    def addItem(self, item):
        """Add item."""
        super().addItem(item)
        item = self.model().item(self.count() - 1, 0)
        item.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
        item.setCheckState(QtCore.Qt.Unchecked)

    def addItems(self, texts: ty.Sequence[str]) -> None:
        """Add items."""
        current = self.count()
        super().addItems(texts)
        for index in range(current, self.count()):
            item = self.model().item(index, 0)
            item.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
            item.setCheckState(QtCore.Qt.Unchecked)

    def itemChecked(self, index):
        """Item is checked."""
        item = self.model().item(index, 0)
        return item.checkState() == QtCore.Qt.Checked


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
