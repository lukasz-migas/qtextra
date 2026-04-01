"""Rich tooltip widget.

A floating tooltip that renders rich HTML content, displays images and animated
GIFs, contains clickable hyperlinks, and supports action buttons.  Inspired by
the documentation popups found in JetBrains IDEs (e.g. PyCharm).
"""

from __future__ import annotations

import contextlib
import re
import typing as ty
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field
from qtpy.QtCore import QEvent, QPoint, QPropertyAnimation, QSize, Qt, QTimer, Signal
from qtpy.QtGui import QColor, QCursor, QMovie, QPixmap
from qtpy.QtWidgets import (
    QApplication,
    QFrame,
    QGraphicsDropShadowEffect,
    QLabel,
    QWidget,
)

import qtextra.helpers as hp
from qtextra.config import THEMES, is_dark

#: Grace period (ms) before closing on mouse-leave or focus loss.
_DISMISS_DELAY_MS: int = 400


class RichToolTipAction(BaseModel):
    """A clickable button rendered in the tooltip footer.

    Parameters
    ----------
    label : str
        Button text.
    callback : Callable | None
        Function invoked when the button is clicked.
    object_name : str
        Qt object name applied to the button (for stylesheet targeting).
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    label: str
    callback: ty.Callable[[], ty.Any] | None = None
    object_name: str = ""


class RichToolTipData(BaseModel):
    """Declarative data model for a rich tooltip.

    All visual properties of the tooltip can be specified via this model
    and then passed to :meth:`QtRichToolTip.show_tooltip` or used to
    construct a :class:`_RichToolTipContent` directly.

    Parameters
    ----------
    title : str
        Bold header text.
    content : str
        Rich HTML body.  Supports ``<b>``, ``<i>``, ``<code>``,
        ``<a href="...">``, ``<br>``, ``<ul>``/``<li>``, etc.
    image : str | None
        Path to an image or animated GIF shown above the text body.
    icon : str | None
        QtAwesome icon name shown next to the title.
    shortcut : str
        Keyboard shortcut badge rendered to the right of the title.
    actions : list[RichToolTipAction]
        Buttons rendered in a footer bar below a separator.
    duration : int
        Auto-hide delay in ms.  ``-1`` means persistent (dismiss on
        mouse-leave or focus loss).
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    title: str = ""
    content: str = ""
    image: str | None = None
    icon: str | None = None
    shortcut: str = ""
    actions: list[RichToolTipAction] = Field(default_factory=list)
    duration: int = -1


class _MediaWidget(QLabel):
    """Display an image or animated GIF, scaled to fit the tooltip width."""

    _MAX_SIZE = QSize(480, 280)

    def __init__(self, source: str | QPixmap | None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setObjectName("richMedia")
        self._movie: QMovie | None = None

        if source is None:
            self.hide()
            return

        if isinstance(source, QPixmap):
            self._set_pixmap(source)
        elif isinstance(source, str) and Path(source).is_file():
            suffix = Path(source).suffix.lower()
            if suffix == ".gif":
                self._movie = QMovie(source)
                self._movie.setScaledSize(self._MAX_SIZE)
                self.setMovie(self._movie)
                self._movie.start()
            else:
                self._set_pixmap(QPixmap(source))
        else:
            self.hide()

    def _set_pixmap(self, pix: QPixmap) -> None:
        """Scale and display *pix*, or hide when null."""
        if pix.isNull():
            self.hide()
            return
        scaled = pix.scaled(
            self._MAX_SIZE,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.setPixmap(scaled)

    def stop(self) -> None:
        """Stop the GIF animation (if any)."""
        if self._movie is not None:
            self._movie.stop()


class _ContentLabel(QLabel):
    """A QLabel configured for rich HTML rendering with clickable links."""

    def __init__(self, html: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setTextFormat(Qt.TextFormat.RichText)
        self.setWordWrap(True)
        self.setOpenExternalLinks(True)
        self.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextBrowserInteraction
            | Qt.TextInteractionFlag.LinksAccessibleByMouse
            | Qt.TextInteractionFlag.TextSelectableByMouse
            | Qt.TextInteractionFlag.TextSelectableByKeyboard
        )
        self.setText(html)


class _RichToolTipContent(QFrame):
    """Inner content frame rendered inside the tooltip bubble.

    Arranges an optional image, a header row (icon + title + shortcut),
    a rich-text body, and an optional footer with action buttons.
    """

    evt_action_clicked = Signal(str)  # emits action label
    evt_link_clicked = Signal(str)  # emits URL

    _MAX_WIDTH: int = 520
    _MIN_WIDTH: int = 200

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
        self._media: _MediaWidget | None = None
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
        root = hp.make_v_layout(spacing=0, margin=0, parent=self)

        if image is not None:
            self._media = _MediaWidget(image, self)
            if not self._media.isHidden():
                root.addWidget(self._media)

        body = hp.make_v_layout(spacing=6, margin=(12, 10, 12, 10))

        if title or icon:
            self._build_header(body, title, icon, shortcut)

        if content:
            content_lbl = _ContentLabel(content, self)
            content_lbl.setObjectName("richToolTipBody")
            content_lbl.linkActivated.connect(self.evt_link_clicked)
            body.addWidget(content_lbl)

        root.addLayout(body)

        if actions:
            self._build_actions(root, actions)

        self.setMinimumWidth(self._MIN_WIDTH)
        self.setMaximumWidth(self._MAX_WIDTH)

    def _build_header(
        self,
        parent_layout,
        title: str,
        icon: str | None,
        shortcut: str,
    ) -> None:
        """Build the header row: icon + title + shortcut badge."""
        header = hp.make_h_layout(spacing=6)

        if icon:
            icon_lbl = hp.make_qta_label(self, icon, small=True)
            icon_lbl.setScaledContents(True)
            header.addWidget(icon_lbl, 0, Qt.AlignmentFlag.AlignVCenter)

        if title:
            title_lbl = hp.make_label(self, title, object_name="richToolTipTitle", bold=True, wrap=True)
            font = title_lbl.font()
            font.setPointSize(font.pointSize() + 1)
            title_lbl.setFont(font)
            header.addWidget(title_lbl, 1)

        if shortcut:
            sc_lbl = hp.make_label(self, shortcut, object_name="richToolTipShortcut")
            header.addWidget(sc_lbl, 0, Qt.AlignmentFlag.AlignVCenter)

        parent_layout.addLayout(header)

    def _build_actions(
        self,
        parent_layout,
        actions: list[RichToolTipAction],
    ) -> None:
        """Build the separator and action-button footer."""
        sep = QFrame(self)
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setObjectName("richToolTipSep")
        parent_layout.addWidget(sep)

        btn_bar = hp.make_h_layout(spacing=6, margin=(10, 6, 10, 8))
        for action in actions:
            btn = hp.make_btn(
                self,
                action.label,
                object_name=action.object_name or "richToolTipAction",
                func=lambda _c=False, a=action: self._on_action(a),
            )
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_bar.addWidget(btn)
        btn_bar.addStretch()
        parent_layout.addLayout(btn_bar)

    def _on_action(self, action: RichToolTipAction) -> None:
        self.evt_action_clicked.emit(action.label)
        if action.callback is not None:
            action.callback()

    def cleanup(self) -> None:
        """Stop media playback."""
        if self._media is not None:
            self._media.stop()


class QtRichToolTip(QWidget):
    """Floating, PyCharm-style rich tooltip.

    Shows near a *target* widget or at the cursor position.  Supports:

    * Rich HTML content with clickable links
    * Images and animated GIFs
    * A title with an optional icon and keyboard-shortcut badge
    * Action buttons in a footer bar
    * Auto-dismiss after a timeout, or persistent until the mouse leaves

    Parameters
    ----------
    content_widget : _RichToolTipContent
        Pre-built content frame.
    target : QWidget | None
        Widget to anchor the tooltip near.  When *None* the tooltip
        appears at the current cursor position.
    duration : int
        Auto-hide delay in milliseconds.  Use ``-1`` for persistent
        (dismiss on mouse-leave / focus loss).
    parent : QWidget | None
        Parent widget (usually the application's top-level window).
    """

    evt_closed = Signal()

    _active_instance: ty.ClassVar[QtRichToolTip | None] = None

    def __init__(
        self,
        content_widget: _RichToolTipContent,
        target: QWidget | None = None,
        duration: int = -1,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._target = target
        self._duration = duration
        self._content = content_widget
        self._hovered: bool = False
        self._sticky_after_hover: bool = False
        self._pointer_interacting: bool = False

        # window flags
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setWindowFlags(
            Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowDoesNotAcceptFocus,
        )
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        # layout
        layout = hp.make_v_layout(margin=(10, 8, 10, 12), parent=self)

        self._bubble = QFrame(self)
        self._bubble.setObjectName("richToolTipBubble")
        bubble_layout = hp.make_v_layout(spacing=0, margin=0, parent=self._bubble)
        bubble_layout.addWidget(self._content)
        layout.addWidget(self._bubble)

        # effects
        self._apply_shadow()
        self._opacity_anim = QPropertyAnimation(self, b"windowOpacity", self)

        # timers
        self._dismiss_timer = QTimer(self)
        self._dismiss_timer.setSingleShot(True)
        self._dismiss_timer.timeout.connect(self._fade_out)

        self._leave_timer = QTimer(self)
        self._leave_timer.setSingleShot(True)
        self._leave_timer.setInterval(_DISMISS_DELAY_MS)
        self._leave_timer.timeout.connect(self._fade_out)

        # event filters
        if parent and parent.window():
            parent.window().installEventFilter(self)
        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)

        self._install_interaction_filters()
        self._apply_theme()

    def _apply_theme(self) -> None:
        """Apply the current theme stylesheet to this top-level popup."""
        THEMES.set_theme_stylesheet(self)

    def _cancel_dismiss(self) -> None:
        """Stop any pending auto-dismiss or leave-dismiss."""
        self._dismiss_timer.stop()
        self._leave_timer.stop()

    def _set_hovered(self, hovered: bool) -> None:
        """Update hover state and keep the tooltip alive after first entry."""
        self._hovered = hovered
        if hovered:
            self._sticky_after_hover = True
            self._cancel_dismiss()

    def _refresh_hover_state(self) -> bool:
        """Recompute hover state from the current cursor position."""
        hovered = self._cursor_inside_tooltip()
        self._hovered = hovered
        return hovered

    def _schedule_leave_dismiss(self) -> None:
        """Dismiss after the pointer leaves and the user stops interacting."""
        if self._hovered or self._pointer_interacting:
            return
        self._leave_timer.start()

    def _cursor_inside_tooltip(self) -> bool:
        """Return whether the global cursor is currently inside the tooltip."""
        return self.frameGeometry().contains(QCursor.pos())

    def _install_interaction_filters(self) -> None:
        """Track pointer activity on the tooltip and all child widgets."""
        self.installEventFilter(self)
        for widget in self.findChildren(QWidget):
            widget.installEventFilter(self)

    def _is_tooltip_widget(self, obj: object) -> bool:
        """Return whether *obj* is this tooltip or one of its descendants."""
        return isinstance(obj, QWidget) and (obj is self or self.isAncestorOf(obj))

    def _on_pointer_enter(self) -> None:
        """Keep the tooltip open while the pointer is inside it."""
        self._set_hovered(True)

    def _on_pointer_leave(self) -> None:
        """Dismiss only after the pointer has actually left the tooltip."""
        if not self._refresh_hover_state():
            self._schedule_leave_dismiss()

    def _set_pointer_interacting(self, interacting: bool) -> None:
        """Track pointer-driven interactions such as selecting or right-clicking."""
        self._pointer_interacting = interacting
        if interacting:
            self._sticky_after_hover = True
            self._cancel_dismiss()
        elif not self._refresh_hover_state():
            self._schedule_leave_dismiss()

    def _apply_shadow(self) -> None:
        """Apply a drop-shadow effect to the bubble frame."""
        shadow = QGraphicsDropShadowEffect(self._bubble)
        shadow.setBlurRadius(24)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 100 if is_dark() else 50))
        self._bubble.setGraphicsEffect(shadow)

    @staticmethod
    def _code_style() -> str:
        """Return inline CSS for ``<code>`` blocks, theme-aware."""
        if is_dark():
            return "background:#383b40; color:#a9b7c6; padding:2px 5px; border-radius:3px;"
        return "background:#e8eaed; color:#2e2e2e; padding:2px 5px; border-radius:3px;"

    def _inject_code_style(self) -> None:
        """Rewrite ``<code>`` tags in body labels to include theme-aware inline styles."""
        style = self._code_style()
        for lbl in self._content.findChildren(QLabel, "richToolTipBody"):
            html = lbl.text()
            # bare <code> tags
            html = re.sub(r"<code(?!\s+style)([^>]*)>", rf'<code style="{style}"\1>', html)
            # existing <code style="..."> — prepend theme defaults
            html = re.sub(
                r'<code\s+style="([^"]*)"',
                rf'<code style="{style} \1"',
                html,
            )
            lbl.setText(html)

    def showEvent(self, event) -> None:  # noqa: D102
        # singleton — close the previous tooltip
        if QtRichToolTip._active_instance is not None and QtRichToolTip._active_instance is not self:
            QtRichToolTip._active_instance.close()
        QtRichToolTip._active_instance = self

        self._inject_code_style()
        self._position_near_target()
        self.adjustSize()

        # fade in
        self._opacity_anim.stop()
        self._opacity_anim.setDuration(150)
        self._opacity_anim.setStartValue(0.0)
        self._opacity_anim.setEndValue(1.0)
        self._opacity_anim.start()

        if self._duration >= 0 and not self._sticky_after_hover:
            self._dismiss_timer.start(self._duration)

        super().showEvent(event)

    def _fade_out(self) -> None:
        """Start the fade-out animation, unless the mouse is hovering."""
        if self._hovered or self._pointer_interacting:
            return
        self._opacity_anim.stop()
        self._opacity_anim.setDuration(120)
        self._opacity_anim.setStartValue(self.windowOpacity())
        self._opacity_anim.setEndValue(0.0)
        with contextlib.suppress(RuntimeError, TypeError):
            self._opacity_anim.finished.disconnect(self.close)
        self._opacity_anim.finished.connect(self.close)
        self._opacity_anim.start()

    def closeEvent(self, event) -> None:  # noqa: D102
        if QtRichToolTip._active_instance is self:
            QtRichToolTip._active_instance = None
        self._content.cleanup()
        self.evt_closed.emit()
        self.deleteLater()
        super().closeEvent(event)

    def _position_near_target(self) -> None:
        """Place the tooltip below the *target* widget, or at the cursor."""
        if self._target is not None:
            target_rect = self._target.rect()
            global_pos = self._target.mapToGlobal(QPoint(0, target_rect.height()))
        else:
            global_pos = QCursor.pos() + QPoint(12, 16)

        hint = self.sizeHint()
        screen = QApplication.screenAt(global_pos)
        if screen is None:
            screen = QApplication.primaryScreen()
        screen_rect = screen.availableGeometry()

        x = global_pos.x()
        y = global_pos.y() + 4

        # flip upward if it would go off-screen
        if y + hint.height() > screen_rect.bottom():
            if self._target is not None:
                y = self._target.mapToGlobal(QPoint(0, 0)).y() - hint.height() - 4
            else:
                y = global_pos.y() - hint.height() - 20

        # clamp horizontally
        if x + hint.width() > screen_rect.right():
            x = screen_rect.right() - hint.width() - 4
        x = max(screen_rect.left(), x)
        y = max(screen_rect.top(), y)

        self.move(x, y)

    def enterEvent(self, event) -> None:
        """Enter event."""
        self._on_pointer_enter()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        """Leave event."""
        self._on_pointer_leave()
        super().leaveEvent(event)

    def eventFilter(self, obj, event: QEvent) -> bool:
        """Event filter."""
        event_type = event.type()

        # track parent-window geometry changes
        if (
            self.parent()
            and obj is self.parent().window()
            and event_type in (QEvent.Type.Resize, QEvent.Type.Move, QEvent.Type.WindowStateChange)
        ):
            self._position_near_target()

        if self._is_tooltip_widget(obj):
            if event_type in (QEvent.Type.Enter, QEvent.Type.HoverEnter):
                self._on_pointer_enter()
            elif event_type in (QEvent.Type.Leave, QEvent.Type.HoverLeave):
                self._on_pointer_leave()

        if event_type == QEvent.Type.MouseButtonPress and self._cursor_inside_tooltip():
            self._set_pointer_interacting(True)
        elif event_type == QEvent.Type.MouseButtonRelease and self._pointer_interacting:
            self._set_pointer_interacting(False)

        # dismiss when the application loses focus
        if event_type == QEvent.Type.ApplicationDeactivate:
            if not (self._hovered or self._pointer_interacting or self._sticky_after_hover):
                self._schedule_leave_dismiss()
        elif event_type == QEvent.Type.ApplicationActivate and (self._hovered or self._pointer_interacting):
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
        """Create and show a rich tooltip in one call.

        Parameters
        ----------
        title : str
            Bold header text.
        content : str
            Rich HTML body.  Supports ``<b>``, ``<i>``, ``<code>``,
            ``<a href="...">``, ``<br>``, ``<ul>``/``<li>``, etc.
        image : str | QPixmap | None
            Path to an image/GIF or a :class:`QPixmap`, shown above the text.
        icon : str | None
            QtAwesome icon name shown next to the title.
        actions : list[RichToolTipAction] | None
            Buttons rendered in a footer bar.
        shortcut : str
            Keyboard shortcut badge (e.g. ``"Ctrl+Q"``).
        target : QWidget | None
            Anchor widget.  When *None* the tooltip appears at the cursor.
        duration : int
            Auto-hide in ms.  ``-1`` = persistent.
        parent : QWidget | None
            Parent widget.

        Returns
        -------
        QtRichToolTip
            The tooltip instance (already visible).
        """
        view = _RichToolTipContent(
            title=title,
            content=content,
            image=image,
            icon=icon,
            actions=actions,
            shortcut=shortcut,
        )
        return cls._show(view, target=target, duration=duration, parent=parent)

    @classmethod
    def show_from_data(
        cls,
        data: RichToolTipData,
        target: QWidget | None = None,
        parent: QWidget | None = None,
    ) -> QtRichToolTip:
        """Create and show a rich tooltip from a :class:`RichToolTipData` model.

        Parameters
        ----------
        data : RichToolTipData
            Declarative tooltip specification.
        target : QWidget | None
            Anchor widget.
        parent : QWidget | None
            Parent widget.

        Returns
        -------
        QtRichToolTip
            The tooltip instance (already visible).
        """
        view = _RichToolTipContent(
            title=data.title,
            content=data.content,
            image=data.image,
            icon=data.icon,
            actions=data.actions,
            shortcut=data.shortcut,
        )
        return cls._show(view, target=target, duration=data.duration, parent=parent)

    @classmethod
    def _show(
        cls,
        view: _RichToolTipContent,
        target: QWidget | None,
        duration: int,
        parent: QWidget | None,
    ) -> QtRichToolTip:
        """Internal helper — instantiate, show, and return the tooltip."""
        tip = cls(content_widget=view, target=target, duration=duration, parent=parent)
        tip.show()
        return tip

    @classmethod
    def dismiss(cls) -> None:
        """Dismiss the currently active tooltip, if any."""
        if cls._active_instance is not None:
            cls._active_instance.close()


if __name__ == "__main__":  # pragma: no cover

    def _main() -> None:  # type: ignore[no-untyped-def]
        import sys

        from qtextra.utils.dev import qframe

        app, frame, layout = qframe(horz=False)

        def _show_simple() -> None:
            QtRichToolTip.show_tooltip(
                title="Quick Documentation",
                content=(
                    "<b>dict.get</b>(key, default=None)<br><br>"
                    "Return the value for <i>key</i> if <i>key</i> is in the "
                    "dictionary, else <i>default</i>.<br><br>"
                    "<code>d = {'a': 1}; d.get('b', 42)  # returns 42</code>"
                ),
                icon="fa5s.book",
                shortcut="Ctrl+Q",
                target=btn_simple,
                parent=frame,
            )

        btn_simple = hp.make_btn(frame, "Simple Docs Tooltip", func=_show_simple)
        layout.addWidget(btn_simple)

        def _show_rich() -> None:
            QtRichToolTip.show_tooltip(
                title="QtRichToolTip Widget",
                content=(
                    "A <b>PyCharm-inspired</b> tooltip that supports:<br>"
                    "<ul>"
                    "<li>Rich <b>HTML</b> formatting</li>"
                    "<li>Images and animated GIFs</li>"
                    '<li>Clickable <a href="https://doc.qt.io">hyperlinks</a></li>'
                    "<li>Action buttons in a footer</li>"
                    "</ul>"
                    "Use it anywhere you need a polished documentation popup."
                ),
                icon="fa5s.info-circle",
                actions=[
                    RichToolTipAction(label="Learn More", callback=lambda: print("Learn more")),
                    RichToolTipAction(
                        label="View Source", callback=lambda: print("View source"), object_name="success_btn"
                    ),
                ],
                target=btn_rich,
                parent=frame,
            )

        btn_rich = hp.make_btn(frame, "Rich Tooltip + Actions", func=_show_rich)
        layout.addWidget(btn_rich)

        def _show_timed() -> None:
            QtRichToolTip.show_tooltip(
                title="Auto-dismiss",
                content="This tooltip will disappear in <b>3 seconds</b>.",
                icon="fa5s.clock",
                duration=3000,
                target=btn_timed,
                parent=frame,
            )

        btn_timed = hp.make_btn(frame, "Timed Tooltip (3s)", func=_show_timed)
        layout.addWidget(btn_timed)

        def _show_from_model() -> None:
            data = RichToolTipData(
                title="From Model",
                content="Created via <code>RichToolTipData</code> Pydantic model.",
                icon="fa5s.database",
                actions=[RichToolTipAction(label="OK")],
            )
            QtRichToolTip.show_from_data(data, target=btn_model, parent=frame)

        btn_model = hp.make_btn(frame, "From Pydantic Model", func=_show_from_model)
        layout.addWidget(btn_model)

        def _show_cursor() -> None:
            QtRichToolTip.show_tooltip(
                title="Cursor Tooltip",
                content="This tooltip appears at the <b>cursor position</b> rather than anchored to a widget.",
                icon="fa5s.mouse-pointer",
                duration=4000,
            )

        btn_cursor = hp.make_btn(frame, "Cursor Tooltip", func=_show_cursor)
        layout.addWidget(btn_cursor)

        def _show_signature() -> None:
            QtRichToolTip.show_tooltip(
                title="add_widget",
                content=(
                    "<code>"
                    "def <b>add_widget</b>(<br>"
                    "&nbsp;&nbsp;&nbsp;&nbsp;self,<br>"
                    "&nbsp;&nbsp;&nbsp;&nbsp;name: <i>str</i>,<br>"
                    "&nbsp;&nbsp;&nbsp;&nbsp;tooltip: <i>str</i> = <span style='color:#6a9955;'>\"\"</span>,<br>"
                    "&nbsp;&nbsp;&nbsp;&nbsp;widget: <i>QWidget | None</i> = None,<br>"
                    "&nbsp;&nbsp;&nbsp;&nbsp;location: <i>str</i> = <span style='color:#6a9955;'>\"top\"</span>,<br>"
                    ") -> <i>QtToolbarPushButton</i>"
                    "</code><br><br>"
                    "Add a toolbar button and optionally bind it to a panel widget.<br><br>"
                    "<b>Parameters:</b><br>"
                    "&nbsp;&nbsp;<code>name</code> \u2013 name of the object used to select the icon<br>"
                    "&nbsp;&nbsp;<code>tooltip</code> \u2013 text for the tooltip information<br>"
                    "&nbsp;&nbsp;<code>widget</code> \u2013 widget inserted into the stack<br>"
                    "&nbsp;&nbsp;<code>location</code> \u2013 <code>top</code> or <code>bottom</code>"
                ),
                icon="fa5s.code",
                shortcut="Ctrl+P",
                actions=[
                    RichToolTipAction(label="View Source", callback=lambda: print("Navigate to source")),
                ],
                target=btn_sig,
                parent=frame,
            )

        btn_sig = hp.make_btn(frame, "Signature Tooltip", func=_show_signature)
        layout.addWidget(btn_sig)

        layout.addStretch()
        frame.setMinimumSize(400, 300)
        frame.show()
        sys.exit(app.exec_())

    _main()
