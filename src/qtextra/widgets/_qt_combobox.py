"""Combobox."""

from qtpy.QtCore import QPoint, QRectF, Qt, Signal
from qtpy.QtGui import QColor, QFont, QPainter, QPen
from qtpy.QtWidgets import QAbstractButton, QFrame, QScrollArea, QSizePolicy, QVBoxLayout, QWidget

from qtextra.config import QtStyler

_BTN_H = 34
_BTN_RADIUS = 8
_ITEM_H = 34
_ITEM_RADIUS = 6
_FONT_SIZE = 13
_HEADER_SIZE = 11


def _base_font(bold=False, size=_FONT_SIZE) -> QFont:
    f = QFont()
    f.setPixelSize(size)
    f.setBold(bold)
    return f


def _draw_chevron(painter: QPainter, cx: float, cy: float, close: bool = True):
    """Draw a ▾ or ▴ chevron."""
    pen = QPen(
        QtStyler.icon(),
        1.6,
        Qt.PenStyle.SolidLine,
        Qt.PenCapStyle.RoundCap,
        Qt.PenJoinStyle.RoundJoin,
    )
    painter.setPen(pen)
    if close:
        painter.drawLine(int(cx - 4), int(cy - 2), int(cx), int(cy + 2))
        painter.drawLine(int(cx), int(cy + 2), int(cx + 4), int(cy - 2))
    else:
        painter.drawLine(int(cx - 4), int(cy + 2), int(cx), int(cy - 2))
        painter.drawLine(int(cx), int(cy - 2), int(cx + 4), int(cy + 2))


class _BaseButton(QAbstractButton):
    """Shared pill-shaped dropdown trigger button."""

    def __init__(self, min_width=180, parent=None):
        super().__init__(parent)
        self._open = False
        self._hovered = False
        self.setFixedHeight(_BTN_H)
        self.setMinimumWidth(min_width)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)

    def set_open(self, v: bool):
        self._open = v
        self.update()

    def _bg(self):
        if self._open:
            return QtStyler.background()
        if self._hovered:
            return QtStyler.highlight()
        return QtStyler.background()

    def _draw_frame(self, p: QPainter):
        rect = QRectF(0.5, 0.5, self.width() - 1, _BTN_H - 1)
        border = QtStyler.highlight() if self._open else QtStyler.foreground()
        p.setPen(QPen(border, 1.5 if self._open else 1))
        p.setBrush(self._bg())
        p.drawRoundedRect(rect, _BTN_RADIUS, _BTN_RADIUS)

    def enterEvent(self, e):
        self._hovered = True
        self.update()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._hovered = False
        self.update()
        super().leaveEvent(e)


class _PopupPanel(QWidget):
    """Floating popup card that closes when clicking outside."""

    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def _card_rect(self):
        return QRectF(2, 2, self.width() - 4, self.height() - 4)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        # shadow
        for i in range(4):
            shadow = QColor(0, 0, 0, 18 - i * 4)
            p.setPen(QPen(shadow, (4 - i) * 0.8))
            p.setBrush(Qt.BrushStyle.NoBrush)
            r = self._card_rect().adjusted(-i, -i, i, i)
            p.drawRoundedRect(r, 10 + i, 10 + i)
        # card
        p.setPen(QPen(QtStyler.background().darker(50), 1))
        p.setBrush(QtStyler.background())
        p.drawRoundedRect(self._card_rect(), 10, 10)
        p.end()

    def show_below(self, widget: QWidget, min_width: int = 0):
        pos = widget.mapToGlobal(QPoint(0, widget.height() + 4))
        self.adjustSize()
        w = max(widget.width(), min_width)
        self.setMinimumWidth(w + 4)
        self.adjustSize()
        self.move(pos.x() - 2, pos.y())
        self.show()
        self.raise_()


class _ScrollablePanel(_PopupPanel):
    """Popup with a scrollable inner area."""

    MAX_VISIBLE_H = 280

    def __init__(self, parent=None):
        super().__init__(parent)
        self._outer_l = QVBoxLayout(self)
        self._outer_l.setContentsMargins(6, 6, 6, 6)
        self._outer_l.setSpacing(4)

        self._scroll = QScrollArea()
        self._scroll.setObjectName("combobox_scroll")
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._inner = QWidget()
        self._inner.setObjectName("combobox_inner")
        self._inner_l = QVBoxLayout(self._inner)
        self._inner_l.setContentsMargins(0, 0, 0, 0)
        self._inner_l.setSpacing(2)
        self._scroll.setWidget(self._inner)
        self._outer_l.addWidget(self._scroll)

    def _finalize_height(self):
        self._inner_l.activate()
        self._inner.adjustSize()
        ih = self._inner.sizeHint().height()
        h = min(ih, self.MAX_VISIBLE_H) + 16
        self._scroll.setFixedHeight(h)
        self.adjustSize()


class _ItemRow(QAbstractButton):
    """A single selectable row inside a popup."""

    def __init__(self, label: str, selected: bool = False, parent=None):
        super().__init__(parent)
        self._label = label
        self._selected = selected
        self._hovered = False
        self.setFixedHeight(_ITEM_H)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)

    def set_selected(self, v: bool):
        self._selected = v
        self.update()

    def set_label(self, v: str):
        self._label = v
        self.update()

    def _draw_content(self, p: QPainter):
        p.setFont(_base_font())
        p.setPen(QtStyler.text())
        p.drawText(
            QRectF(10, 0, self.width() - 36, _ITEM_H),
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            self._label,
        )
        if self._selected:
            self._draw_check(p)

    def _draw_check(self, p: QPainter):
        cx = self.width() - 16
        cy = _ITEM_H / 2
        color = QtStyler.icon()
        p.setPen(QPen(color, 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        p.drawLine(int(cx - 5), int(cy), int(cx - 2), int(cy + 3))
        p.drawLine(int(cx - 2), int(cy + 3), int(cx + 4), int(cy - 4))

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(2, 2, self.width() - 4, _ITEM_H - 4)
        if self._selected:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QtStyler.highlight().darker(50))
            p.drawRoundedRect(rect, _ITEM_RADIUS, _ITEM_RADIUS)
        elif self._hovered:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QtStyler.highlight())
            p.drawRoundedRect(rect, _ITEM_RADIUS, _ITEM_RADIUS)
        self._draw_content(p)
        p.end()

    def enterEvent(self, e):
        self._hovered = True
        self.update()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._hovered = False
        self.update()
        super().leaveEvent(e)


class _MultiItemRow(QAbstractButton):
    toggled_item = Signal(str, bool)

    def __init__(self, label: str, parent=None):
        super().__init__(parent)
        self._label = label
        self._checked = False
        self._hovered = False
        self.setFixedHeight(_ITEM_H)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)

    def set_checked(self, v: bool):
        self._checked = v
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(2, 2, self.width() - 4, _ITEM_H - 4)
        if self._checked:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QtStyler.highlight_muted())
            p.drawRoundedRect(rect, _ITEM_RADIUS, _ITEM_RADIUS)
        if self._hovered:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QtStyler.highlight())
            p.drawRoundedRect(rect, _ITEM_RADIUS, _ITEM_RADIUS)

        # checkbox
        cb = QRectF(10, _ITEM_H / 2 - 7, 14, 14)
        color = QtStyler.highlight()
        p.setPen(QPen(color, 1.5))
        color = QtStyler.background()
        p.setBrush(color)
        p.drawRoundedRect(cb, 3, 3)
        if self._checked:
            p.setPen(
                QPen(
                    QtStyler.icon(),
                    2,
                    Qt.PenStyle.SolidLine,
                    Qt.PenCapStyle.RoundCap,
                    Qt.PenJoinStyle.RoundJoin,
                ),
            )
            cx, cy = cb.center().x(), cb.center().y()
            p.drawLine(int(cx - 3), int(cy), int(cx - 1), int(cy + 2))
            p.drawLine(int(cx - 1), int(cy + 2), int(cx + 4), int(cy - 3))

        # text
        p.setFont(_base_font())
        p.setPen(QtStyler.text())
        p.drawText(
            QRectF(32, 0, self.width() - 42, _ITEM_H),
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            self._label,
        )
        p.end()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._checked = not self._checked
            self.update()
            self.toggled_item.emit(self._label, self._checked)
        super().mousePressEvent(e)

    def enterEvent(self, e):
        self._hovered = True
        self.update()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._hovered = False
        self.update()
        super().leaveEvent(e)
