"""WhatsNew carousel dialog."""

from __future__ import annotations

import contextlib
from pathlib import Path

from pydantic import BaseModel, Field
from qtpy.QtCore import QEasingCurve, QPoint, QPropertyAnimation, Qt, Signal
from qtpy.QtGui import QBrush, QColor, QLinearGradient, QPainter, QPen, QPixmap
from qtpy.QtWidgets import (
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QStackedWidget,
    QWidget,
)

import qtextra.helpers as hp
from qtextra.config import QtStyler
from qtextra.widgets.qt_dialog import QtDialog


class WhatsNewPage(BaseModel):
    """Data model for a single What's New carousel slide.

    Parameters
    ----------
    title : str
        Slide heading.
    html : str
        Rich body text (HTML subset).
    bullets : list[str]
        Numbered callout lines displayed below the body.
    image_path : str | None
        Path to an image file shown on the right side.
    icon_char : str | None
        Fallback emoji/character used when no image is provided.
    gradient_start : str
        CSS colour for the top-left corner of the slide background gradient.
    gradient_end : str
        CSS colour for the bottom-right corner of the slide background gradient.
    """

    title: str = ""
    html: str = ""
    bullets: list[str] = Field(default_factory=list)
    image_path: str | None = None
    icon_char: str | None = None
    gradient_start: str = "#C9DFF5"
    gradient_end: str = "#F9C5A7"


class _GradientBackground(QWidget):
    """Paints a diagonal linear gradient background."""

    def __init__(self, start: str, end: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._top = QColor(start)
        self._bottom = QColor(end)

    def set_colors(self, start: str, end: str) -> None:
        """Update gradient colours and repaint."""
        self._top = QColor(start)
        self._bottom = QColor(end)
        self.update()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        grad = QLinearGradient(0, 0, self.width(), self.height())
        grad.setColorAt(0.0, self._top)
        grad.setColorAt(1.0, self._bottom)
        p.fillRect(self.rect(), grad)


class _DotIndicator(QWidget):
    """Row of navigation dots — active one is hollow, idle ones are filled.

    Emits ``evt_clicked(int)`` when the user clicks a dot.
    """

    evt_clicked = Signal(int)

    _DOT_R = 5
    _DOT_BIG = 7
    _SPACING = 18

    def __init__(self, count: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._count = count
        self._current = 0
        self.setObjectName("transparent")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(self._DOT_BIG * 2 + 4)
        self.setMinimumWidth(count * self._SPACING + self._DOT_BIG * 2)

    def set_current(self, idx: int) -> None:
        """Update which dot is highlighted."""
        self._current = idx
        self.update()

    def _dot_index_at(self, x: int) -> int | None:
        """Return the dot index under pixel *x*, or ``None`` if no hit."""
        total_w = (self._count - 1) * self._SPACING + self._DOT_BIG * 2
        x0 = (self.width() - total_w) // 2
        for i in range(self._count):
            cx = x0 + i * self._SPACING
            if abs(x - cx) <= self._DOT_BIG + 2:
                return i
        return None

    def mousePressEvent(self, event) -> None:
        """Emit ``evt_clicked`` with the index of the clicked dot."""
        if event.button() == Qt.MouseButton.LeftButton:
            idx = self._dot_index_at(event.x())
            if idx is not None:
                self.evt_clicked.emit(idx)

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        total_w = (self._count - 1) * self._SPACING + self._DOT_BIG * 2
        x0 = (self.width() - total_w) // 2
        cy = self.height() // 2
        for i in range(self._count):
            cx = x0 + i * self._SPACING
            if i == self._current:
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.setPen(QPen(QtStyler.highlight(), 2))
                p.drawEllipse(QPoint(cx, cy), self._DOT_BIG, self._DOT_BIG)
            else:
                p.setBrush(QBrush(QtStyler.foreground()))
                p.setPen(Qt.PenStyle.NoPen)
                p.drawEllipse(QPoint(cx, cy), self._DOT_R, self._DOT_R)


class _CalloutBadge(QWidget):
    """Filled circle with a number inside, used for bullet callouts."""

    _SIZE = 28

    def __init__(self, number: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._number = number
        self.setFixedSize(self._SIZE, self._SIZE)

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QBrush(QtStyler.icon()))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(0, 0, self._SIZE, self._SIZE)
        p.setPen(QPen(Qt.GlobalColor.white))
        f = p.font()
        f.setBold(True)
        f.setPixelSize(14)
        p.setFont(f)
        p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, str(self._number))


class _PageCard(QWidget):
    """One carousel slide: title + HTML body + optional bullets + optional image."""

    _IMG_W, _IMG_H = 300, 260

    def __init__(self, page: WhatsNewPage, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("transparent")
        self._build(page)

    def _build(self, page: WhatsNewPage) -> None:
        root = QHBoxLayout(self)
        root.setContentsMargins(48, 36, 48, 20)
        root.setSpacing(40)

        left = hp.make_v_layout(spacing=12)

        title_lbl = hp.make_label(self, page.title, bold=True, wrap=True, font_size=22)
        left.addWidget(title_lbl)

        body_lbl = hp.make_label(self, page.html, enable_url=True, wrap=True)
        left.addWidget(body_lbl)

        for i, bullet in enumerate(page.bullets, start=1):
            row = hp.make_h_layout(spacing=10)
            row.addWidget(_CalloutBadge(i), 0, Qt.AlignmentFlag.AlignTop)
            blbl = hp.make_label(self, bullet, wrap=True, bold=True)
            row.addWidget(blbl, 1)
            left.addLayout(row)

        left.addStretch()
        root.addLayout(left, 1)

        if page.image_path and Path(page.image_path).exists():
            img_lbl = hp.make_label(self, alignment=Qt.AlignmentFlag.AlignCenter)
            pix = QPixmap(page.image_path).scaled(
                self._IMG_W,
                self._IMG_H,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            img_lbl.setPixmap(pix)
            root.addWidget(img_lbl, 0, Qt.AlignmentFlag.AlignCenter)
        elif page.icon_char:
            icon_lbl = hp.make_label(self, page.icon_char, alignment=Qt.AlignmentFlag.AlignCenter, object_name="96px_t")
            icon_lbl.setFixedSize(self._IMG_W, self._IMG_H)
            root.addWidget(icon_lbl, 0, Qt.AlignmentFlag.AlignCenter)


class QtWhatsNewDialog(QtDialog):
    """Drop-in "What's New" carousel dialog.

    Parameters
    ----------
    pages : list[WhatsNewPage]
        Slide data; each item describes one page of the carousel.
    version : str
        Shown in the window title.
    parent : QWidget | None
    """

    CARD_W, CARD_H = 760, 500

    def __init__(
        self,
        pages: list[WhatsNewPage],
        version: str = "",
        parent: QWidget | None = None,
    ) -> None:
        self._pages = pages
        self._current = 0
        self._version = version
        super().__init__(parent, title=f"What's New{(' in ' + version) if version else ''}")
        self.setFixedSize(self.CARD_W, self.CARD_H + 100)
        self._go_to(0, animate=False)

    # noinspection PyAttributeOutsideInit
    def make_panel(self):
        """Build and return the dialog layout."""
        first = self._pages[0] if self._pages else WhatsNewPage()

        # Gradient covers the entire dialog
        self._bg = _GradientBackground(first.gradient_start, first.gradient_end)
        bg_layout = hp.make_v_layout(margin=0, spacing=0, parent=self._bg)

        self._stack = QStackedWidget()
        self._stack.setObjectName("transparent")
        for page in self._pages:
            self._stack.addWidget(_PageCard(page))
        bg_layout.addWidget(self._stack, 1)

        # Bottom bar — lives inside _bg so gradient shows underneath
        self._dots = _DotIndicator(len(self._pages))
        self._dots.evt_clicked.connect(self._go_to)
        self._skip_btn = hp.make_btn(self, "Skip", func=self.reject, object_name="cancel_btn")
        self._prev_btn = hp.make_btn(self, "< Previous", func=self._prev, bold=True)
        self._next_btn = hp.make_btn(self, "Next >", func=self._next)

        # Equal-stretch left/right sections keep dots perfectly centred
        left_l = hp.make_h_layout(self._skip_btn, margin=0, stretch_after=True)
        right_l = hp.make_h_layout(self._prev_btn, self._next_btn, margin=0, spacing=8, stretch_before=True)

        bar = QHBoxLayout()
        bar.setContentsMargins(24, 10, 24, 16)
        bar.setSpacing(0)
        bar.addLayout(left_l, 1)
        bar.addWidget(self._dots, 0, Qt.AlignmentFlag.AlignVCenter)
        bar.addLayout(right_l, 1)
        bg_layout.addLayout(bar)

        layout = hp.make_v_layout(spacing=0, margin=0)
        layout.addWidget(self._bg, 1)
        return layout

    def _go_to(self, idx: int, animate: bool = True) -> None:
        if idx < 0 or idx >= len(self._pages):
            return

        self._current = idx
        self._stack.setCurrentIndex(idx)

        page = self._pages[idx]
        self._bg.set_colors(page.gradient_start, page.gradient_end)
        self._dots.set_current(idx)

        self._prev_btn.setEnabled(idx > 0)

        is_last = idx == len(self._pages) - 1
        self._next_btn.setText("Done" if is_last else "Next >")
        hp.set_object_name(self._next_btn, object_name="success_btn" if is_last else "")

        with contextlib.suppress(RuntimeError):
            self._next_btn.clicked.disconnect()
        self._next_btn.clicked.connect(self.accept if is_last else self._next)

        if animate:
            w = self._stack.currentWidget()
            effect = QGraphicsOpacityEffect(w)
            w.setGraphicsEffect(effect)
            anim = QPropertyAnimation(effect, b"opacity", w)
            anim.setDuration(200)
            anim.setStartValue(0.0)
            anim.setEndValue(1.0)
            anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            anim.start()

    def _next(self) -> None:
        self._go_to(self._current + 1)

    def _prev(self) -> None:
        self._go_to(self._current - 1)

    @staticmethod
    def show_if_new(
        pages: list[WhatsNewPage],
        version: str,
        last_seen_key: str = "",
        parent: QWidget | None = None,
    ) -> bool:
        """Show the dialog only when *version* differs from the stored value.

        Stores the acknowledged version in QSettings under *last_seen_key*.
        Returns ``True`` when the user accepts, ``False`` on skip/close.
        """
        from qtpy.QtCore import QSettings

        settings = QSettings()
        if settings.value(last_seen_key, "") == version:
            return True
        dlg = QtWhatsNewDialog(pages, version, parent)
        result = dlg.exec()
        if result:
            settings.setValue(last_seen_key, version)
        return bool(result)


# For backwards compatibility
WhatsNewDialog = QtWhatsNewDialog
