"""
WhatsNew Widget — a polished "What's New" onboarding carousel for Qt applications.

Requirements:
    pip install qtpy PyQt5   (or PySide6)

Usage:
    python whats_new_widget.py

Customise the PAGES list at the bottom to supply your own images and HTML.
Each page dict accepts:
    image_path : str | None   – absolute / relative path to an image file,
                                or None to show a placeholder icon
    title      : str          – plain-text slide title
    html       : str          – rich HTML rendered in the body area
"""

import contextlib
import sys
from pathlib import Path

from qtpy.QtCore import Property, QEasingCurve, QObject, QPoint, QPropertyAnimation, QSize, Qt, QTimer
from qtpy.QtGui import (
    QBrush,
    QColor,
    QFont,
    QFontDatabase,
    QIcon,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from qtpy.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QStyle,
    QVBoxLayout,
    QWidget,
)

# ── Colour palette ────────────────────────────────────────────────────────────
ACCENT = QColor("#F07A2E")  # warm orange (matches screenshots)
ACCENT_DARK = QColor("#D4611A")
BG_LIGHT = QColor("#FAFAFA")
TEXT_HEAD = QColor("#1C1C1E")
TEXT_BODY = QColor("#48484A")
DOT_ACTIVE = QColor("#F07A2E")
DOT_IDLE = QColor("#D1D1D6")

RADIUS = 16  # card corner radius
SHADOW_CLR = QColor(0, 0, 0, 30)


# ── Gradient background widget ────────────────────────────────────────────────
class GradientBackground(QWidget):
    """Draws a soft radial/linear gradient matching the reference screenshots."""

    GRADIENTS = [
        # (top-left colour, bottom-right colour)
        ("#C9DFF5", "#F9C5A7"),  # blue → peach
        ("#FFFFFF", "#EAF3FB"),  # white → faint blue
        ("#E8F5E9", "#FFF9C4"),  # mint → cream
        ("#F3E5F5", "#FCE4EC"),  # lavender → rose
    ]

    def __init__(self, index: int = 0, parent=None):
        super().__init__(parent)
        self.set_index(index)

    def set_index(self, index: int):
        pair = self.GRADIENTS[index % len(self.GRADIENTS)]
        self._top = QColor(pair[0])
        self._bottom = QColor(pair[1])
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        grad = QLinearGradient(0, 0, self.width(), self.height())
        grad.setColorAt(0.0, self._top)
        grad.setColorAt(1.0, self._bottom)
        p.fillRect(self.rect(), grad)


# ── Dot indicator ─────────────────────────────────────────────────────────────
class DotIndicator(QWidget):
    DOT_R = 5
    DOT_BIG = 7
    SPACING = 18

    def __init__(self, count: int, parent=None):
        super().__init__(parent)
        self._count = count
        self._current = 0
        h = self.DOT_BIG * 2 + 4
        self.setFixedHeight(h)
        self.setMinimumWidth(count * self.SPACING + self.DOT_BIG * 2)

    def set_current(self, idx: int):
        self._current = idx
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        total_w = (self._count - 1) * self.SPACING + self.DOT_BIG * 2
        x0 = (self.width() - total_w) // 2
        cy = self.height() // 2
        for i in range(self._count):
            if i == self._current:
                r = self.DOT_BIG
                p.setBrush(QBrush(DOT_ACTIVE))
                p.setPen(QPen(DOT_ACTIVE, 2))
                # hollow circle for active
                p.setBrush(Qt.NoBrush)
                p.drawEllipse(QPoint(x0 + i * self.SPACING, cy), r, r)
            else:
                r = self.DOT_R
                p.setBrush(QBrush(DOT_IDLE))
                p.setPen(Qt.NoPen)
                p.drawEllipse(QPoint(x0 + i * self.SPACING, cy), r, r)


# ── Orange button ─────────────────────────────────────────────────────────────
_BTN_STYLE = """
QPushButton {{
    background: {bg};
    color: white;
    border: none;
    border-radius: 10px;
    padding: 0 22px;
    font-size: 15px;
    font-weight: 600;
}}
QPushButton:hover  {{ background: {hover}; }}
QPushButton:pressed {{ background: {press}; }}
"""


class OrangeButton(QPushButton):
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setFixedHeight(40)
        self.setMinimumWidth(90)
        self.setStyleSheet(
            _BTN_STYLE.format(
                bg=ACCENT.name(),
                hover=ACCENT_DARK.lighter(115).name(),
                press=ACCENT_DARK.name(),
            ),
        )


# ── Numbered callout label (①②…) ─────────────────────────────────────────────
class CalloutBadge(QWidget):
    SIZE = 28

    def __init__(self, number: int, parent=None):
        super().__init__(parent)
        self._number = number
        self.setFixedSize(self.SIZE, self.SIZE)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setBrush(QBrush(ACCENT))
        p.setPen(Qt.NoPen)
        p.drawEllipse(0, 0, self.SIZE, self.SIZE)
        p.setPen(QPen(Qt.white))
        f = p.font()
        f.setBold(True)
        f.setPixelSize(14)
        p.setFont(f)
        p.drawText(self.rect(), Qt.AlignCenter, str(self._number))


# ── Single page card ──────────────────────────────────────────────────────────
class PageCard(QWidget):
    """
    One slide.  Layout mirrors the reference screenshots:
      - optional image / illustration on the right (or top)
      - title + HTML body on the left
      - bullet callouts if provided.
    """

    IMG_W, IMG_H = 300, 260

    def __init__(self, page: dict, parent=None):
        super().__init__(parent)
        self._build(page)

    def _build(self, page: dict):
        root = QHBoxLayout(self)
        root.setContentsMargins(48, 36, 48, 20)
        root.setSpacing(40)

        # ── Left column ───────────────────────────────────────────────────────
        left = QVBoxLayout()
        left.setSpacing(12)

        # Title
        title_lbl = QLabel(page.get("title", ""))
        title_lbl.setWordWrap(True)
        f = QFont()
        f.setPointSize(22)
        f.setBold(True)
        title_lbl.setFont(f)
        title_lbl.setStyleSheet(f"color: {TEXT_HEAD.name()};")
        left.addWidget(title_lbl)

        # Body HTML
        body_lbl = QLabel()
        body_lbl.setTextFormat(Qt.RichText)
        body_lbl.setWordWrap(True)
        body_lbl.setOpenExternalLinks(True)
        body_lbl.setText(page.get("html", ""))
        body_lbl.setStyleSheet(f"color: {TEXT_BODY.name()}; font-size: 14px; line-height: 1.5;")
        left.addWidget(body_lbl)

        # Callout bullets
        for i, bullet in enumerate(page.get("bullets", []), start=1):
            row = QHBoxLayout()
            row.setSpacing(10)
            badge = CalloutBadge(i)
            row.addWidget(badge, 0, Qt.AlignTop)
            blbl = QLabel(bullet)
            blbl.setWordWrap(True)
            blbl.setStyleSheet(
                f"color: {ACCENT.name()}; font-size: 14px; font-weight: 600;",
            )
            row.addWidget(blbl, 1)
            left.addLayout(row)

        left.addStretch()
        root.addLayout(left, 1)

        # ── Right column – image ──────────────────────────────────────────────
        image_path = page.get("image_path")
        if image_path and Path(image_path).exists():
            img_lbl = QLabel()
            img_lbl.setAlignment(Qt.AlignCenter)
            pix = QPixmap(image_path).scaled(
                self.IMG_W,
                self.IMG_H,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
            img_lbl.setPixmap(pix)
            root.addWidget(img_lbl, 0, Qt.AlignCenter)
        elif page.get("icon_char"):
            # Fallback: big emoji / unicode character as illustration
            icon_lbl = QLabel(page["icon_char"])
            icon_lbl.setAlignment(Qt.AlignCenter)
            icon_lbl.setStyleSheet("font-size: 96px;")
            icon_lbl.setFixedSize(self.IMG_W, self.IMG_H)
            root.addWidget(icon_lbl, 0, Qt.AlignCenter)


# ── Main dialog ───────────────────────────────────────────────────────────────
class WhatsNewDialog(QDialog):
    """
    Drop-in "What's New" carousel dialog.

    Parameters
    ----------
    pages : list[dict]
        Each dict may contain:
            title      str   – slide heading
            html       str   – rich body text (HTML subset)
            bullets    list  – orange numbered callout lines
            image_path str   – path to an image file (optional)
            icon_char  str   – fallback emoji/character (optional)
    version : str
        Shown in the window title.
    parent : QWidget | None
    """

    CARD_W, CARD_H = 760, 500

    def __init__(self, pages: list, version: str = "", parent=None):
        super().__init__(parent)
        self._pages = pages
        self._current = 0
        self._version = version
        self._setup_ui()
        self._go_to(0, animate=False)

    # ── UI construction ───────────────────────────────────────────────────────
    def _setup_ui(self):
        self.setWindowTitle(f"What's New{(' in ' + self._version) if self._version else ''}")
        self.setFixedSize(self.CARD_W, self.CARD_H + 100)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        # ── Card container with rounded corners ───────────────────────────────
        self._card = QFrame(self)
        self._card.setObjectName("card")
        self._card.setStyleSheet("""
            QFrame#card {
                background: #FAFAFA;
                border-radius: 18px;
            }
        """)
        card_layout = QVBoxLayout(self._card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)

        # Gradient top area (holds the page cards)
        self._bg = GradientBackground(0, self._card)
        self._bg.setFixedHeight(self.CARD_H)

        # Stacked widget inside the gradient bg
        bg_layout = QVBoxLayout(self._bg)
        bg_layout.setContentsMargins(0, 0, 0, 0)

        self._stack = QStackedWidget()
        self._stack.setStyleSheet("background: transparent;")
        for page in self._pages:
            self._stack.addWidget(PageCard(page))
        bg_layout.addWidget(self._stack)

        card_layout.addWidget(self._bg)

        # ── Bottom bar ────────────────────────────────────────────────────────
        bar = QHBoxLayout()
        bar.setContentsMargins(24, 10, 24, 16)
        bar.setSpacing(12)

        # Skip / Done
        self._skip_btn = QPushButton("Skip")
        self._skip_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {TEXT_BODY.name()};
                border: none;
                font-size: 14px;
            }}
            QPushButton:hover {{ color: {TEXT_HEAD.name()}; text-decoration: underline; }}
        """)
        self._skip_btn.clicked.connect(self.reject)
        bar.addWidget(self._skip_btn, 0, Qt.AlignVCenter)

        bar.addStretch()

        # Dot indicator
        self._dots = DotIndicator(len(self._pages))
        bar.addWidget(self._dots, 0, Qt.AlignVCenter)

        bar.addStretch()

        # Prev / Next
        self._prev_btn = OrangeButton("‹")
        self._prev_btn.setFixedWidth(44)
        self._prev_btn.clicked.connect(self._prev)

        self._next_btn = OrangeButton("Next ›")
        self._next_btn.clicked.connect(self._next)

        bar.addWidget(self._prev_btn)
        bar.addWidget(self._next_btn)

        bar_widget = QWidget()
        bar_widget.setLayout(bar)
        bar_widget.setStyleSheet("background: #FAFAFA;")
        card_layout.addWidget(bar_widget)

        outer.addWidget(self._card)

    # ── Navigation ────────────────────────────────────────────────────────────
    def _go_to(self, idx: int, animate: bool = True):
        if idx < 0 or idx >= len(self._pages):
            return

        self._current = idx
        self._stack.setCurrentIndex(idx)
        self._bg.set_index(idx)
        self._dots.set_current(idx)

        # Update buttons
        self._prev_btn.setEnabled(idx > 0)
        self._prev_btn.setStyleSheet(self._prev_btn.styleSheet())  # force repaint

        is_last = idx == len(self._pages) - 1
        self._next_btn.setText("Done" if is_last else "Next ›")
        self._skip_btn.setVisible(not is_last)

        if is_last:
            with contextlib.suppress(RuntimeError):
                self._next_btn.clicked.disconnect()
            self._next_btn.clicked.connect(self.accept)
        else:
            with contextlib.suppress(RuntimeError):
                self._next_btn.clicked.disconnect()
            self._next_btn.clicked.connect(self._next)

        # Opacity fade
        if animate:
            w = self._stack.currentWidget()
            effect = QGraphicsOpacityEffect(w)
            w.setGraphicsEffect(effect)
            anim = QPropertyAnimation(effect, b"opacity", w)
            anim.setDuration(200)
            anim.setStartValue(0.0)
            anim.setEndValue(1.0)
            anim.setEasingCurve(QEasingCurve.OutCubic)
            anim.start()

    def _next(self):
        self._go_to(self._current + 1)

    def _prev(self):
        self._go_to(self._current - 1)

    # ── Allow dragging the frameless window ───────────────────────────────────
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and hasattr(self, "_drag_pos"):
            self.move(event.globalPos() - self._drag_pos)

    # ── Convenience static method ─────────────────────────────────────────────
    @staticmethod
    def show_if_new(pages: list, version: str, last_seen_key: str = "", parent=None) -> bool:
        """
        Show the dialog only if *version* differs from what was stored in
        QSettings under *last_seen_key*.  Returns True when the user
        acknowledges (clicks Done), False if they skip.

        For simple scripts, just call WhatsNewDialog(pages, version).exec_()
        """
        from qtpy.QtCore import QSettings

        settings = QSettings()
        if settings.value(last_seen_key, "") == version:
            return True
        dlg = WhatsNewDialog(pages, version, parent)
        result = dlg.exec_()
        if result:
            settings.setValue(last_seen_key, version)
        return bool(result)


# ── Demo ──────────────────────────────────────────────────────────────────────
DEMO_PAGES = [
    {
        "title": "Welcome to version 3.0!",
        "html": (
            "Applications on your computer can send whatever information they "
            "want to wherever they want. Most often they do that for good reason, "
            "at your explicit request.<br><br>"
            "<b>But sometimes they don't!</b>"
        ),
        "icon_char": "🔒",
    },
    {
        "title": "Network Monitor",
        "html": (
            "The <b>Network Monitor</b> is a powerful tool for viewing, analyzing "
            "and controlling your app's network activity on a per-process basis."
        ),
        "bullets": [
            "The connection list shows successful and blocked connections for all running processes.",
            "The traffic diagram provides a detailed history of each process for in-depth traffic analysis.",
        ],
        "icon_char": "📡",
    },
    {
        "title": "Smarter Filtering",
        "html": (
            "New <b>domain-based rules</b> let you block or allow entire hostnames "
            "with a single click.  Rules sync across your devices automatically."
        ),
        "bullets": [
            "One-click wildcard rules cover all subdomains instantly.",
            "Import & export your rule sets as a simple JSON file.",
        ],
        "icon_char": "🛡️",
    },
    {
        "title": "Live Statistics",
        "html": (
            "A redesigned <b>statistics panel</b> shows bandwidth, request counts, "
            "and latency broken down by process, domain, and protocol — all in "
            "real time."
        ),
        "icon_char": "📊",
    },
]


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    dlg = WhatsNewDialog(DEMO_PAGES, version="3.0")
    result = dlg.exec_()
    print("Accepted:" if result else "Skipped")
    sys.exit(0)
