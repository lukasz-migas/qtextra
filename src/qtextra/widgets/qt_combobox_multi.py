"""Multi-selection widget."""

from __future__ import annotations

import typing as ty

from qtpy.QtCore import QRectF, Qt, Signal
from qtpy.QtGui import QFontMetrics, QPainter
from qtpy.QtWidgets import QHBoxLayout, QLineEdit, QWidget

from qtextra.config import QtStyler
from qtextra.widgets._qt_combobox import _BTN_H, _base_font, _BaseButton, _draw_chevron, _MultiItemRow, _ScrollablePanel


class _MultiPanel(_ScrollablePanel):
    evt_selection_changed = Signal(list)

    def __init__(self, items: list[str], parent=None):
        super().__init__(parent)
        self._selected: set[str] = set()
        self._rows: list[_MultiItemRow] = []

        self._search = QLineEdit()
        self._search.setPlaceholderText("Search...")
        self._search.textChanged.connect(self._filter)
        self._outer_l.insertWidget(0, self._search)

        for text in items:
            row = _MultiItemRow(text)
            row.toggled_item.connect(self._on_toggle)
            self._inner_l.addWidget(row)
            self._rows.append(row)
        self._finalize_height()

    def _filter(self, text: str):
        """Filter visible rows by search text."""
        q = text.lower()
        for row in self._rows:
            row.setVisible(q in row._label.lower())
        self._finalize_height()

    def show_below(self, widget, min_width=0):
        """Show panel below widget, resetting the search field."""
        self._search.clear()
        self._filter("")
        super().show_below(widget, min_width)
        self._finalize_height()
        self._search.setFocus()

    def _on_toggle(self, text: str, checked: bool):
        if checked:
            self._selected.add(text)
        else:
            self._selected.discard(text)
        self.evt_selection_changed.emit(sorted(self._selected, key=lambda x: [r._label for r in self._rows].index(x)))

    def set_selected(self, items: list[str]):
        self._selected = set(items)
        for r in self._rows:
            r.set_checked(r._label in self._selected)

    def selected(self) -> list[str]:
        order = [r._label for r in self._rows]
        return [x for x in order if x in self._selected]


class _MultiBtn(_BaseButton):
    _CHIP_H = 20
    _CHIP_PAD = 6
    _CHIP_GAP = 4

    def __init__(self, placeholder, parent=None):
        super().__init__(parent=parent)
        self._selected: list[str] = []
        self._placeholder = placeholder
        self.setMinimumHeight(_BTN_H)

    def set_selected(self, items: list[str]):
        self._selected = items
        # adjust height if chips wrap
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._draw_frame(p)

        if not self._selected:
            p.setFont(_base_font())
            p.setPen(QtStyler.text_muted())
            p.drawText(
                QRectF(12, 0, self.width() - 32, _BTN_H),
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                self._placeholder,
            )
        else:
            x = 8
            y = (_BTN_H - self._CHIP_H) / 2
            fm = QFontMetrics(_base_font(size=11))
            for i, item in enumerate(self._selected):
                tw = fm.horizontalAdvance(item)
                cw = tw + self._CHIP_PAD * 2
                if x + cw > self.width() - 28:
                    remaining = len(self._selected) - i
                    # draw +N badge
                    badge = f"+{remaining}"
                    bw = fm.horizontalAdvance(badge) + 10
                    # paint chip
                    p.setPen(Qt.PenStyle.NoPen)
                    p.setBrush(QtStyler.foreground())
                    p.drawRoundedRect(QRectF(x, y, bw, self._CHIP_H), self._CHIP_H / 2, self._CHIP_H / 2)
                    # write text
                    p.setFont(_base_font(size=11))
                    p.setPen(QtStyler.text())
                    p.drawText(QRectF(x, y, bw, self._CHIP_H), Qt.AlignmentFlag.AlignCenter, badge)
                    break

                # paint chip
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QtStyler.foreground())
                p.drawRoundedRect(QRectF(x, y, cw, self._CHIP_H), self._CHIP_H / 2, self._CHIP_H / 2)
                # write text
                p.setFont(_base_font(size=11))
                p.setPen(QtStyler.text())
                p.drawText(QRectF(x, y, cw, self._CHIP_H), Qt.AlignmentFlag.AlignCenter, item)
                x += cw + self._CHIP_GAP
        _draw_chevron(p, self.width() - 14, _BTN_H / 2, close=not self._open)
        p.end()


class MultiSelectComboBox(QWidget):
    """Combobox allowing multiple selections, shown as chips in the button."""

    evt_selection_changed = Signal(list)

    def __init__(self, items: ty.Optional[list[str]] = None, placeholder: str = "Select items…", parent=None):
        super().__init__(parent)
        self._placeholder = placeholder
        self._selected: list[str] = []
        self._panel = _MultiPanel(items or [], parent=self)
        self._panel.evt_selection_changed.connect(self._on_change)
        self._panel.evt_hidden.connect(lambda: self._btn.set_open(False))
        self._build()

    def _build(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._btn = _MultiBtn(self._placeholder)
        self._btn.clicked.connect(self._toggle)
        layout.addWidget(self._btn)

    def _toggle(self):
        if self._panel.isVisible():
            self._panel.hide()
            self._btn.set_open(False)
        else:
            self._panel.show_below(self._btn)
            self._btn.set_open(True)

    def _on_change(self, items: list[str]):
        self._selected = items
        self._btn.set_selected(items)
        self.evt_selection_changed.emit(items)

    def selected(self) -> list[str]:
        return list(self._selected)

    def set_selected(self, items: list[str]):
        self._panel.set_selected(items)
        self._on_change(items)


if __name__ == "__main__":  # pragma: no cover
    import sys

    from qtextra.utils.dev import qframe

    app, frame, ha = qframe(False)
    combo = MultiSelectComboBox(
        items=[
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
        placeholder="Choose fruit…",
    )
    combo.evt_selection_changed.connect(lambda s: print(f"Multi: {s}"))
    ha.addWidget(combo)
    frame.show()
    sys.exit(app.exec_())
