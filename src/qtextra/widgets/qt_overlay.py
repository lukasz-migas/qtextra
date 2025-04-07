"""Overlay Message Widget - A Widget to display a temporary dismissible message over another widget."""

import sys

from qtpy.QtCore import QEvent, QPoint, QRect, QSize, Qt, Signal, Slot
from qtpy.QtGui import QPainter
from qtpy.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy, QStyle, QStyleOption, QVBoxLayout, QWidget

from qtextra.helpers import make_btn
from qtextra.widgets.qt_label_icon import QtIconLabel


# noinspection PyPep8Naming
class QtOverlay(QWidget):
    """A widget positioned on top of another widget."""

    Y_OFFSET: int = 10

    def __init__(self, parent=None, alignment=Qt.AlignmentFlag.AlignCenter, **kwargs):
        super().__init__(parent, **kwargs)
        self.setContentsMargins(0, 0, 0, 0)
        self.__alignment = alignment
        self.__widget = None

    def set_widget(self, widget: QWidget):
        """Set the widget over which this overlay should be displayed (anchored)."""
        if self.__widget is not None:
            self.__widget.removeEventFilter(self)
            self.__widget.destroyed.disconnect(self.__on_destroyed)
        self.__widget = widget
        if self.__widget is not None:
            self.__widget.installEventFilter(self)
            self.__widget.destroyed.connect(self.__on_destroyed)

        if self.__widget is None:
            self.hide()
        else:
            self.__layout()

    def widget(self) -> QWidget:
        """Return the overlaid widget."""
        return self.__widget

    def setAlignment(self, alignment: Qt.AlignmentFlag):
        """Set overlay alignment."""
        if self.__alignment != alignment:
            self.__alignment = alignment
            if self.__widget is not None:
                self.__layout()

    def alignment(self) -> Qt.AlignmentFlag:
        """Return the overlay alignment."""
        return self.__alignment

    def eventFilter(self, recv, event):
        """Event filter."""
        # reimplemented
        if recv is self.__widget:
            if event.type() == QEvent.Type.Resize or event.type() == QEvent.Type.Move:
                self.__layout()
            elif event.type() == QEvent.Type.Show:
                self.show()
            elif event.type() == QEvent.Type.Hide:
                self.hide()
        return super().eventFilter(recv, event)

    def event(self, event):
        """Event."""
        # reimplemented
        if event.type() == QEvent.Type.LayoutRequest:
            self.__layout()
            return True
        else:
            return super().event(event)

    def paintEvent(self, event):
        """Paint event."""
        opt = QStyleOption()
        opt.initFrom(self)
        painter = QPainter(self)
        self.style().drawPrimitive(QStyle.PrimitiveElement.PE_Widget, opt, painter, self)

    def showEvent(self, event):
        """Show event."""
        super().showEvent(event)
        # Force immediate re-layout on show
        self.__layout()

    def __layout(self):
        # position itself over `widget`
        # noinspection PyShadowingNames
        def _get_size(hint, minimum, maximum, policy):
            if policy == QSizePolicy.Policy.Ignored:
                return maximum
            elif policy == QSizePolicy.PolicyFlag.ExpandFlag:
                return maximum
            else:
                return max(hint, minimum)

        widget = self.__widget
        if widget is None:
            return

        alignment = self.__alignment
        policy = self.sizePolicy()

        if widget.window() is self.window() and not self.isWindow():
            if widget.isWindow():
                bounds = widget.rect()
            else:
                bounds = QRect(widget.mapTo(widget.window(), QPoint(0, 0)), widget.size())
            tl = self.parent().mapFrom(widget.window(), bounds.topLeft())
            bounds = QRect(tl, widget.size())
        else:
            if widget.isWindow():
                bounds = widget.geometry()
            else:
                bounds = QRect(widget.mapToGlobal(QPoint(0, 0)), widget.size())

            if self.isWindow():
                bounds = bounds
            else:
                bounds = QRect(self.parent().mapFromGlobal(bounds.topLeft()), bounds.size())

        sh = self.sizeHint()
        min_sh = self.minimumSizeHint()
        minsize = self.minimumSize()
        if minsize.isNull():
            minsize = min_sh
        maxsize = bounds.size().boundedTo(self.maximumSize())
        minsize = minsize.boundedTo(maxsize)
        effective_sh = sh.expandedTo(minsize).boundedTo(maxsize)

        h_policy = policy.horizontalPolicy()
        v_policy = policy.verticalPolicy()

        if not effective_sh.isValid():
            effective_sh = QSize(0, 0)
            v_policy = h_policy = QSizePolicy.Ignored

        width = _get_size(effective_sh.width(), minsize.width(), maxsize.width(), h_policy)

        height_forw = self.heightForWidth(width)
        if height_forw > 0:
            height = _get_size(height_forw, minsize.height(), maxsize.height(), v_policy)
        else:
            height = _get_size(effective_sh.height(), minsize.height(), maxsize.height(), v_policy)

        size = QSize(width, height)
        if alignment & Qt.AlignmentFlag.AlignLeft:
            x = bounds.x()
        elif alignment & Qt.AlignmentFlag.AlignRight:
            x = bounds.x() + bounds.width() - size.width()
        else:
            x = bounds.x() + max(0, bounds.width() - size.width()) // 2

        if alignment & Qt.AlignmentFlag.AlignTop:
            y = bounds.y()
        elif alignment & Qt.AlignmentFlag.AlignBottom:
            y = bounds.y() + bounds.height() - size.height()
        else:
            y = bounds.y() + max(0, bounds.height() - size.height()) // 2

        geom = QRect(QPoint(x, y + self.Y_OFFSET), size)
        self.setGeometry(geom)

    @Slot()
    def __on_destroyed(self):
        self.__widget = None
        try:
            if self.isVisible():
                self.hide()
        except RuntimeError:
            pass


class QtOverlayWidget(QFrame):
    """Widget to display message without user interaction."""

    def __init__(
        self,
        parent=None,
        text: str = "",
        **kwargs,
    ):
        super().__init__(parent, **kwargs)
        self.setFrameShape(QFrame.Shape.Box)
        self.setLineWidth(1)

        self.text_label = QLabel(text=text, wordWrap=False, textFormat=Qt.TextFormat.AutoText)
        self.text_label.setAlignment(Qt.AlignmentFlag.AlignJustify)
        if sys.platform == "darwin":
            self.text_label.setAttribute(Qt.WidgetAttribute.WA_MacSmallSize)

        row = QHBoxLayout(self)
        row.addWidget(self.text_label, stretch=True)


class QtOverlayLabel(QtOverlay):
    """Message widget that sits on top of another widget."""

    def __init__(
        self,
        parent=None,
        text="",
        alignment=Qt.AlignmentFlag.AlignTop,
        **kwargs,
    ):
        super().__init__(parent, alignment=alignment, **kwargs)
        layout = QHBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        self._msg_widget = QtOverlayWidget(
            parent=self,
            text=text,
        )

        layout.addWidget(self._msg_widget)
        self.setLayout(layout)


class QtMessageWidget(QFrame):
    """Widget to display simple message to the user."""

    #: Emitted when a button with an Accept role is clicked
    evt_accepted = Signal()
    #: Emitted when a button with a RejectRole is clicked
    evt_rejected = Signal()
    #: Emitted when a button with a DismissRole is clicked
    evt_dismissed = Signal()

    def __init__(
        self,
        parent=None,
        icon_name: str = "info",
        text: str = "",
        wrap_word: bool = False,
        text_format: Qt.TextFormat = Qt.TextFormat.AutoText,
        **kwargs,
    ):
        super().__init__(parent, **kwargs)
        self._text = text
        self._wordWrap = wrap_word
        self._dismissed = False

        self.setFrameShape(QFrame.Box)
        self.setLineWidth(1)

        self.icon_label = QtIconLabel(icon_name, parent=self)
        self.text_label = QLabel(text=text, wordWrap=wrap_word, textFormat=text_format)
        self.text_label.setAlignment(Qt.AlignmentFlag.AlignJustify)
        if sys.platform == "darwin":
            self.text_label.setAttribute(Qt.WidgetAttribute.WA_MacSmallSize)

        self.ok_btn = make_btn(self, "OK", tooltip="Accept")
        self.ok_btn.clicked.connect(self.on_accept)
        self.ok_btn.setVisible(False)
        self.cancel_btn = make_btn(self, "Close", tooltip="Close message")
        self.cancel_btn.clicked.connect(self.close)
        self.cancel_btn.setVisible(False)
        self.dismiss_btn = make_btn(self, "Dismiss", tooltip="Dismiss message and don't show it again in this session")
        self.dismiss_btn.clicked.connect(self.on_dismiss)
        self.dismiss_btn.setVisible(False)

        self.btn_row = QHBoxLayout()
        self.btn_row.addWidget(self.ok_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        self.btn_row.addWidget(self.cancel_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        self.btn_row.addWidget(self.dismiss_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        row = QHBoxLayout()
        row.addWidget(self.icon_label, alignment=Qt.AlignmentFlag.AlignTop)
        row.addWidget(self.text_label, stretch=True)
        row.setSpacing(5)

        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(4, 4, 4, 4)
        self.layout.setSpacing(0)
        self.layout.addLayout(row)
        self.layout.addSpacing(5)
        self.layout.addLayout(self.btn_row)
        self.setLayout(self.layout)

    def set_buttons(
        self, ok_btn: bool = False, cancel_btn: bool = False, dismiss_btn: bool = False, ok_func=None, ok_text="OK"
    ):
        """Set buttons on the ui."""
        self.ok_btn.setVisible(ok_btn)
        self.ok_btn.setText(ok_text)
        if ok_func is not None and callable(ok_func):
            self.ok_btn.clicked.connect(ok_func)
        self.cancel_btn.setVisible(cancel_btn)
        self.dismiss_btn.setVisible(dismiss_btn)

    def display(self):
        """Display widget if it has not been dismissed before."""
        if self._dismissed:
            return
        self.setVisible(True)

    def on_accept(self):
        """Close message and accept."""
        self.hide()
        self.evt_accepted.emit()

    def on_close(self):
        """Close message and reject."""
        self.hide()
        self.evt_rejected.emit()

    def on_dismiss(self):
        """Close message and reject."""
        self.hide()
        self._dismissed = True
        self.evt_dismissed.emit()

    def dismiss(self):
        """Dismiss widget."""
        self.on_dismiss()


class QtOverlayMessage(QtOverlay):
    """Message widget that sits on top of another widget."""

    #: Emitted when a button with an Accept role is clicked
    evt_accepted = Signal()
    #: Emitted when a button with a RejectRole is clicked
    evt_rejected = Signal()
    #: Emitted when a button with a DismissRole is clicked
    evt_dismissed = Signal()

    def __init__(
        self,
        parent=None,
        text="",
        icon_name="",
        alignment=Qt.AlignmentFlag.AlignTop,
        word_wrap=False,
        can_dismiss: bool = True,
        **kwargs,
    ):
        super().__init__(parent, alignment=alignment, **kwargs)
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self._can_dismiss = can_dismiss
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
        self.setLayout(layout)

    @property
    def is_dismissed(self) -> bool:
        """Flag to indicate whether overlay message is dismissed."""
        return self._msg_widget._dismissed

    @property
    def is_displayed(self) -> bool:
        """Flag to indicate whether overlay message is displayed."""
        return not self._msg_widget._dismissed

    def dismiss(self):
        """Dismiss message."""
        self._msg_widget.dismiss()
        if not self._can_dismiss:
            self._msg_widget._dismissed = False

    def display(self):
        """Display message."""
        self._msg_widget.display()


class QtOverlayDismissMessage(QtOverlayMessage):
    """Message widget that sits on top of another widget."""

    def __init__(
        self,
        parent=None,
        text="",
        icon_name="",
        alignment=Qt.AlignmentFlag.AlignTop,
        word_wrap=False,
        dismiss_btn=True,
        ok_btn=False,
        ok_func=None,
        ok_text="OK",
        **kwargs,
    ):
        super().__init__(
            parent=parent, text=text, icon_name=icon_name, alignment=alignment, word_wrap=word_wrap, **kwargs
        )
        self._msg_widget.set_buttons(dismiss_btn=dismiss_btn, ok_btn=ok_btn, ok_func=ok_func, ok_text=ok_text)


if __name__ == "__main__":  # pragma: no cover
    from qtextra.utils.dev import qframe

    app, frame, ha = qframe(False)
    frame.setLayout(ha)
    frame.setMinimumSize(400, 400)

    overlay = QtOverlayLabel(parent=frame, text="Spatial overlay text")

    # overlay = QtOverlayMessage(
    #     parent=frame,
    #     icon_name="info",
    #     text="This is a test message which should span over several lines This is a test message which
    #     should span over several lines This is a test message which should span over several lines",
    #     word_wrap=True,
    # )
    overlay.set_widget(frame)

    frame.show()
    sys.exit(app.exec_())
