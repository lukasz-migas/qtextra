"""Selection list."""

from __future__ import annotations

from natsort import index_natsorted, order_by_index
from qtpy.QtCore import QSize, Qt, Signal
from qtpy.QtGui import QAbstractTextDocumentLayout, QPalette, QTextDocument
from qtpy.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QFormLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QWidget,
)

import qtextra.helpers as hp
from qtextra.widgets.qt_dialog import QtFramelessPopup
from qtextra.widgets.qt_toolbar_mini import QtMiniToolbar


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

    evt_selection_changed = Signal()

    _layout: QFormLayout
    list_widget: QListWidget
    toolbar: QtMiniToolbar
    filter_by: QLineEdit

    def __init__(
        self,
        parent: QWidget | None = None,
        allow_toolbar: bool = True,
        allow_sort: bool = True,
        allow_filter: bool = True,
        allow_visible_toggle: bool = True,
        enable_single_click: bool = False,
        double_click_to_select: bool = True,
        text: str = "",
    ):
        super().__init__(parent)
        self.text: str = text
        self.allow_toolbar = allow_toolbar
        self.allow_sort = allow_sort
        self.allow_filter = allow_filter
        self.allow_visible_toggle = allow_visible_toggle

        # actions
        self.enable_single_click = enable_single_click
        self.double_click_to_select = double_click_to_select
        self.init_ui()

    # noinspection PyAttributeOutsideInit
    def init_ui(self) -> None:
        """Initialize the user interface."""
        self._layout = hp.make_form_layout(parent=self)
        self.filter_by = hp.make_line_edit(
            self, placeholder="Type in text to filter...", func_changed=self.on_filter, func_clear=self.on_filter
        )
        self.filter_by.setMinimumWidth(200)
        hp.set_expanding_sizer_policy(self.filter_by, horz=True)
        if not self.allow_filter:
            self.filter_by.hide()

        self.info_label = hp.make_label(self, "")

        self.toolbar = QtMiniToolbar(self, add_spacer=False, spacing=2, icon_size="average")
        self.toolbar.add_qta_tool("toggle_on", func=self.on_select_all, average=True, tooltip="Select all items")
        self.toolbar.add_qta_tool("toggle_off", func=self.on_deselect_all, average=True, tooltip="Deselect all items")
        self.toolbar.add_qta_tool(
            "invert_selection",
            func=self.on_invert_selection,
            average=True,
            tooltip="Invert selection",
            hide=not self.allow_visible_toggle,
        )
        self.toolbar.add_qta_tool("visible", func=self.on_show_all, average=True, tooltip="Show all items")
        self.toolbar.add_qta_tool(
            "visible_off",
            func=self.on_hide_deselected,
            average=True,
            tooltip="Hide deselected items",
            hide=not self.allow_visible_toggle,
        )
        self.toolbar.add_widget(self.filter_by, stretch=True)
        self.toolbar.add_widget(self.info_label)
        self.toolbar.max_size = self.filter_by.minimumHeight() + 2

        if not self.allow_filter:
            self.toolbar.add_spacer()
        if not self.allow_toolbar:
            self.toolbar.hide()
        self._layout.addRow(self.toolbar)

        self.list_widget = QListWidget(self)
        self.list_widget.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.list_widget.setWordWrap(True)
        self.list_widget.itemChanged.connect(self.on_selection_changed)
        if self.double_click_to_select:
            self.list_widget.itemDoubleClicked.connect(
                lambda item: item.setCheckState(
                    Qt.CheckState.Checked if item.checkState() == Qt.CheckState.Unchecked else Qt.CheckState.Unchecked
                )
            )
        if self.enable_single_click:
            self.list_widget.itemClicked.connect(
                lambda item: item.setCheckState(
                    Qt.CheckState.Checked if item.checkState() == Qt.CheckState.Unchecked else Qt.CheckState.Unchecked
                )
            )
        # self.list_widget.setAlternatingRowColors(True)
        self._layout.addRow(self.list_widget)

    def on_click(self, index: int) -> None:
        """Select an item by index."""
        item = self.list_widget.item(index)
        if item:
            self.list_widget.setCurrentItem(item)

    def on_selection_changed(self) -> None:
        """Update selection changed information."""
        self.evt_selection_changed.emit()
        if self.allow_toolbar:
            selected = self.get_checked()
            count = self.list_widget.count()
            self.info_label.setText(f"{len(selected)}/{count}")

    def add_item(self, item_text: str, check: bool = False) -> None:
        """Add an item to the list in alphabetical order."""
        items = [self.list_widget.item(i).text() for i in range(self.list_widget.count())]
        items.append(item_text)
        checked = [
            self.list_widget.item(i).checkState() == Qt.CheckState.Checked for i in range(self.list_widget.count())
        ]
        checked.append(check)
        if self.allow_sort:
            index = index_natsorted(items)
            items, checked = order_by_index(items, index), order_by_index(checked, index)  # type: ignore[assignment]

        self.list_widget.clear()
        for text, checked in zip(items, checked):
            item = QListWidgetItem(text)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked if not checked else Qt.CheckState.Checked)
            self.list_widget.addItem(item)
        self.on_selection_changed()

    def add_items(self, items: list[str], *, check: bool = False, clear: bool = False) -> None:
        """Add multiple items to the list."""
        if clear:
            self.list_widget.clear()
        for item in items:
            self.add_item(item, check=check)

    def remove_item(self, item_text: str) -> None:
        """Remove an item from the list."""
        for i in range(self.list_widget.count()):
            if self.list_widget.item(i).text() == item_text:
                self.list_widget.takeItem(i)
                break

    def on_filter(self) -> None:
        """Filter the list of items in the table."""
        text = self.filter_by.text().lower()
        for index in range(self.list_widget.count()):
            item = self.list_widget.item(index)
            item.setHidden(text not in item.text().lower())

    def on_hide_deselected(self) -> None:
        """Hide deselected items."""
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.checkState() == Qt.CheckState.Unchecked:
                item.setHidden(True)

    def on_show_all(self) -> None:
        """Show all items."""
        self.filter_by.setText("")
        for i in range(self.list_widget.count()):
            self.list_widget.item(i).setHidden(False)

    def on_select_all(self) -> None:
        """Select all items in the list."""
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.isHidden():
                continue
            item.setCheckState(Qt.CheckState.Checked)

    def on_deselect_all(self) -> None:
        """Deselect all items in the list."""
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.isHidden():
                continue
            item.setCheckState(Qt.CheckState.Unchecked)

    def on_invert_selection(self) -> None:
        """Invert the selection of all items."""
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.isHidden():
                continue
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

    def get_unchecked(self) -> list[str]:
        """Get unchecked items."""
        return [
            self.list_widget.item(i).text()
            for i in range(self.list_widget.count())
            if self.list_widget.item(i).checkState() == Qt.CheckState.Unchecked
        ]

    def set_checked(self, checked: list[str]) -> None:
        """Set checked items."""
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            current_state = item.checkState()
            item.setCheckState(Qt.CheckState.Checked if item.text() in checked else current_state)


class QtListSelectPopup(QtFramelessPopup):
    """Popup window."""

    def __init__(
        self,
        parent: QWidget | None = None,
        allow_toolbar: bool = False,
        allow_sort: bool = False,
        allow_filter: bool = False,
        allow_visible_toggle: bool = False,
        enable_single_click: bool = False,
        double_click_to_select: bool = True,
        text: str = "",
    ) -> None:
        self.text: str = text
        self.allow_toolbar = allow_toolbar
        self.allow_sort = allow_sort
        self.allow_filter = allow_filter
        self.allow_visible_toggle = allow_visible_toggle
        self.enable_single_click = enable_single_click
        self.double_click_to_select = double_click_to_select

        super().__init__(parent)

    # noinspection PyAttributeOutsideInit
    def make_panel(self) -> QFormLayout:
        """Make panel."""
        self.selection_list = QtSelectionList(
            parent=self,
            allow_toolbar=self.allow_toolbar,
            allow_sort=self.allow_sort,
            allow_filter=self.allow_filter,
            allow_visible_toggle=self.allow_visible_toggle,
            enable_single_click=self.enable_single_click,
            double_click_to_select=self.double_click_to_select,
            text=self.text,
        )
        layout = hp.make_form_layout(parent=self)
        layout.addRow(hp.make_label(self, self.text, hide=self.text == ""))
        layout.addRow(hp.make_h_line(self))
        layout.addRow(self.selection_list)
        return layout


if __name__ == "__main__":  # pragma: no cover
    import sys

    from qtextra.utils.dev import qframe

    app, frame, ha = qframe(False)
    frame.setMinimumSize(600, 600)

    wdg = QtSelectionList(frame)
    wdg.add_item("Item 1")
    wdg.add_item("Item 2")
    wdg.add_item("Item 3")
    ha.addWidget(wdg)

    frame.show()
    sys.exit(app.exec_())
