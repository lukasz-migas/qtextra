"""Info widgets."""

from __future__ import annotations

import weakref
from enum import Enum
from typing import Union

from qtpy.QtCore import (
    QEasingCurve,
    QEvent,
    QObject,
    QParallelAnimationGroup,
    QPoint,
    QPropertyAnimation,
    QSize,
    Qt,
    QTimer,
    Signal,
)
from qtpy.QtGui import QColor, QIcon, QPainter
from qtpy.QtWidgets import QFrame, QGraphicsOpacityEffect, QHBoxLayout, QVBoxLayout, QWidget

import qtextra.helpers as hp
from qtextra.config import is_dark
from qtextra.utils.wrap import TextWrap
from qtextra.widgets.qt_label_icon import QtSeverityLabel


class ToastPosition(Enum):
    """info toast position."""

    TOP = 0
    BOTTOM = 1
    TOP_LEFT = 2
    TOP_RIGHT = 3
    BOTTOM_LEFT = 4
    BOTTOM_RIGHT = 5
    NONE = 6


TOAST_POSITION_DICT = {
    "top": ToastPosition.TOP,
    "bottom": ToastPosition.BOTTOM,
    "top_left": ToastPosition.TOP_LEFT,
    "top_right": ToastPosition.TOP_RIGHT,
    "bottom_left": ToastPosition.BOTTOM_LEFT,
    "bottom_right": ToastPosition.BOTTOM_RIGHT,
    "none": ToastPosition.NONE,
}


class QtInfoToast(QFrame):
    """Information bar."""

    evt_closed = Signal()

    def __init__(
        self,
        icon: Union[QIcon, str],
        title: str,
        content: str,
        orientation: Qt.Orientation = Qt.Orientation.Vertical,
        is_closable: bool = True,
        duration: int = 3000,
        position=ToastPosition.TOP_RIGHT,
        parent: QWidget | None = None,
    ):
        """
        Parameters
        ----------
        icon: QtInfoToastIcon |  QIcon | str
            the icon of info toast

        title: str
            the title of info toast

        content: str
            the content of info toast

        orientation: Qt.Orientation
            the layout direction of info toast, use `Qt.Horizontal` for short content

        is_closable: bool
            whether to show the close button

        duration: int
            the time for info toast to display in milliseconds. If duration is less than zero,
            info toast will never disappear.

        parent: QWidget
            parent widget
        """
        super().__init__(parent=parent)
        self.title = title
        self.content = content
        self.orientation = orientation
        self.icon = icon
        self.duration = duration
        self.is_closable = is_closable
        self.position = position

        self.titleLabel = hp.make_label(self, object_name="titleLabel", bold=True)
        self.contentLabel = hp.make_label(self, object_name="contentLabel", wrap=True, enable_url=True)

        self.closeButton = hp.make_qta_btn(self, "cross", func=self.close)
        self.closeButton.set_normal()
        self.closeButton.setCursor(Qt.CursorShape.PointingHandCursor)
        self.closeButton.setVisible(self.is_closable)

        self.iconWidget = QtSeverityLabel(self)
        self.iconWidget.set_normal()
        self.iconWidget.severity = icon
        hp.set_properties(self, {"type": icon, "dark": is_dark()})

        self.hBoxLayout = QHBoxLayout(self)
        self.textLayout = QHBoxLayout() if self.orientation == Qt.Orientation.Horizontal else QVBoxLayout()
        self.widgetLayout = QHBoxLayout() if self.orientation == Qt.Orientation.Horizontal else QVBoxLayout()

        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.opacity_animation = QPropertyAnimation(self.opacity_effect, b"opacity", self)
        self.opacity_effect.setOpacity(1)
        self.setGraphicsEffect(self.opacity_effect)

        self._light_bg_color = None
        self._dark_bg_color = None

        self.__initLayout()

    def __initLayout(self):
        self.hBoxLayout.setContentsMargins(6, 6, 6, 6)
        self.hBoxLayout.setSizeConstraint(QVBoxLayout.SizeConstraint.SetMinimumSize)
        self.textLayout.setSizeConstraint(QHBoxLayout.SizeConstraint.SetMinimumSize)
        self.textLayout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.textLayout.setContentsMargins(1, 8, 0, 8)

        self.hBoxLayout.setSpacing(0)
        self.textLayout.setSpacing(5)

        # add icon to layout
        self.hBoxLayout.addWidget(self.iconWidget, 0, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        # add title to layout
        self.textLayout.addWidget(self.titleLabel, 1, Qt.AlignmentFlag.AlignTop)
        self.titleLabel.setVisible(bool(self.title))

        # add content label to layout
        if self.orientation == Qt.Orientation.Horizontal:
            self.textLayout.addSpacing(7)

        self.textLayout.addWidget(self.contentLabel, 1, Qt.AlignmentFlag.AlignTop)
        self.contentLabel.setVisible(bool(self.content))
        self.hBoxLayout.addLayout(self.textLayout, stretch=True)

        # add widget layout
        if self.orientation == Qt.Orientation.Horizontal:
            self.hBoxLayout.addLayout(self.widgetLayout)
            self.widgetLayout.setSpacing(10)
        else:
            self.textLayout.addLayout(self.widgetLayout)
            self.textLayout.addStretch(True)

        # add close button to layout
        self.hBoxLayout.addSpacing(12)
        self.hBoxLayout.addWidget(self.closeButton, 0, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        self._adjustText()

    def __fadeOut(self):
        """Fade out."""
        self.opacity_animation.setDuration(200)
        self.opacity_animation.setStartValue(1)
        self.opacity_animation.setEndValue(0)
        self.opacity_animation.finished.connect(self.close)
        self.opacity_animation.start()

    def _adjustText(self):
        w = 900 if not self.parent() else (self.parent().width() - 50)

        # adjust title
        chars = max(min(w / 10, 120), 30)
        self.titleLabel.setText(TextWrap.wrap(self.title, chars, False)[0])

        # adjust content
        chars = max(min(w / 9, 120), 30)
        self.contentLabel.setText(TextWrap.wrap(self.content, chars, False)[0])
        self.adjustSize()

    def addWidget(self, widget: QWidget, stretch=0):
        """Add widget to info toast."""
        self.widgetLayout.addSpacing(6)
        align = (
            Qt.AlignmentFlag.AlignTop if self.orientation == Qt.Orientation.Vertical else Qt.AlignmentFlag.AlignVCenter
        )
        self.widgetLayout.addWidget(widget, stretch, Qt.AlignmentFlag.AlignLeft | align)

    def setCustomBackgroundColor(self, light, dark):
        """Set the custom background color.

        Parameters
        ----------
        light, dark: str | Qt.GlobalColor | QColor
            background color in light/dark theme mode
        """
        self._light_bg_color = QColor(light)
        self._dark_bg_color = QColor(dark)
        self.update()

    def eventFilter(self, obj, e: QEvent):
        if obj is self.parent():
            if e.type() in [QEvent.Type.Resize, QEvent.Type.WindowStateChange]:
                self._adjustText()

        return super().eventFilter(obj, e)

    def closeEvent(self, e):
        self.evt_closed.emit()
        self.deleteLater()
        e.ignore()

    def showEvent(self, e):
        self._adjustText()
        super().showEvent(e)

        if self.duration >= 0:
            QTimer.singleShot(self.duration, self.__fadeOut)

        if self.position != ToastPosition.NONE:
            manager = QtInfoToastManager.make(self.position)
            manager.add(self)

        if self.parent():
            self.parent().installEventFilter(self)

    def paintEvent(self, e):
        super().paintEvent(e)
        if self._light_bg_color is None:
            return

        painter = QPainter(self)
        painter.setRenderHints(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)

        if is_dark():
            painter.setBrush(self._dark_bg_color)
        else:
            painter.setBrush(self._light_bg_color)

        rect = self.rect().adjusted(1, 1, -1, -1)
        painter.drawRoundedRect(rect, 6, 6)

    @classmethod
    def new(
        cls,
        icon,
        title,
        content,
        orientation: Qt.Orientation = Qt.Orientation.Vertical,
        is_closable=True,
        duration: int = 3000,
        position=ToastPosition.TOP_RIGHT,
        parent=None,
        min_width: int = 0,
    ):
        """Create new toast."""
        w = QtInfoToast(icon, title, content, orientation, is_closable, duration, position, parent)
        if min_width > 0:
            w.setMinimumWidth(min_width)
        w.show()
        return w

    @classmethod
    def info(
        cls,
        title: str,
        content: str,
        orientation: Qt.Orientation = Qt.Orientation.Vertical,
        is_closable: bool = True,
        duration: int = 1000,
        position: ToastPosition = ToastPosition.TOP_RIGHT,
        parent: QWidget | None = None,
    ):
        """Info toast."""
        return cls.new("info", title, content, orientation, is_closable, duration, position, parent)

    @classmethod
    def success(
        cls,
        title: str,
        content: str,
        orientation: Qt.Orientation = Qt.Orientation.Vertical,
        is_closable: bool = True,
        duration: int = 1000,
        position: ToastPosition = ToastPosition.TOP_RIGHT,
        parent: QWidget | None = None,
    ):
        """Success info toast."""
        return cls.new("success", title, content, orientation, is_closable, duration, position, parent)

    @classmethod
    def warning(
        cls,
        title: str,
        content: str,
        orientation: Qt.Orientation = Qt.Orientation.Vertical,
        is_closable: bool = True,
        duration: int = 1000,
        position: ToastPosition = ToastPosition.TOP_RIGHT,
        parent: QWidget | None = None,
    ):
        """Warning info toast."""
        return cls.new("warning", title, content, orientation, is_closable, duration, position, parent)

    @classmethod
    def error(
        cls,
        title: str,
        content: str,
        orientation: Qt.Orientation = Qt.Orientation.Vertical,
        is_closable: bool = True,
        duration: int = 1000,
        position: ToastPosition = ToastPosition.TOP_RIGHT,
        parent: QWidget | None = None,
    ):
        """Error info toast."""
        return cls.new("error", title, content, orientation, is_closable, duration, position, parent)

    @classmethod
    def critical(
        cls,
        title: str,
        content: str,
        orientation: Qt.Orientation = Qt.Orientation.Vertical,
        is_closable: bool = True,
        duration: int = 1000,
        position: ToastPosition = ToastPosition.TOP_RIGHT,
        parent: QWidget | None = None,
    ):
        """Critical info toast."""
        return cls.new("critical", title, content, orientation, is_closable, duration, position, parent)


class QtInfoToastManager(QObject):
    """info toast manager."""

    _instance = None
    managers = {}

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls, *args, **kwargs)
            cls._instance.__initialized = False

        return cls._instance

    def __init__(self):
        if self.__initialized:
            return
        super().__init__()

        self.spacing = 16
        self.margin = 24
        self._toast = weakref.WeakKeyDictionary()
        self._animation_groups = weakref.WeakKeyDictionary()
        self._slide_animations = []
        self._drop_animations = []
        self.__initialized = True

    def add(self, toast: QtInfoToast):
        """Add info toast."""
        p = toast.parent()  # type:QWidget
        if not p:
            return

        if p not in self._toast:
            p.installEventFilter(self)
            self._toast[p] = []
            self._animation_groups[p] = QParallelAnimationGroup(self)

        if toast in self._toast[p]:
            return

        # add drop animation
        if self._toast[p]:
            remove_animation = QPropertyAnimation(toast, b"pos")
            remove_animation.setDuration(200)

            self._animation_groups[p].addAnimation(remove_animation)
            self._drop_animations.append(remove_animation)

            toast.setProperty("remove_animation", remove_animation)

        # add slide animation
        self._toast[p].append(toast)
        slide_animation = self._create_slide_animation(toast)
        self._slide_animations.append(slide_animation)

        toast.setProperty("slide_animation", slide_animation)
        toast.evt_closed.connect(lambda: self.remove(toast))
        slide_animation.start()

    def remove(self, toast: QtInfoToast):
        """Remove info toast."""
        p = toast.parent()
        if p not in self._toast:
            return

        if toast not in self._toast[p]:
            return

        self._toast[p].remove(toast)

        # remove drop animation
        remove_animation = toast.property("remove_animation")
        if remove_animation:
            self._animation_groups[p].removeAnimation(remove_animation)
            self._drop_animations.remove(remove_animation)

        # remove slider animation
        slide_animation = toast.property("slide_animation")
        if slide_animation:
            self._slide_animations.remove(slide_animation)

        # adjust the position of the remaining info toasts
        self._update_drop_animation(p)
        self._animation_groups[p].start()

    def _create_slide_animation(self, toast: QtInfoToast):
        slide_animation = QPropertyAnimation(toast, b"pos")
        slide_animation.setEasingCurve(QEasingCurve.Type.OutQuad)
        slide_animation.setDuration(200)

        slide_animation.setStartValue(self._get_slider_start_position(toast))
        slide_animation.setEndValue(self._get_position(toast))

        return slide_animation

    def _update_drop_animation(self, parent):
        for bar in self._toast[parent]:
            animation = bar.property("remove_animation")
            if not animation:
                continue

            animation.setStartValue(bar.pos())
            animation.setEndValue(self._get_position(bar))

    def _get_position(self, toast: QtInfoToast, size=None) -> QPoint:
        """Return the position of info toast."""
        raise NotImplementedError

    def _get_slider_start_position(self, toast: QtInfoToast) -> QPoint:
        """Return the start position of slide animation."""
        raise NotImplementedError

    def eventFilter(self, obj, e: QEvent):
        if obj not in self._toast:
            return False

        if e.type() in [QEvent.Type.Resize, QEvent.Type.WindowStateChange]:
            size = e.size() if e.type() == QEvent.Type.Resize else None
            for bar in self._toast[obj]:
                bar.move(self._get_position(bar, size))

        return super().eventFilter(obj, e)

    @classmethod
    def register(cls, name):
        """Register menu animation manager.

        Parameters
        ----------
        name: Any
            the name of manager, it should be unique
        """

        def wrapper(mgr):
            if name not in cls.managers:
                cls.managers[name] = mgr

            return mgr

        return wrapper

    @classmethod
    def make(cls, position: ToastPosition):
        """Mask info toast manager according to the display position."""
        if position not in cls.managers:
            raise ValueError(f"`{position}` is an invalid animation type.")

        return cls.managers[position]()


@QtInfoToastManager.register(ToastPosition.TOP)
class TopQtInfoToastManager(QtInfoToastManager):
    """Top position info toast manager."""

    def _get_position(self, toast: QtInfoToast, size=None):
        p = toast.parent()

        x = (toast.parent().width() - toast.width()) // 2
        y = self.margin
        index = self._toast[p].index(toast)
        for bar in self._toast[p][0:index]:
            y += bar.height() + self.spacing

        return QPoint(x, y)

    def _get_slider_start_position(self, toast: QtInfoToast):
        pos = self._get_position(toast)
        return QPoint(pos.x(), pos.y() - 16)


@QtInfoToastManager.register(ToastPosition.TOP_RIGHT)
class TopRightQtInfoToastManager(QtInfoToastManager):
    """Top right position info toast manager."""

    def _get_position(self, toast: QtInfoToast, size=None):
        p = toast.parent()
        size = size or p.size()

        x = size.width() - toast.width() - self.margin
        y = self.margin
        index = self._toast[p].index(toast)
        for bar in self._toast[p][0:index]:
            y += bar.height() + self.spacing

        return QPoint(x, y)

    def _get_slider_start_position(self, toast: QtInfoToast):
        return QPoint(toast.parent().width(), self._get_position(toast).y())


@QtInfoToastManager.register(ToastPosition.BOTTOM_RIGHT)
class BottomRightQtInfoToastManager(QtInfoToastManager):
    """Bottom right position info toast manager."""

    def _get_position(self, toast: QtInfoToast, size=None) -> QPoint:
        p = toast.parent()
        size = size or p.size()

        x = size.width() - toast.width() - self.margin
        y = size.height() - toast.height() - self.margin

        index = self._toast[p].index(toast)
        for bar in self._toast[p][0:index]:
            y -= bar.height() + self.spacing

        return QPoint(x, y)

    def _get_slider_start_position(self, toast: QtInfoToast):
        return QPoint(toast.parent().width(), self._get_position(toast).y())


@QtInfoToastManager.register(ToastPosition.TOP_LEFT)
class TopLeftQtInfoToastManager(QtInfoToastManager):
    """Top left position info toast manager."""

    def _get_position(self, toast: QtInfoToast, size=None) -> QPoint:
        p = toast.parent()

        y = self.margin
        index = self._toast[p].index(toast)

        for bar in self._toast[p][0:index]:
            y += bar.height() + self.spacing

        return QPoint(self.margin, y)

    def _get_slider_start_position(self, toast: QtInfoToast):
        return QPoint(-toast.width(), self._get_position(toast).y())


@QtInfoToastManager.register(ToastPosition.BOTTOM_LEFT)
class BottomLeftQtInfoToastManager(QtInfoToastManager):
    """Bottom left position info toast manager."""

    def _get_position(self, toast: QtInfoToast, size: QSize = None) -> QPoint:
        p = toast.parent()
        size = size or p.size()

        y = size.height() - toast.height() - self.margin
        index = self._toast[p].index(toast)

        for bar in self._toast[p][0:index]:
            y -= bar.height() + self.spacing

        return QPoint(self.margin, y)

    def _get_slider_start_position(self, toast: QtInfoToast):
        return QPoint(-toast.width(), self._get_position(toast).y())


@QtInfoToastManager.register(ToastPosition.BOTTOM)
class BottomQtInfoToastManager(QtInfoToastManager):
    """Bottom position info toast manager."""

    def _get_position(self, toast: QtInfoToast, size: QSize = None) -> QPoint:
        p = toast.parent()
        size = size or p.size()

        x = (size.width() - toast.width()) // 2
        y = size.height() - toast.height() - self.margin
        index = self._toast[p].index(toast)

        for bar in self._toast[p][0:index]:
            y -= bar.height() + self.spacing

        return QPoint(x, y)

    def _get_slider_start_position(self, toast: QtInfoToast):
        pos = self._get_position(toast)
        return QPoint(pos.x(), pos.y() + 16)


if __name__ == "__main__":  # pragma: no cover

    def _main():  # type: ignore[no-untyped-def]
        import sys
        from random import choice

        from qtextra.config import THEMES
        from qtextra.utils.dev import qframe

        def _popup_notif() -> None:
            pop = [QtInfoToast.info, QtInfoToast.success, QtInfoToast.warning, QtInfoToast.error, QtInfoToast.critical]
            pop = choice(pop)
            pop = pop(
                title="Title",
                content="Here is a message.\nA couple of lines long.\nAnother line",
                parent=frame,
                position=choice(list(ToastPosition)),
                duration=3000,
                orientation=Qt.Orientation.Vertical,
            )

            THEMES.set_theme_stylesheet(pop)

        app, frame, ha = qframe(False, set_style=True)
        frame.setMinimumSize(600, 600)

        btn2 = hp.make_btn(frame, "Create random notification")
        btn2.clicked.connect(_popup_notif)
        ha.addWidget(btn2)
        ha.addStretch(1)

        frame.show()
        sys.exit(app.exec_())

    _main()
