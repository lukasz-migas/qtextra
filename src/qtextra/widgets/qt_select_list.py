"""Selection list."""

from __future__ import annotations

from natsort import index_natsorted, order_by_index
from qtpy.QtCore import QSize, Qt
from qtpy.QtGui import QAbstractTextDocumentLayout, QPalette, QTextDocument
from qtpy.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QFormLayout,
    QListWidget,
    QListWidgetItem,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QWidget,
)

import qtextra.helpers as hp
from qtextra.widgets.qt_mini_toolbar import QtMiniToolbar


class HTMLDelegate(QStyledItemDelegate):
    """Rich text delegate."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.doc = QTextDocument(self)

    def paint(self, painter, option, index):
        painter.save()
        options = QStyleOptionViewItem(option)
        self.initStyleOption(options, index)
        self.doc.setHtml(options.text)
        options.text = ""
        style = QApplication.style() if options.widget is None else options.widget.style()
        style.drawControl(QStyle.CE_ItemViewItem, options, painter)

        ctx = QAbstractTextDocumentLayout.PaintContext()
        if option.state & QStyle.State_Selected:
            ctx.palette.setColor(QPalette.Text, option.palette.color(QPalette.Active, QPalette.HighlightedText))
        else:
            ctx.palette.setColor(QPalette.Text, option.palette.color(QPalette.Active, QPalette.Text))
        textRect = style.subElementRect(QStyle.SE_ItemViewItemText, options, None)
        if index.column() != 0:
            textRect.adjust(5, 0, 0, 0)
        constant = 4
        margin = (option.rect.height() - options.fontMetrics.height()) // 2
        margin = margin - constant
        textRect.setTop(textRect.top() + margin)

        painter.translate(textRect.topLeft())
        painter.setClipRect(textRect.translated(-textRect.topLeft()))
        self.doc.documentLayout().draw(painter, ctx)
        painter.restore()

    def sizeHint(self, option, index):
        """Size hint."""
        return QSize(self.doc.idealWidth(), self.doc.size().height())


class QtSelectionList(QWidget):
    """Widget which allows to select items from a list.

    It also provides an easy to use interface to add items to the list, select all, deselect all and invert selection.
    """

    _layout: QFormLayout
    list_widget: QListWidget
    toolbar: QtMiniToolbar

    def __init__(self, parent: QWidget | None = None, allow_buttons: bool = True, allow_sort: bool = True):
        super().__init__(parent)
        self.allow_buttons = allow_buttons
        self.allow_sort = allow_sort
        self.init_ui()

    def init_ui(self) -> None:
        """Initialize the user interface."""
        self._layout = hp.make_form_layout(self)

        self.toolbar = QtMiniToolbar(self, add_spacer=False)
        self.toolbar.add_widget(hp.make_btn(self, "Select all", func=self.on_select_all))
        self.toolbar.add_widget(hp.make_btn(self, "Deselect all", func=self.on_deselect_all))
        self.toolbar.add_widget(hp.make_btn(self, "Invert selection", func=self.on_invert_selection))
        self.toolbar.append_spacer()
        self._layout.addRow(self.toolbar)
        if not self.allow_buttons:
            self.toolbar.hide()

        self.list_widget = QListWidget(self)
        # self.list_widget.setItemDelegate(HTMLDelegate(self))
        self.list_widget.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.list_widget.itemClicked.connect(
            lambda item: item.setCheckState(
                Qt.CheckState.Checked if item.checkState() == Qt.CheckState.Unchecked else Qt.CheckState.Unchecked
            )
        )
        # self.list_widget.setAlternatingRowColors(True)
        self._layout.addRow(self.list_widget)

    def add_item(self, item_text: str) -> None:
        """Add an item to the list in alphabetical order."""
        items = [self.list_widget.item(i).text() for i in range(self.list_widget.count())]
        items.append(item_text)
        checked = [
            self.list_widget.item(i).checkState() == Qt.CheckState.Checked for i in range(self.list_widget.count())
        ]
        checked.append(False)
        if self.allow_sort:
            index = index_natsorted(items)
            items, checked = order_by_index(items, index), order_by_index(checked, index)  # type: ignore[assignment]

        self.list_widget.clear()
        for text, checked in zip(items, checked):
            item = QListWidgetItem(text)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked if not checked else Qt.CheckState.Checked)
            self.list_widget.addItem(item)

    def add_items(self, items: list[str]) -> None:
        """Add multiple items to the list."""
        for item in items:
            self.add_item(item)

    def remove_item(self, item_text: str) -> None:
        """Remove an item from the list."""
        for i in range(self.list_widget.count()):
            if self.list_widget.item(i).text() == item_text:
                self.list_widget.takeItem(i)
                break

    def on_select_all(self) -> None:
        """Select all items in the list."""
        for i in range(self.list_widget.count()):
            self.list_widget.item(i).setCheckState(Qt.CheckState.Checked)

    def on_deselect_all(self) -> None:
        """Deselect all items in the list."""
        for i in range(self.list_widget.count()):
            self.list_widget.item(i).setCheckState(Qt.CheckState.Unchecked)

    def on_invert_selection(self) -> None:
        """Invert the selection of all items."""
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            item.setCheckState(
                Qt.CheckState.Checked if item.checkState() == Qt.CheckState.Unchecked else Qt.CheckState.Unchecked
            )

    def get_checked(self) -> list[str]:
        """Get checked items."""
        return [
            self.list_widget.item(i).text()
            for i in range(self.list_widget.count())
            if self.list_widget.item(i).checkState() == Qt.CheckState.Checked
        ]


if __name__ == "__main__":
    import sys

    from qtextra.utils.dev import qmain

    app, frame, ha = qmain(False)
    frame.setMinimumSize(600, 600)

    wdg = QtSelectionList(frame)
    wdg.add_item("Item 1")
    wdg.add_item("Item 2")
    wdg.add_item("Item 3")
    ha.addWidget(wdg)

    frame.show()
    sys.exit(app.exec_())
