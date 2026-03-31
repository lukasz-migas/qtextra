"""Overlay widgets that attach floating labels and messages to another widget."""

from __future__ import annotations

import sys
from contextlib import suppress
from typing import Callable

from qtpy.QtCore import QEvent, QPoint, QRect, QSize, Qt, Signal, Slot
from qtpy.QtGui import QPainter, QPaintEvent
from qtpy.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy, QStyle, QStyleOption, QVBoxLayout, QWidget

import qtextra.helpers as hp
from qtextra.widgets.qt_label_icon import QtIconLabel


class QtOverlay(QWidget):
    """A widget positioned on top of another widget."""

    Y_OFFSET: int = 10

    def __init__(
        self,
        parent: QWidget | None = None,
        alignment: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignCenter,
        widget: QWidget | None = None,
        **kwargs,
    ):
        super().__init__(parent, **kwargs)
        self.setContentsMargins(0, 0, 0, 0)
        self._alignment = alignment
        self._widget: QWidget | None = None
        if widget is not None:
            self.set_widget(widget)

    def set_widget(self, widget: QWidget | None) -> None:
        """Attach the overlay to a widget and track its geometry."""
        if widget is self._widget:
            if widget is not None:
                self._relayout()
            return

        if self._widget is not None:
            self._widget.removeEventFilter(self)
            with suppress(TypeError, RuntimeError):
                self._widget.destroyed.disconnect(self._on_destroyed)

        self._widget = widget

        if self._widget is None:
            self.hide()
            return

        self._widget.installEventFilter(self)
        self._widget.destroyed.connect(self._on_destroyed)
        self._sync_to_anchor()
        self._relayout()

    def attach_to(self, widget: QWidget | None) -> None:
        """Attach the overlay to a widget."""
        self.set_widget(widget)

    def widget(self) -> QWidget | None:
        """Return the widget the overlay is attached to."""
        return self._widget

    def setAlignment(self, alignment: Qt.AlignmentFlag) -> None:
        """Set overlay alignment."""
        if self._alignment == alignment:
            return
        self._alignment = alignment
        self._relayout()

    def alignment(self) -> Qt.AlignmentFlag:
        """Return the overlay alignment."""
        return self._alignment

    def eventFilter(self, recv, event):  # type: ignore[override]
        """Track anchor movement and visibility."""
        if recv is self._widget:
            event_type = event.type()
            if event_type in (QEvent.Type.Resize, QEvent.Type.Move):
                self._relayout()
            elif event_type == QEvent.Type.Show:
                self._sync_to_anchor()
                self._relayout()
            elif event_type == QEvent.Type.Hide:
                self.hide()
        return super().eventFilter(recv, event)

    def event(self, event):  # type: ignore[override]
        """Update geometry when the overlay layout changes."""
        if event.type() == QEvent.Type.LayoutRequest:
            self._relayout()
            return True
        return super().event(event)

    def paintEvent(self, event: QPaintEvent) -> None:  # type: ignore[override]
        """Paint the widget using the active style."""
        option = QStyleOption()
        option.initFrom(self)
        painter = QPainter(self)
        self.style().drawPrimitive(QStyle.PrimitiveElement.PE_Widget, option, painter, self)
        del event

    def showEvent(self, event) -> None:  # type: ignore[override]
        """Refresh geometry when the overlay becomes visible."""
        super().showEvent(event)
        self._relayout()

    def _sync_to_anchor(self) -> None:
        widget = self._widget
        if widget is None:
            self.hide()
            return
        self.setVisible(widget.isVisible())

    def _anchor_bounds(self) -> QRect:
        widget = self._widget
        if widget is None:
            return QRect()

        if widget.window() is self.window() and not self.isWindow():
            top_left = widget.mapTo(self.parentWidget(), QPoint(0, 0))
            return QRect(top_left, widget.size())

        bounds = widget.geometry() if widget.isWindow() else QRect(widget.mapToGlobal(QPoint(0, 0)), widget.size())
        if self.isWindow():
            return bounds
        return QRect(self.parentWidget().mapFromGlobal(bounds.topLeft()), bounds.size())

    @staticmethod
    def _resolved_size(
        hint: int,
        minimum: int,
        maximum: int,
        policy: QSizePolicy.Policy,
    ) -> int:
        if policy in (QSizePolicy.Policy.Ignored, QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Expanding):
            return maximum
        return max(hint, minimum)

    def _relayout(self) -> None:
        widget = self._widget
        if widget is None or (self.parentWidget() is None and not self.isWindow()):
            return

        bounds = self._anchor_bounds()
        if not bounds.isValid():
            return

        size_policy = self.sizePolicy()
        size_hint = self.sizeHint()
        minimum_size = self.minimumSize()
        if minimum_size.isNull():
            minimum_size = self.minimumSizeHint()

        max_size = bounds.size().boundedTo(self.maximumSize())
        minimum_size = minimum_size.boundedTo(max_size)
        effective_size_hint = size_hint.expandedTo(minimum_size).boundedTo(max_size)

        h_policy = size_policy.horizontalPolicy()
        v_policy = size_policy.verticalPolicy()
        if not effective_size_hint.isValid():
            effective_size_hint = QSize(0, 0)
            h_policy = QSizePolicy.Policy.Ignored
            v_policy = QSizePolicy.Policy.Ignored

        width = self._resolved_size(effective_size_hint.width(), minimum_size.width(), max_size.width(), h_policy)
        height_for_width = self.heightForWidth(width)
        if height_for_width > 0:
            height = self._resolved_size(height_for_width, minimum_size.height(), max_size.height(), v_policy)
        else:
            height = self._resolved_size(
                effective_size_hint.height(), minimum_size.height(), max_size.height(), v_policy
            )

        size = QSize(width, height)
        alignment = self._alignment

        if alignment & Qt.AlignmentFlag.AlignLeft:
            x = bounds.x()
        elif alignment & Qt.AlignmentFlag.AlignRight:
            x = bounds.right() - size.width() + 1
        else:
            x = bounds.x() + max(0, bounds.width() - size.width()) // 2

        if alignment & Qt.AlignmentFlag.AlignTop:
            y = bounds.y()
        elif alignment & Qt.AlignmentFlag.AlignBottom:
            y = bounds.bottom() - size.height() + 1
        else:
            y = bounds.y() + max(0, bounds.height() - size.height()) // 2

        self.setGeometry(QRect(QPoint(x, y + self.Y_OFFSET), size))

    @Slot()
    def _on_destroyed(self) -> None:
        self._widget = None
        with suppress(RuntimeError):
            self.hide()


class QtOverlayWidget(QFrame):
    """Simple overlay body that renders a single line of text."""

    def __init__(self, parent: QWidget | None = None, text: str = "", **kwargs):
        super().__init__(parent, **kwargs)
        self.setFrameShape(QFrame.Shape.Box)
        self.setLineWidth(1)

        self.text_label = QLabel(text=text, wordWrap=False, textFormat=Qt.TextFormat.AutoText)
        self.text_label.setAlignment(Qt.AlignmentFlag.AlignJustify)
        if sys.platform == "darwin":
            self.text_label.setAttribute(Qt.WidgetAttribute.WA_MacSmallSize)

        row = QHBoxLayout(self)
        row.setContentsMargins(6, 4, 6, 4)
        row.addWidget(self.text_label, stretch=True)


class QtOverlayLabel(QtOverlay):
    """Text label that sits on top of another widget."""

    def __init__(
        self,
        parent: QWidget | None = None,
        text: str = "",
        alignment: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignTop,
        widget: QWidget | None = None,
        **kwargs,
    ):
        super().__init__(parent=parent, alignment=alignment, widget=widget, **kwargs)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        self._msg_widget = QtOverlayWidget(parent=self, text=text)
        layout.addWidget(self._msg_widget)

    @property
    def text(self) -> str:
        """Return overlay text."""
        return self._msg_widget.text_label.text()

    def set_text(self, text: str) -> None:
        """Update overlay text."""
        self._msg_widget.text_label.setText(text)
        self.updateGeometry()
        self._relayout()


class QtMessageWidget(QFrame):
    """Widget to display a simple message with optional actions."""

    evt_accepted = Signal()
    evt_rejected = Signal()
    evt_dismissed = Signal()

    def __init__(
        self,
        parent: QWidget | None = None,
        icon_name: str = "info",
        text: str = "",
        wrap_word: bool = False,
        text_format: Qt.TextFormat = Qt.TextFormat.AutoText,
        **kwargs,
    ):
        super().__init__(parent, **kwargs)
        self._dismissed = False

        self.setFrameShape(QFrame.Shape.Box)
        self.setLineWidth(1)

        self.icon_label = QtIconLabel(icon_name, parent=self)
        self.text_label = hp.make_label(
            self,
            text=text,
            wrap=wrap_word,
            text_format=text_format,
            alignment=Qt.AlignmentFlag.AlignJustify,
        )

        self.ok_btn = hp.make_btn(self, "OK", tooltip="Accept", func=self.on_accept, hide=True)
        self.cancel_btn = hp.make_btn(self, "Close", tooltip="Close message", func=self.on_close, hide=True)
        self.dismiss_btn = hp.make_btn(
            self,
            "Dismiss",
            tooltip="Dismiss message and don't show it again in this session",
            func=self.on_dismiss,
            hide=True,
        )

        self.btn_row = QHBoxLayout()
        self.btn_row.addWidget(self.ok_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        self.btn_row.addWidget(self.cancel_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        self.btn_row.addWidget(self.dismiss_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        message_row = QHBoxLayout()
        message_row.addWidget(self.icon_label, alignment=Qt.AlignmentFlag.AlignTop)
        message_row.addWidget(self.text_label, stretch=True)
        message_row.setSpacing(5)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(4, 4, 4, 4)
        self._layout.setSpacing(0)
        self._layout.addLayout(message_row)
        self._layout.addSpacing(5)
        self._layout.addLayout(self.btn_row)

    @property
    def is_dismissed(self) -> bool:
        """Return whether the message was dismissed for the current session."""
        return self._dismissed

    def set_buttons(
        self,
        ok_btn: bool = False,
        cancel_btn: bool = False,
        dismiss_btn: bool = False,
        ok_func: Callable | None = None,
        ok_text: str = "OK",
    ) -> None:
        """Configure which buttons are visible."""
        self.ok_btn.setVisible(ok_btn)
        self.ok_btn.setText(ok_text)
        if ok_func is not None and callable(ok_func):
            with suppress(TypeError):
                self.ok_btn.clicked.disconnect(ok_func)
            self.ok_btn.clicked.connect(ok_func)
        self.cancel_btn.setVisible(cancel_btn)
        self.dismiss_btn.setVisible(dismiss_btn)

    def display(self) -> None:
        """Display the message if it has not been dismissed."""
        if self._dismissed:
            return
        self.show()

    def on_accept(self) -> None:
        """Close the message and emit the accept signal."""
        self.hide()
        self.evt_accepted.emit()

    def on_close(self) -> None:
        """Close the message and emit the reject signal."""
        self.hide()
        self.evt_rejected.emit()

    def on_dismiss(self) -> None:
        """Dismiss the message for the current session."""
        self.hide()
        self._dismissed = True
        self.evt_dismissed.emit()

    def dismiss(self) -> None:
        """Dismiss the message for the current session."""
        self.on_dismiss()


class QtOverlayMessage(QtOverlay):
    """Message widget that sits on top of another widget."""

    evt_accepted = Signal()
    evt_rejected = Signal()
    evt_dismissed = Signal()

    def __init__(
        self,
        parent: QWidget | None = None,
        text: str = "",
        icon_name: str = "",
        alignment: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignTop,
        word_wrap: bool = False,
        can_dismiss: bool = True,
        widget: QWidget | None = None,
        **kwargs,
    ):
        super().__init__(parent=parent, alignment=alignment, widget=widget, **kwargs)
        self._can_dismiss = can_dismiss

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._msg_widget = QtMessageWidget(
            parent=self,
            text=text,
            icon_name=icon_name,
            wrap_word=word_wrap,
        )
        self._msg_widget.evt_accepted.connect(self.evt_accepted)
        self._msg_widget.evt_rejected.connect(self.evt_rejected)
        self._msg_widget.evt_dismissed.connect(self.evt_dismissed)

        layout.addWidget(self._msg_widget)

    @property
    def is_dismissed(self) -> bool:
        """Return whether the message has been dismissed."""
        return self._msg_widget.is_dismissed

    @property
    def is_displayed(self) -> bool:
        """Return whether the message content is currently visible."""
        return self._msg_widget.isVisible()

    def dismiss(self) -> None:
        """Dismiss the message."""
        self._msg_widget.dismiss()
        if not self._can_dismiss:
            self._msg_widget._dismissed = False

    def display(self) -> None:
        """Display the message."""
        self._msg_widget.display()
        if self.widget() is not None and self.widget().isVisible():
            self.show()
            self._relayout()


class QtOverlayDismissMessage(QtOverlayMessage):
    """Overlay message preconfigured with dismiss and optional OK actions."""

    def __init__(
        self,
        parent: QWidget | None = None,
        text: str = "",
        icon_name: str = "",
        alignment: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignTop,
        word_wrap: bool = False,
        dismiss_btn: bool = True,
        ok_btn: bool = False,
        ok_func: Callable | None = None,
        ok_text: str = "OK",
        widget: QWidget | None = None,
        **kwargs,
    ):
        super().__init__(
            parent=parent,
            text=text,
            icon_name=icon_name,
            alignment=alignment,
            word_wrap=word_wrap,
            widget=widget,
            **kwargs,
        )
        self._msg_widget.set_buttons(dismiss_btn=dismiss_btn, ok_btn=ok_btn, ok_func=ok_func, ok_text=ok_text)


if __name__ == "__main__":  # pragma: no cover
    import qtextra.helpers as hp
    from qtextra.utils.dev import qframe

    def _popup_dismiss() -> None:
        overlay_widget = QtOverlayDismissMessage(
            frame,
            "Some random text that is written here to test the overlay message widget" * 3,
            word_wrap=True,
            dismiss_btn=True,
            can_dismiss=True,
        )
        overlay_widget.set_widget(frame)

    app, frame, layout = qframe(False)
    frame.setLayout(layout)
    frame.setMinimumSize(400, 400)

    btn = hp.make_btn(frame, "Create popup")
    btn.clicked.connect(_popup_dismiss)
    layout.addWidget(btn)

    overlay = QtOverlayLabel(parent=frame, text="Spatial overlay text")
    overlay.set_widget(frame)

    frame.show()
    sys.exit(app.exec_())
