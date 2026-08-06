"""Modal, scrollable side overlay for reading mixed content."""

from __future__ import annotations

from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import TypeAlias

from qtpy.QtCore import (
    Property,
    QEasingCurve,
    QEvent,
    QObject,
    QPoint,
    QPropertyAnimation,
    QRect,
    QSize,
    Qt,
    QUrl,
    Signal,
)
from qtpy.QtGui import QImage, QKeyEvent, QKeySequence, QMouseEvent, QPainter, QPaintEvent, QPixmap, QResizeEvent
from qtpy.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from qtpy.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QScrollArea,
    QShortcut,
    QSizePolicy,
    QStyle,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

import qtextra.helpers as hp
from qtextra.config import QtStyler
from qtextra.widgets.qt_overlay import _apply_elevated_card_effect


@dataclass(frozen=True, slots=True)
class SideOverlayTitle:
    """A prominent heading in a :class:`QtSideOverlay` document."""

    text: str


@dataclass(frozen=True, slots=True)
class SideOverlaySubtitle:
    """A secondary heading in a :class:`QtSideOverlay` document."""

    text: str


@dataclass(frozen=True, slots=True)
class SideOverlayText:
    """A selectable, word-wrapped paragraph in a side-overlay document."""

    text: str


@dataclass(frozen=True, slots=True)
class SideOverlaySeparator:
    """A horizontal separator in a side-overlay document."""


@dataclass(frozen=True, slots=True)
class SideOverlayImage:
    """An image in a side-overlay document.

    ``source`` can be a local image path, an ``http(s)`` URL, a ``QImage``, or
    a ``QPixmap``. Remote images are fetched asynchronously when the overlay
    content is built.
    """

    source: str | Path | QImage | QPixmap


SideOverlayBlock: TypeAlias = (
    SideOverlayTitle | SideOverlaySubtitle | SideOverlayText | SideOverlaySeparator | SideOverlayImage
)


class _SideOverlayImageLabel(QWidget):
    """Responsive image label that preserves the source aspect ratio."""

    _MAX_HEIGHT = 320

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._source_pixmap = QPixmap()
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

    def hasHeightForWidth(self) -> bool:  # type: ignore[override]
        """Return that image height follows the available width."""
        return not self._source_pixmap.isNull()

    def heightForWidth(self, width: int) -> int:  # type: ignore[override]
        """Return the aspect-ratio-preserving image height for *width*."""
        if self._source_pixmap.isNull() or width <= 0:
            return 0
        height = round(width * self._source_pixmap.height() / self._source_pixmap.width())
        return min(height, self._MAX_HEIGHT)

    def sizeHint(self) -> QSize:  # type: ignore[override]
        """Return a practical initial image size for a scrollable document."""
        if self._source_pixmap.isNull():
            return QSize()
        width = min(self._source_pixmap.width(), 360)
        return self._source_pixmap.size().scaled(
            width,
            self._MAX_HEIGHT,
            Qt.AspectRatioMode.KeepAspectRatio,
        )

    def set_source_pixmap(self, pixmap: QPixmap) -> None:
        """Set the original image and refresh its displayed size."""
        self._source_pixmap = pixmap
        self.updateGeometry()

        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:  # type: ignore[override]
        """Draw the source pixmap without changing widget geometry."""
        if self._source_pixmap.isNull():
            return
        target_size = self._source_pixmap.size()
        target_size.scale(
            self.contentsRect().size(),
            Qt.AspectRatioMode.KeepAspectRatio,
        )
        target = QRect(QPoint(), target_size)
        target.moveCenter(self.contentsRect().center())
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.drawPixmap(target, self._source_pixmap)
        del event


class QtSideOverlay(QWidget):
    """A modal, scrollable document panel that slides over a host widget.

    Parameters
    ----------
    parent : QWidget
        A widget inside the window or dialog to cover. The overlay attaches to
        its top-level window, so it can safely be created from nested content.
    header_title : str
        Text kept visible in the panel's fixed header.
    blocks : tuple[SideOverlayBlock, ...]
        Ordered document content rendered beneath the fixed header.
    side : {"left", "right"}
        Edge from which the panel enters. Defaults to ``"right"``.
    width : int
        Preferred panel width in pixels. It is clamped to the host width.
    animation_duration : int
        Open and dismissal animation duration in milliseconds.
    """

    evt_opened = Signal()
    evt_closed = Signal()
    evt_image_failed = Signal(str)

    _SCRIM_OPACITY = 0.42

    def __init__(
        self,
        parent: QWidget,
        *,
        header_title: str = "",
        blocks: tuple[SideOverlayBlock, ...] | list[SideOverlayBlock] = (),
        side: str = "right",
        width: int = 440,
        animation_duration: int = 200,
    ) -> None:
        host = parent.window()
        super().__init__(host)
        if side not in {"left", "right"}:
            raise ValueError("side must be either 'left' or 'right'.")
        if width <= 0:
            raise ValueError("width must be greater than zero.")
        if animation_duration < 0:
            raise ValueError("animation_duration cannot be negative.")

        self._host = host
        self._side = side
        self._preferred_width = width
        self._animation_duration = animation_duration
        self._blocks: tuple[SideOverlayBlock, ...] = ()
        self._pending_replies: dict[QNetworkReply, _SideOverlayImageLabel] = {}
        self._state = "closed"
        self._scrim_opacity = 0.0

        self.setObjectName("qtSideOverlay")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._host.installEventFilter(self)

        self._network_manager = QNetworkAccessManager(self)
        self._panel = self._make_panel(header_title)
        self._slide_animation = QPropertyAnimation(self._panel, b"pos", self)
        self._scrim_animation = QPropertyAnimation(self, b"scrimOpacity", self)
        self._configure_animations()
        self._escape_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        self._escape_shortcut.setContext(Qt.ShortcutContext.WindowShortcut)
        self._escape_shortcut.activated.connect(self.dismiss)

        self.set_blocks(blocks)
        self.hide()

    def blocks(self) -> tuple[SideOverlayBlock, ...]:
        """Return the document blocks in their rendered order."""
        return self._blocks

    def set_blocks(self, blocks: tuple[SideOverlayBlock, ...] | list[SideOverlayBlock]) -> None:
        """Replace the scrollable document content with ordered *blocks*."""
        materialized = tuple(blocks)
        for block in materialized:
            if not isinstance(
                block,
                (SideOverlayTitle, SideOverlaySubtitle, SideOverlayText, SideOverlaySeparator, SideOverlayImage),
            ):
                raise TypeError(f"Unsupported side-overlay block: {type(block).__name__}.")

        self._cancel_pending_requests()
        self._clear_content()
        self._blocks = materialized
        for block in self._blocks:
            self._add_block(block)
        self._content_layout.addStretch()

    def open(self) -> None:
        """Show the scrim and slide the panel into the host window."""
        if self._state in {"opening", "open"}:
            self.raise_()
            return

        self._stop_animations()
        self._sync_host_geometry()
        self._state = "opening"
        self.show()
        self.raise_()
        self._panel.setGeometry(self._panel_geometry())
        self._panel.move(self._hidden_panel_position())
        self.set_scrim_opacity(0.0)
        self.setFocus(Qt.FocusReason.ActiveWindowFocusReason)

        self._slide_animation.setStartValue(self._hidden_panel_position())
        self._slide_animation.setEndValue(self._panel_geometry().topLeft())
        self._scrim_animation.setStartValue(0.0)
        self._scrim_animation.setEndValue(self._SCRIM_OPACITY)
        self._slide_animation.finished.connect(self._on_open_finished)
        self._slide_animation.start()
        self._scrim_animation.start()

    def dismiss(self) -> None:
        """Slide the panel away and hide the modal scrim."""
        if self._state in {"closed", "closing"}:
            return

        self._stop_animations()
        self._state = "closing"
        self._slide_animation.setStartValue(self._panel.pos())
        self._slide_animation.setEndValue(self._hidden_panel_position())
        self._scrim_animation.setStartValue(self._scrim_opacity)
        self._scrim_animation.setEndValue(0.0)
        self._slide_animation.finished.connect(self._on_dismiss_finished)
        self._slide_animation.start()
        self._scrim_animation.start()

    def get_scrim_opacity(self) -> float:
        """Return the current painted opacity of the modal scrim."""
        return self._scrim_opacity

    def set_scrim_opacity(self, opacity: float) -> None:
        """Set the painted opacity of the modal scrim."""
        self._scrim_opacity = max(0.0, min(float(opacity), self._SCRIM_OPACITY))
        self.update()

    scrimOpacity = Property(float, fget=get_scrim_opacity, fset=set_scrim_opacity)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # type: ignore[override]
        """Keep the overlay aligned with its top-level host widget."""
        if watched is self._host:
            if event.type() in (QEvent.Type.Resize, QEvent.Type.Move, QEvent.Type.LayoutRequest):
                self._sync_host_geometry()
            elif event.type() in (QEvent.Type.Hide, QEvent.Type.HideToParent):
                self.hide()
            elif event.type() in (QEvent.Type.Show, QEvent.Type.ShowToParent) and self._state != "closed":
                self.show()
                self.raise_()
        return super().eventFilter(watched, event)

    def resizeEvent(self, event: QResizeEvent) -> None:  # type: ignore[override]
        """Resize the panel with its host while preserving its selected edge."""
        panel = getattr(self, "_panel", None)
        if panel is not None:
            panel.setGeometry(self._panel_geometry())
        super().resizeEvent(event)

    def paintEvent(self, event: QPaintEvent) -> None:  # type: ignore[override]
        """Paint the modal scrim behind the side panel."""
        from qtpy.QtGui import QColor, QPainter

        painter = QPainter(self)
        color = QColor(0, 0, 0)
        color.setAlphaF(self._scrim_opacity)
        painter.fillRect(self.rect(), color)
        del event

    def mousePressEvent(self, event: QMouseEvent) -> None:  # type: ignore[override]
        """Consume presses on the scrim to keep the overlay modal."""
        event.accept()

    def keyPressEvent(self, event: QKeyEvent) -> None:  # type: ignore[override]
        """Dismiss the panel when Escape is delivered directly to the overlay."""
        if event.key() == Qt.Key.Key_Escape:
            self.dismiss()
            event.accept()
            return
        super().keyPressEvent(event)

    def closeEvent(self, event) -> None:  # type: ignore[override]
        """Detach from the host and cancel outstanding image requests."""
        self._cancel_pending_requests()
        self._host.removeEventFilter(self)
        super().closeEvent(event)

    def _make_panel(self, header_title: str) -> QFrame:
        """Create the fixed-header panel and its scrollable document body."""
        panel = QFrame(self)
        panel.setObjectName("qtSideOverlayPanel")
        panel.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        _apply_elevated_card_effect(panel)

        background = QtStyler.background().name()
        secondary = QtStyler.secondary().name()
        text = QtStyler.text().name()
        panel.setStyleSheet(
            "QFrame#qtSideOverlayPanel {"
            f"background: {background}; border: 1px solid {secondary};"
            "border-radius: 14px; }"
            "QLabel#qtSideOverlayHeaderTitle { font-weight: bold; }"
            "QLabel#qtSideOverlayTitle { font-weight: bold; }"
            "QLabel#qtSideOverlaySubtitle { font-weight: bold; }"
            "QFrame#qtSideOverlayHeader { border-bottom: 1px solid "
            f"{secondary}; }}"
            "QToolButton#qtSideOverlayClose { border: none; border-radius: 14px;"
            f" color: {text}; padding: 4px; }}"
            f"QToolButton#qtSideOverlayClose:hover {{ background: {secondary}; }}"
            "QScrollArea#qtSideOverlayScroll { border: none; background: transparent; }"
        )

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QFrame(panel)
        header.setObjectName("qtSideOverlayHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(24, 16, 16, 16)
        self.header_title_label = hp.make_label(
            header, header_title, bold=True, font_size=15, object_name="qtSideOverlayHeaderTitle"
        )
        self.close_button = QToolButton(header)
        self.close_button.setObjectName("qtSideOverlayClose")
        self.close_button.setToolTip("Close")
        self.close_button.setIcon(header.style().standardIcon(QStyle.StandardPixmap.SP_TitleBarCloseButton))
        self.close_button.clicked.connect(self.dismiss)
        header_layout.addWidget(self.header_title_label, 1)
        header_layout.addWidget(self.close_button)
        layout.addWidget(header)

        self.scroll_area = QScrollArea(panel)
        self.scroll_area.setObjectName("qtSideOverlayScroll")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._document = QWidget(self.scroll_area)
        self._document.setObjectName("qtSideOverlayDocument")
        self._content_layout = QVBoxLayout(self._document)
        self._content_layout.setContentsMargins(28, 26, 28, 28)
        self._content_layout.setSpacing(16)
        self.scroll_area.setWidget(self._document)
        layout.addWidget(self.scroll_area, 1)
        return panel

    def _add_block(self, block: SideOverlayBlock) -> None:
        """Create and append one document widget for *block*."""
        if isinstance(block, SideOverlayTitle):
            label = hp.make_label(
                self._document,
                block.text,
                bold=True,
                wrap=True,
                font_size=24,
                object_name="qtSideOverlayTitle",
            )
            self._content_layout.addWidget(label)
        elif isinstance(block, SideOverlaySubtitle):
            label = hp.make_label(
                self._document,
                block.text,
                bold=True,
                wrap=True,
                font_size=17,
                object_name="qtSideOverlaySubtitle",
            )
            self._content_layout.addWidget(label)
        elif isinstance(block, SideOverlayText):
            label = hp.make_label(self._document, block.text, wrap=True, selectable=True)
            label.setObjectName("qtSideOverlayText")
            self._content_layout.addWidget(label)
        elif isinstance(block, SideOverlaySeparator):
            separator = QFrame(self._document)
            separator.setFrameShape(QFrame.Shape.HLine)
            separator.setFrameShadow(QFrame.Shadow.Sunken)
            separator.setObjectName("qtSideOverlaySeparator")
            self._content_layout.addWidget(separator)
        else:
            image_label = _SideOverlayImageLabel(self._document)
            self._content_layout.addWidget(image_label)
            self._load_image(block.source, image_label)

    def _load_image(self, source: str | Path | QImage | QPixmap, label: _SideOverlayImageLabel) -> None:
        """Load an image immediately or request a remote image asynchronously."""
        if isinstance(source, QPixmap):
            self._set_or_remove_image(label, source, "QPixmap")
            return
        if isinstance(source, QImage):
            self._set_or_remove_image(label, QPixmap.fromImage(source), "QImage")
            return

        source_text = str(source)
        url = QUrl(source_text)
        if url.scheme().lower() in {"http", "https"}:
            reply = self._network_manager.get(QNetworkRequest(url))
            self._pending_replies[reply] = label
            reply.finished.connect(lambda: self._finish_remote_image(reply, source_text))
            return
        self._set_or_remove_image(label, QPixmap(source_text), source_text)

    def _finish_remote_image(self, reply: QNetworkReply, source: str) -> None:
        """Decode a completed network reply if its image slot is still current."""
        label = self._pending_replies.pop(reply, None)
        try:
            error = reply.error()
            no_error = QNetworkReply.NetworkError.NoError
            error_value = getattr(error, "value", error)
            no_error_value = getattr(no_error, "value", no_error)
            if label is None or error_value != no_error_value:
                if label is not None:
                    self._remove_image(label, source)
                return
            pixmap = QPixmap()
            if not pixmap.loadFromData(reply.readAll()):
                self._remove_image(label, source)
                return
            label.set_source_pixmap(pixmap)
        finally:
            reply.deleteLater()

    def _set_or_remove_image(self, label: _SideOverlayImageLabel, pixmap: QPixmap, source: str) -> None:
        """Display a valid image or remove its reserved document slot."""
        if pixmap.isNull():
            self._remove_image(label, source)
            return
        label.set_source_pixmap(pixmap)

    def _remove_image(self, label: _SideOverlayImageLabel, source: str) -> None:
        """Remove an unavailable image from the document and notify callers."""
        self._content_layout.removeWidget(label)
        label.hide()
        label.setParent(None)
        label.deleteLater()
        self.evt_image_failed.emit(source)

    def _clear_content(self) -> None:
        """Delete every widget in the previous scrollable document."""
        while self._content_layout.count():
            item = self._content_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

    def _cancel_pending_requests(self) -> None:
        """Abort image loads that belong to outdated document content."""
        for reply in tuple(self._pending_replies):
            reply.abort()
            reply.deleteLater()
        self._pending_replies.clear()

    def _configure_animations(self) -> None:
        """Configure both panel and scrim animations consistently."""
        for animation in (self._slide_animation, self._scrim_animation):
            animation.setDuration(self._animation_duration)
            animation.setEasingCurve(QEasingCurve.Type.OutCubic)

    def _stop_animations(self) -> None:
        """Stop current animations and clear any one-shot completion callback."""
        self._slide_animation.stop()
        self._scrim_animation.stop()
        with suppress(TypeError):
            self._slide_animation.finished.disconnect()

    def _on_open_finished(self) -> None:
        """Finalize a completed opening transition."""
        if self._state != "opening":
            return
        self._state = "open"
        self.evt_opened.emit()

    def _on_dismiss_finished(self) -> None:
        """Hide the root after a completed dismissal transition."""
        if self._state != "closing":
            return
        self._state = "closed"
        self.hide()
        self.evt_closed.emit()

    def _sync_host_geometry(self) -> None:
        """Cover the complete host and position the panel at its visible edge."""
        self.setGeometry(self._host.rect())
        if self._state == "open":
            self._panel.setGeometry(self._panel_geometry())

    def _panel_geometry(self) -> QRect:
        """Return the panel's visible geometry in overlay coordinates."""
        panel_width = min(self._preferred_width, self.width())
        x = 0 if self._side == "left" else self.width() - panel_width
        return self.rect().adjusted(x, 0, -(self.width() - x - panel_width), 0)

    def _hidden_panel_position(self) -> QPoint:
        """Return the off-screen panel position for the selected entrance edge."""
        if self._side == "left":
            return QPoint(-self._panel.width(), 0)
        return QPoint(self.width(), 0)
