"""Combobox with color swatches."""

from __future__ import annotations

from qtpy.QtCore import QRectF, Qt, Signal
from qtpy.QtGui import QColor, QPainter, QPen
from qtpy.QtWidgets import QAbstractButton, QGridLayout, QHBoxLayout, QVBoxLayout, QWidget

from qtextra.config import QtStyler
from qtextra.widgets._qt_combobox import _BTN_H, _base_font, _BaseButton, _draw_chevron, _PopupPanel


class ColorSwatchComboBox(QWidget):
    """Combobox showing a grid of color swatches with optional names."""

    evt_color_changed = Signal(QColor)

    def __init__(self, placeholder: str = "Choose color...", parent=None):
        super().__init__(parent)
        self._color = None
        self._name = ""
        self._placeholder = placeholder
        self._panel = _SwatchPanel(parent=self)
        self._panel.evt_color_selected.connect(self._on_select)
        self._panel.evt_hidden.connect(lambda: self._btn.set_open(False))
        self._build()

    def _build(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._btn = _SwatchComboBtn(self._placeholder)
        self._btn.clicked.connect(self._toggle)
        layout.addWidget(self._btn)

    def add_swatch(self, color: QColor | str, name: str = ""):
        self._panel.add_swatch(QColor(color), name)

    def add_swatches(self, swatches: list[tuple[str, str]]):
        """Swatches = list of (hex, name) tuples."""
        for hex_c, name in swatches:
            self.add_swatch(hex_c, name)

    def _toggle(self):
        if self._panel.isVisible():
            self._panel.hide()
            self._btn.set_open(False)
        else:
            self._panel.show_below(self._btn, min_width=240)
            self._btn.set_open(True)

    def _on_select(self, color: QColor, name: str):
        self._color = color
        self._name = name
        self._btn.set_color(color, name)
        self._btn.set_open(False)
        self.evt_color_changed.emit(color)

    def current_color(self) -> QColor | None:
        return self._color


class _SwatchPanel(_PopupPanel):
    evt_color_selected = Signal(QColor, str)

    CELL = 28
    MIN_GAP = 2
    PADDING = 20  # total horizontal padding inside the popup

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cols = 8  # initial fallback, recalculated in show_below
        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 10, 10, 10)
        outer.setSpacing(6)

        self._grid_w = QWidget()
        self._grid = QGridLayout(self._grid_w)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setSpacing(self.MIN_GAP)
        self._cells: list[_SwatchCell] = []
        outer.addWidget(self._grid_w)

    def add_swatch(self, color: QColor, name: str):
        idx = len(self._cells)
        cell = _SwatchCell(color, name, size=self.CELL)
        cell.clicked.connect(lambda _, c=color, n=name: self._pick(c, n))
        self._grid.addWidget(cell, idx // self._cols, idx % self._cols)
        self._cells.append(cell)
        self.adjustSize()

    def _rebuild_grid(self, cols: int):
        """Redistribute all cells with a new column count."""
        if cols == self._cols:
            return
        self._cols = cols
        for i, cell in enumerate(self._cells):
            self._grid.removeWidget(cell)
            self._grid.addWidget(cell, i // cols, i % cols)
        self.adjustSize()

    def show_below(self, widget, min_width=0):
        """Recalculate columns from available width before showing."""
        avail = max(widget.width(), min_width) - self.PADDING
        cols = max(1, avail // (self.CELL + self.MIN_GAP))
        self._rebuild_grid(cols)
        super().show_below(widget, min_width)
        self.adjustSize()

    def _pick(self, color: QColor, name: str):
        for c in self._cells:
            c.set_selected(c._color == color)
        self.hide()
        self.evt_color_selected.emit(color, name)


class _SwatchCell(QAbstractButton):
    def __init__(self, color: QColor, name: str, size: int = 28, parent=None):
        super().__init__(parent)
        self._color = color
        self._name = name
        self._hovered = False
        self._selected = False
        self.setFixedSize(size, size)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(name or color.name().upper())
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)

    def set_selected(self, v: bool):
        self._selected = v
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        s = self.width()
        rect = QRectF(1, 1, s - 2, s - 2)
        if self._selected:
            p.setPen(QPen(QtStyler.highlight(), 5))
        elif self._hovered:
            p.setPen(QPen(QColor(0, 0, 0, 80), 1.5))
        else:
            p.setPen(QPen(QColor(0, 0, 0, 30), 0.8))
        p.setBrush(self._color)
        p.drawRoundedRect(rect, 5, 5)
        if self._selected:
            # white checkmark
            p.setPen(
                QPen(
                    Qt.GlobalColor.white,
                    2,
                    Qt.PenStyle.SolidLine,
                    Qt.PenCapStyle.RoundCap,
                    Qt.PenJoinStyle.RoundJoin,
                ),
            )
            cx, cy = s / 2, s / 2
            p.drawLine(int(cx - 4), int(cy), int(cx - 1), int(cy + 3))
            p.drawLine(int(cx - 1), int(cy + 3), int(cx + 4), int(cy - 3))
        p.end()

    def enterEvent(self, e):
        self._hovered = True
        self.update()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._hovered = False
        self.update()
        super().leaveEvent(e)


class _SwatchComboBtn(_BaseButton):
    def __init__(self, placeholder, parent=None):
        super().__init__(parent=parent)
        self._color = None
        self._name = ""
        self._placeholder = placeholder

    def set_color(self, color: QColor, name: str):
        self._color = color
        self._name = name
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._draw_frame(p)
        x = 10
        if self._color:
            sw = 18
            sy = (_BTN_H - sw) / 2
            p.setPen(QPen(QColor(0, 0, 0, 40), 0.8))
            p.setBrush(self._color)
            p.drawRoundedRect(QRectF(x, sy, sw, sw), 4, 4)
            x += sw + 8
        label = self._name or (self._color.name().upper() if self._color else self._placeholder)
        p.setFont(_base_font())
        p.setPen(QtStyler.text() if self._color else QtStyler.text_muted())
        p.drawText(
            QRectF(x, 0, self.width() - x - 20, _BTN_H),
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            label,
        )
        _draw_chevron(p, self.width() - 14, _BTN_H / 2, close=not self._open)
        p.end()


if __name__ == "__main__":  # pragma: no cover
    import sys

    from qtextra.utils.dev import qframe

    app, frame, ha = qframe(False)
    combo = ColorSwatchComboBox(placeholder="Pick a color…")
    combo.add_swatches(
        [
            ("#FFFFFF", "White"),
            ("#F8F9FA", "Snow"),
            ("#E9ECEF", "Light Gray"),
            ("#CED4DA", "Gray"),
            ("#6C757D", "Slate"),
            ("#343A40", "Dark"),
            ("#000000", "Black"),
            ("#FFE8E8", "Rose"),
            ("#FF6B6B", "Coral"),
            ("#FF0000", "Red"),
            ("#C0392B", "Crimson"),
            ("#FFF3CD", "Cream"),
            ("#FFC107", "Amber"),
            ("#FF8C00", "Orange"),
            ("#E8F5E9", "Mint"),
            ("#00C853", "Green"),
            ("#006400", "Forest"),
            ("#E3F2FD", "Sky"),
            ("#4472C4", "Blue"),
            ("#1A237E", "Navy"),
            ("#9C27B0", "Purple"),
            ("#E91E63", "Pink"),
            ("#795548", "Brown"),
            ("#FF5722", "Deep Org"),
        ],
    )
    combo.evt_color_changed.connect(lambda c: print(f"Color: {c.name()}"))
    ha.addWidget(combo)
    frame.show()
    sys.exit(app.exec_())
