"""Searchable combobox."""

from __future__ import annotations

import typing as ty

from qtpy.QtCore import QRectF, Qt, Signal
from qtpy.QtGui import QPainter, QPen
from qtpy.QtWidgets import QComboBox, QCompleter, QHBoxLayout, QLineEdit, QStyledItemDelegate, QWidget

from qtextra.config import QtStyler
from qtextra.widgets._qt_combobox import _BTN_H, _base_font, _BaseButton, _ItemRow, _ScrollablePanel


class _SearchPanel(_ScrollablePanel):
    itemSelected = Signal(str)

    def __init__(self, items: list[str], parent=None):
        super().__init__(parent)
        self._all_items = items
        self._rows: list[_ItemRow] = []
        self._selected = ""

        # search bar pinned above the scroll area
        self._search = QLineEdit()
        self._search.setPlaceholderText("Search...")
        self._search.textChanged.connect(self._filter)
        self._outer_l.insertWidget(0, self._search)

        self._build_rows(items)

    def set_items(self, items: list[str]):
        self._all_items = items
        self._rebuild_rows(items)

    def set_selected(self, text: str):
        self._selected = text
        for r in self._rows:
            r.set_selected(r._label == text)

    def _build_rows(self, items: list[str]):
        for text in items:
            row = _ItemRow(text, selected=(text == self._selected))
            row.clicked.connect(self._make_row_click_handler(text))
            self._inner_l.addWidget(row)
            self._rows.append(row)
        self._finalize_height()

    def _rebuild_rows(self, items: list[str]):
        for r in self._rows:
            self._inner_l.removeWidget(r)
            r.deleteLater()
        self._rows.clear()
        self._build_rows(items)

    def _filter(self, text: str):
        q = text.lower()
        for row in self._rows:
            row.setVisible(q in row._label.lower())
        self._finalize_height()

    def _pick(self, text: str):
        self._selected = text
        for r in self._rows:
            r.set_selected(r._label == text)
        self.hide()
        self.itemSelected.emit(text)

    def show_below(self, widget, min_width=0):
        """Show widgets."""
        self._search.clear()
        self._filter("")
        super().show_below(widget, min_width)
        self._finalize_height()
        self._search.setFocus()

    # Alias method to offer Qt-like interface
    addItems = set_items

    def _make_row_click_handler(self, text: str) -> ty.Callable[[bool], None]:
        """Create a click handler for a specific item label."""

        def _handle_row_click(_checked: bool = False) -> None:
            self._pick(text)

        return _handle_row_click


class _SearchComboBtn(_BaseButton):
    def __init__(self, placeholder, parent=None):
        super().__init__(parent=parent)
        self._text = ""
        self._placeholder = placeholder

    def set_text(self, t: str):
        """Set text to be displayed."""
        self._text = t
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._draw_frame(p)
        # label
        label = self._text or self._placeholder
        p.setFont(_base_font())
        p.setPen(QtStyler.text() if self._text else QtStyler.text_muted())
        # p.setPen(_TEXT if self._text else _MUTED)
        p.drawText(
            QRectF(12, 0, self.width() - 32, _BTN_H),
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            label,
        )
        # search icon
        ic = self.width() - 22
        p.setPen(QPen(QtStyler.icon(), 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QRectF(ic - 7, _BTN_H / 2 - 5, 8, 8))
        p.drawLine(int(ic - 1), int(_BTN_H / 2 + 3), int(ic + 3), int(_BTN_H / 2 + 7))
        p.end()


class QtSearchComboBox(QWidget):
    """Combobox with a live-filter search field in the dropdown."""

    currentTextChanged = Signal(str)

    def __init__(self, items: list[str] | None = None, placeholder: str = "Select…", parent=None):
        super().__init__(parent)
        self._text = ""
        self._placeholder = placeholder
        self._panel = _SearchPanel(items or [], parent=self)
        self._panel.itemSelected.connect(self._on_select)
        self._panel.evt_hidden.connect(self._close_panel)
        self._build()

    def _build(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._btn = _SearchComboBtn(self._placeholder)
        self._btn.clicked.connect(self._toggle)
        layout.addWidget(self._btn)

    def _toggle(self):
        if self._panel.isVisible():
            self._panel.hide()
            self._close_panel()
        else:
            self._panel.show_below(self._btn)
            self._btn.set_open(True)

    def _on_select(self, text: str):
        self._text = text
        self._btn.set_text(text)
        self._close_panel()
        self.currentTextChanged.emit(text)

    def set_items(self, items: list[str]):
        """Set items to be displayed."""
        self._panel.set_items(items)

    def current_text(self) -> str:
        """Return current text displayed."""
        return self._text

    def set_current_text(self, t: str):
        """Set current text to be displayed."""
        self._on_select(t)

    # Alias methods to offer Qt-like interface
    addItems = set_items

    def _close_panel(self) -> None:
        """Reset the button state when the popup closes."""
        self._btn.set_open(False)


class QtSearchableComboBox(QComboBox):
    """Searchable combobox."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setEditable(True)
        self.completer_object = QCompleter(parent=self)
        self.completer_object.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.completer_object.setModelSorting(QCompleter.ModelSorting.CaseSensitivelySortedModel)
        self.completer_object.setFilterMode(Qt.MatchFlag.MatchContains)
        self.completer_object.activated.connect(self.on_activated)
        self.setCompleter(self.completer_object)
        self.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)  # ensures that incorrect values are not added
        self.completer_object.popup().setItemDelegate(QStyledItemDelegate(self))
        self.completer_object.popup().setObjectName("search_box_popup")

    def _text_activated(self):  # pragma: no cover
        self.textActivated.emit(self.currentText())

    def on_activated(self, value: str) -> None:
        """On activated."""
        self.currentIndexChanged.emit(self.currentIndex())
        self.currentTextChanged.emit(self.currentText())

    def addItem(self, *args) -> None:
        """Add item."""
        super().addItem(*args)
        self.completer_object.setModel(self.model())

    def addItems(self, items: ty.Sequence[str]) -> None:
        """Add items."""
        super().addItems(items)
        self.completer_object.setModel(self.model())

    def removeItem(self, index: int) -> None:
        """Remove item."""
        super().removeItem(index)
        self.completer_object.setModel(self.model())

    # Alias methods to offer Qt-like interface
    _textActivated = _text_activated
    onActivated = on_activated


def add_search_to_combobox(combobox: QComboBox) -> None:
    """Add search to combobox."""
    combobox.setEditable(True)
    completer_object = QCompleter()
    completer_object.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
    completer_object.setModelSorting(QCompleter.ModelSorting.CaseSensitivelySortedModel)
    completer_object.setFilterMode(Qt.MatchFlag.MatchContains)
    combobox.setCompleter(completer_object)
    combobox.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)  # ensures that incorrect values are not added
    completer_object.popup().setItemDelegate(QStyledItemDelegate(combobox))
    completer_object.popup().setObjectName("search_box_popup")
    combobox.completer_object = completer_object
    combobox._text_activated = _make_text_activated_handler(combobox)


def _make_text_activated_handler(combobox: QComboBox) -> ty.Callable[[], None]:
    """Return a handler that emits the combobox current text."""

    def _emit_current_text() -> None:
        combobox.textActivated.emit(combobox.currentText())

    return _emit_current_text


if __name__ == "__main__":  # pragma: no cover
    import sys

    from qtextra.utils.dev import qframe

    app, frame, ha = qframe(False)
    combo = QtSearchableComboBox()
    combo.addItems(
        [
            "Short text",
            "This is a very long text that likely needs truncation",
            "Another extremely long text example to demonstrate ellipses…",
        ],
    )
    ha.addWidget(combo)

    combo = QtSearchComboBox()
    combo.addItems(
        [
            "Apple",
            "Apricot",
            "Banana",
            "Blueberry",
            "Cherry",
            "Cranberry",
            "Grape",
            "Guava",
            "Kiwi",
            "Lemon",
            "Lime",
            "Mango",
            "Orange",
            "Papaya",
            "Peach",
            "Pear",
            "Pineapple",
            "Plum",
            "Strawberry",
            "Watermelon",
        ],
    )
    ha.addWidget(combo)
    frame.show()
    sys.exit(app.exec_())
