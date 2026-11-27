from __future__ import annotations

import typing as ty

from qtpy.QtCore import QEvent, QObject, QPoint, Qt, Signal
from qtpy.QtGui import QColor, QMouseEvent
from qtpy.QtWidgets import QFrame, QGraphicsDropShadowEffect, QSizePolicy, QStackedWidget, QWidget

import qtextra.helpers as hp


class QtOverlayWidget(QWidget):
    """Floating settings card that lives inside (and is clipped to) its parent tab.

    The card holds one page per results tab; `set_current` picks the page of the visible tab and the card resizes to
    fit it. It is shown only while it is open (see `set_open`), the current tab has a page, and the caller marks it as
    available (e.g. a model is selected). It can be dragged by its header or with the right mouse button anywhere on
    the card, and minimized to its header.
    """

    WIDTH = 440
    SHADOW_MARGIN = (10, 2, 10, 14)

    evt_closed = Signal()

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self._pages: dict[QWidget, tuple[str, QWidget]] = {}
        self._open = True
        self._available = False
        self._drag_offset: QPoint | None = None
        self._user_moved = False
        self._default_position: ty.Callable[[], QPoint] | None = None

        self.card = QFrame(self)
        self.card.setObjectName("settingsCard")
        shadow = QGraphicsDropShadowEffect(self.card)
        shadow.setBlurRadius(24)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 90))
        self.card.setGraphicsEffect(shadow)

        self.header = QWidget(self.card)
        self.header.setToolTip("Drag to move (or right-click and drag anywhere on the card).")
        self.header.setCursor(Qt.CursorShape.OpenHandCursor)
        icon = hp.make_qta_label(self.header, "gear", size_preset="small")
        self.title_label = hp.make_label(self.header, "Settings", object_name="settingsCardTitle")
        self.minimize_btn = hp.make_qta_btn(
            self.header,
            "chevron_up",
            tooltip="Minimize or restore the settings.",
            checkable=True,
            checked_icon_name="chevron_down",
            func=self.set_minimized,
            size_preset="small",
        )
        close_btn = hp.make_qta_btn(self.header, "cross", tooltip="Hide settings", func=self.close, size_preset="small")
        hp.make_h_layout(
            icon,
            self.title_label,
            self.minimize_btn,
            close_btn,
            stretch_id=(1,),
            spacing=6,
            margin=0,
            parent=self.header,
        )

        self.body = QWidget(self.card)
        self.stack = QStackedWidget(self.body)
        body_layout = hp.make_v_layout(parent=self.body, margin=(0, 4, 0, 0), spacing=0)
        body_layout.addWidget(self.stack)

        card_layout = hp.make_v_layout(parent=self.card, margin=(12, 8, 12, 10), spacing=4)
        card_layout.addWidget(self.header)
        card_layout.addWidget(self.body)

        layout = hp.make_v_layout(parent=self, margin=self.SHADOW_MARGIN, spacing=0)
        layout.addWidget(self.card)
        self.setFixedWidth(self.WIDTH)
        parent.installEventFilter(self)
        self.hide()

    @staticmethod
    def make_section(parent: QWidget, title: str) -> QWidget:
        """Make the separator that starts a group of rows on a settings page."""
        return hp.make_h_line_with_text(title, parent, bold=False)

    def set_default_position(self, func: ty.Callable[[], QPoint]) -> None:
        """Set the function returning the top-left position (in parent coordinates) used until the user moves it."""
        self._default_position = func

    def add_page(self, tab: QWidget, title: str, page: QWidget) -> None:
        """Register the settings `page` shown (with `title`) while `tab` is the current results tab."""
        self._pages[tab] = (title, page)
        self.stack.addWidget(page)

    def has_page(self, tab: QWidget | None) -> bool:
        """Return whether `tab` has a settings page."""
        return tab in self._pages

    def current_tab(self) -> QWidget | None:
        """Return the tab whose page is currently shown."""
        current = self.stack.currentWidget()
        return next((tab for tab, (_, page) in self._pages.items() if page is current), None)

    @property
    def is_open(self) -> bool:
        """Return whether the user wants the card open."""
        return self._open

    @property
    def is_minimized(self) -> bool:
        """Return whether the card is collapsed to its header."""
        return self.body.isHidden()

    def set_open(self, is_open: bool) -> None:
        """Open or close the card; it only becomes visible when a page is available."""
        self._open = is_open
        self._update_visibility()

    def set_minimized(self, minimized: bool) -> None:
        """Collapse the card to its header, or restore it."""
        self.minimize_btn.setChecked(minimized)  # emits `toggled` (swaps the chevron), not `clicked`
        self.body.setHidden(minimized)
        self._fit()

    def set_current(self, tab: QWidget | None, available: bool = True) -> None:
        """Show the settings page of `tab`, or hide the card when it has none or is not `available`."""
        self._available = available and tab in self._pages
        if tab in self._pages:
            title, page = self._pages[tab]
            self.title_label.setText(title)
            # size the stack to the current page rather than the largest one
            for _, other in self._pages.values():
                policy = QSizePolicy.Policy.Preferred if other is page else QSizePolicy.Policy.Ignored
                other.setSizePolicy(policy, policy)
            self.stack.setCurrentWidget(page)
        self._update_visibility()

    def close(self) -> bool:
        """Close the card and notify the toggle button."""
        self.set_open(False)
        self.evt_closed.emit()
        return True

    def _update_visibility(self) -> None:
        visible = self._open and self._available
        self.setVisible(visible)
        if visible:
            self._fit()
            self.raise_()

    def _fit(self) -> None:
        """Resize to the content and keep the card inside its parent."""
        self.stack.updateGeometry()
        # nested layouts cache their size hints, so refresh them inside-out
        for layout in (self.body.layout(), self.card.layout(), self.layout()):
            layout.invalidate()
            layout.activate()
        self.resize(self.WIDTH, self.sizeHint().height())
        if not self._user_moved and self._default_position is not None:
            self.move(self._default_position())
        self._clamp()

    def _clamp(self) -> None:
        parent = self.parentWidget()
        x = max(0, min(self.x(), parent.width() - self.width()))
        y = max(0, min(self.y(), parent.height() - self.height()))
        self.move(x, y)

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:  # type: ignore[override]
        """Keep the card in place when the parent resizes."""
        if obj is self.parentWidget() and event.type() == QEvent.Type.Resize and self.isVisible():
            self._fit()
        return super().eventFilter(obj, event)

    def mousePressEvent(self, event: QMouseEvent) -> None:  # type: ignore[override]
        """Start dragging with the right button anywhere, or the left button on the header."""
        on_header = self.header.geometry().contains(self.card.mapFrom(self, event.position().toPoint()))
        if event.button() == Qt.MouseButton.RightButton or (event.button() == Qt.MouseButton.LeftButton and on_header):
            self._drag_offset = event.position().toPoint()
            self.header.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # type: ignore[override]
        """Move the card while dragging."""
        if self._drag_offset is not None:
            self.move(self.mapToParent(event.position().toPoint()) - self._drag_offset)
            self._clamp()
            self._user_moved = True
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # type: ignore[override]
        """Stop dragging."""
        if self._drag_offset is not None:
            self._drag_offset = None
            self.header.setCursor(Qt.CursorShape.OpenHandCursor)
            event.accept()
            return
        super().mouseReleaseEvent(event)
