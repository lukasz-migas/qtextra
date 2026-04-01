"""Rich tooltip widgets with HTML content, media, and footer actions."""

from __future__ import annotations

import typing as ty
from pathlib import Path

from pydantic import BaseModel, ConfigDict
from qtpy.QtCore import QEvent, QPoint, QPropertyAnimation, QSize, Qt, QTimer, Signal
from qtpy.QtGui import QColor, QCursor, QMovie, QPixmap
from qtpy.QtWidgets import (
    QApplication,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

import qtextra.helpers as hp
from qtextra.config import THEMES

_DISMISS_DELAY_MS = 400


class RichToolTipAction(BaseModel):
    """Descriptor for an action button rendered in the tooltip footer."""

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    label: str
    callback: ty.Callable[[], ty.Any] | None = None
    object_name: str = ""

    def __init__(self, label: str = "", /, **data: ty.Any) -> None:
        if label:
            data.setdefault("label", label)
        super().__init__(**data)


class _MediaLabel(QLabel):
    """Display a static image or animated GIF inside the tooltip."""

    MAX_SIZE = QSize(480, 280)

    def __init__(self, source: str | QPixmap | None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._movie: QMovie | None = None
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setObjectName("richToolTipMedia")

        if source is None:
            self.hide()
            return

        if isinstance(source, QPixmap):
            self._set_pixmap(source)
            return

        path = Path(source)
        if not path.is_file():
            self.hide()
            return

        if path.suffix.lower() == ".gif":
            self._movie = QMovie(str(path))
            self._movie.setScaledSize(self.MAX_SIZE)
            self.setMovie(self._movie)
            self._movie.start()
            return

        self._set_pixmap(QPixmap(str(path)))

    def _set_pixmap(self, pixmap: QPixmap) -> None:
        if pixmap.isNull():
            self.hide()
            return
        self.setPixmap(
            pixmap.scaled(
                self.MAX_SIZE,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    def cleanup(self) -> None:
        """Stop any running movie before the tooltip is destroyed."""
        if self._movie is not None:
            self._movie.stop()


class _RichToolTipContent(QFrame):
    """Inner rich tooltip content area."""

    evt_action_clicked = Signal(str)
    evt_link_clicked = Signal(str)

    MIN_WIDTH = 220
    MAX_WIDTH = 520

    def __init__(
        self,
        title: str = "",
        content: str = "",
        image: str | QPixmap | None = None,
        icon: str | None = None,
        actions: list[RichToolTipAction] | None = None,
        shortcut: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("richToolTipContent")
        self._media: _MediaLabel | None = None
        self._content_label: QLabel | None = None
        self._build(title, content, image, icon, actions or [], shortcut)

    def _build(
        self,
        title: str,
        content: str,
        image: str | QPixmap | None,
        icon: str | None,
        actions: list[RichToolTipAction],
        shortcut: str,
    ) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._media = _MediaLabel(image, self)
        if not self._media.isHidden():
            root.addWidget(self._media)

        body = QVBoxLayout()
        body.setContentsMargins(12, 10, 12, 10)
        body.setSpacing(6)

        if title or icon or shortcut:
            header = QHBoxLayout()
            header.setContentsMargins(0, 0, 0, 0)
            header.setSpacing(6)

            if icon:
                icon_label = hp.make_qta_label(self, icon)
                icon_label.setObjectName("richToolTipIcon")
                icon_label.setMinimumSize(16, 16)
                icon_label.setMaximumSize(16, 16)
                header.addWidget(icon_label, 0, Qt.AlignmentFlag.AlignVCenter)

            if title:
                title_label = QLabel(title, self)
                title_label.setObjectName("richToolTipTitle")
                title_label.setWordWrap(True)
                header.addWidget(title_label, 1)

            if shortcut:
                shortcut_label = QLabel(shortcut, self)
                shortcut_label.setObjectName("richToolTipShortcut")
                header.addWidget(shortcut_label, 0, Qt.AlignmentFlag.AlignVCenter)

            body.addLayout(header)

        if content:
            self._content_label = QLabel(self)
            self._content_label.setObjectName("richToolTipBody")
            self._content_label.setTextFormat(Qt.TextFormat.RichText)
            self._content_label.setWordWrap(True)
            self._content_label.setOpenExternalLinks(True)
            self._content_label.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextBrowserInteraction | Qt.TextInteractionFlag.LinksAccessibleByMouse
            )
            self._content_label.setText(content)
            self._content_label.linkActivated.connect(self.evt_link_clicked)
            body.addWidget(self._content_label)

        root.addLayout(body)

        if actions:
            separator = QFrame(self)
            separator.setObjectName("richToolTipSeparator")
            separator.setFrameShape(QFrame.Shape.HLine)
            root.addWidget(separator)

            footer = QHBoxLayout()
            footer.setContentsMargins(10, 6, 10, 8)
            footer.setSpacing(6)
            for action in actions:
                button = hp.make_btn(
                    self,
                    action.label,
                    object_name=action.object_name or "richToolTipAction",
                    func=lambda _checked=False, current=action: self._on_action(current),
                )
                button.setCursor(Qt.CursorShape.PointingHandCursor)
                footer.addWidget(button)
            footer.addStretch(1)
            root.addLayout(footer)

        self.setMinimumWidth(self.MIN_WIDTH)
        self.setMaximumWidth(self.MAX_WIDTH)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)

    def _on_action(self, action: RichToolTipAction) -> None:
        self.evt_action_clicked.emit(action.label)
        if action.callback is not None:
            action.callback()

    def cleanup(self) -> None:
        """Release media resources before the tooltip is deleted."""
        if self._media is not None:
            self._media.cleanup()


class QtRichToolTip(QWidget):
    """A floating rich tooltip with HTML content, media, and footer actions."""

    evt_closed = Signal()
    evt_action_clicked = Signal(str)
    evt_link_clicked = Signal(str)

    _active_instance: ty.ClassVar[QtRichToolTip | None] = None

    def __init__(
        self,
        title: str = "",
        content: str = "",
        image: str | QPixmap | None = None,
        icon: str | None = None,
        actions: list[RichToolTipAction] | None = None,
        shortcut: str = "",
        target: QWidget | None = None,
        duration: int = -1,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._target = target
        self._duration = duration
        self._hovered = False
        self._window_filter_target = parent.window() if parent and parent.window() else None

        self._content = _RichToolTipContent(
            title=title,
            content=content,
            image=image,
            icon=icon,
            actions=actions,
            shortcut=shortcut,
            parent=self,
        )
        self._content.evt_action_clicked.connect(self.evt_action_clicked)
        self._content.evt_link_clicked.connect(self.evt_link_clicked)

        self.setObjectName("QtRichToolTip")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setWindowFlags(
            Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowDoesNotAcceptFocus
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 12)

        self._bubble = QFrame(self)
        self._bubble.setObjectName("richToolTipBubble")
        bubble_layout = QVBoxLayout(self._bubble)
        bubble_layout.setContentsMargins(0, 0, 0, 0)
        bubble_layout.setSpacing(0)
        bubble_layout.addWidget(self._content)
        layout.addWidget(self._bubble)

        self._apply_shadow()

        self._opacity_anim = QPropertyAnimation(self, b"windowOpacity", self)
        self._opacity_anim.finished.connect(self._on_animation_finished)
        self._closing = False

        self._dismiss_timer = QTimer(self)
        self._dismiss_timer.setSingleShot(True)
        self._dismiss_timer.timeout.connect(self._fade_out)

        self._leave_timer = QTimer(self)
        self._leave_timer.setSingleShot(True)
        self._leave_timer.setInterval(_DISMISS_DELAY_MS)
        self._leave_timer.timeout.connect(self._fade_out)

        if self._window_filter_target is not None:
            self._window_filter_target.installEventFilter(self)
        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)

    def _apply_shadow(self) -> None:
        shadow = QGraphicsDropShadowEffect(self._bubble)
        shadow.setBlurRadius(24)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 100 if THEMES.is_dark else 50))
        self._bubble.setGraphicsEffect(shadow)

    def showEvent(self, event) -> None:  # type: ignore[override]
        """Show event."""
        if QtRichToolTip._active_instance is not None and QtRichToolTip._active_instance is not self:
            QtRichToolTip._active_instance.close()
        QtRichToolTip._active_instance = self

        self._position_near_target()
        self.adjustSize()
        self._opacity_anim.stop()
        self._closing = False
        self._opacity_anim.setDuration(150)
        self._opacity_anim.setStartValue(0.0)
        self._opacity_anim.setEndValue(1.0)
        self._opacity_anim.start()

        if self._duration >= 0:
            self._dismiss_timer.start(self._duration)

        super().showEvent(event)

    def closeEvent(self, event) -> None:  # type: ignore[override]
        """Close event."""
        if QtRichToolTip._active_instance is self:
            QtRichToolTip._active_instance = None

        if self._window_filter_target is not None:
            self._window_filter_target.removeEventFilter(self)
        app = QApplication.instance()
        if app is not None:
            app.removeEventFilter(self)

        self._content.cleanup()
        self.evt_closed.emit()
        self.deleteLater()
        super().closeEvent(event)

    def _on_animation_finished(self) -> None:
        if self._closing:
            self.close()

    def _fade_out(self) -> None:
        if self._hovered:
            return
        self._opacity_anim.stop()
        self._closing = True
        self._opacity_anim.setDuration(120)
        self._opacity_anim.setStartValue(self.windowOpacity())
        self._opacity_anim.setEndValue(0.0)
        self._opacity_anim.start()

    def _position_near_target(self) -> None:
        if self._target is not None:
            global_pos = self._target.mapToGlobal(QPoint(0, self._target.rect().height()))
        else:
            global_pos = QCursor.pos() + QPoint(12, 16)

        hint = self.sizeHint()
        screen = QApplication.screenAt(global_pos) or QApplication.primaryScreen()
        if screen is None:
            return
        screen_rect = screen.availableGeometry()

        x = global_pos.x()
        y = global_pos.y() + 4

        if y + hint.height() > screen_rect.bottom():
            if self._target is not None:
                y = self._target.mapToGlobal(QPoint(0, 0)).y() - hint.height() - 4
            else:
                y = global_pos.y() - hint.height() - 20

        if x + hint.width() > screen_rect.right():
            x = screen_rect.right() - hint.width() - 4

        self.move(max(screen_rect.left(), x), max(screen_rect.top(), y))

    def enterEvent(self, event) -> None:  # type: ignore[override]
        """Enter event."""
        self._hovered = True
        self._leave_timer.stop()
        self._dismiss_timer.stop()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # type: ignore[override]
        """Leave event."""
        self._hovered = False
        self._leave_timer.start()
        super().leaveEvent(event)

    def eventFilter(self, obj, event: QEvent) -> bool:  # type: ignore[override]
        """Event filter."""
        if self._window_filter_target is not None and obj is self._window_filter_target:  # noqa: SIM102
            if event.type() in (QEvent.Type.Resize, QEvent.Type.Move, QEvent.Type.WindowStateChange):
                self._position_near_target()
        if event.type() == QEvent.Type.ApplicationDeactivate:
            self._leave_timer.start()
        elif event.type() == QEvent.Type.ApplicationActivate and self._hovered:
            self._leave_timer.stop()

        return super().eventFilter(obj, event)

    @classmethod
    def show_tooltip(
        cls,
        title: str = "",
        content: str = "",
        image: str | QPixmap | None = None,
        icon: str | None = None,
        actions: list[RichToolTipAction] | None = None,
        shortcut: str = "",
        target: QWidget | None = None,
        duration: int = -1,
        parent: QWidget | None = None,
    ) -> QtRichToolTip:
        """Create and show a rich tooltip in one call."""
        tooltip = cls(
            title=title,
            content=content,
            image=image,
            icon=icon,
            actions=actions,
            shortcut=shortcut,
            target=target,
            duration=duration,
            parent=parent,
        )
        tooltip.show()
        return tooltip
