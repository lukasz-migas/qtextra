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
from qtpy.QtWidgets import QFrame, QGraphicsOpacityEffect, QHBoxLayout, QLabel, QVBoxLayout, QWidget

import qtextra.helpers as hp
from qtextra.config import is_dark
from qtextra.utils.wrap import TextWrap
from qtextra.widgets.qt_label_icon import QtSeverityLabel


class ToastPosition(Enum):
    """Info bar position."""

    TOP = 0
    BOTTOM = 1
    TOP_LEFT = 2
    TOP_RIGHT = 3
    BOTTOM_LEFT = 4
    BOTTOM_RIGHT = 5
    NONE = 6


class QtInfoToast(QFrame):
    """Information bar."""

    evt_closed = Signal()

    def __init__(
        self,
        icon: Union[QIcon, str],
        title: str,
        content: str,
        orientation=Qt.Orientation.Horizontal,
        is_closable=True,
        duration=1000,
        position=ToastPosition.TOP_RIGHT,
        parent=None,
    ):
        """
        Parameters
        ----------
        icon: QtInfoToastIcon | FluentIconBase | QIcon | str
            the icon of info bar

        title: str
            the title of info bar

        content: str
            the content of info bar

        orientation: Qt.Orientation
            the layout direction of info bar, use `Qt.Horizontal` for short content

        is_closable: bool
            whether to show the close button

        duraction: int
            the time for info bar to display in milliseconds. If duration is less than zero,
            info bar will never disappear.

        parent: QWidget
            parent widget
        """
        super().__init__(parent=parent)
        self.title = title
        self.content = content
        self.orient = orientation
        self.icon = icon
        self.duration = duration
        self.is_closable = is_closable
        self.position = position

        self.titleLabel = QLabel(self)
        self.contentLabel = QLabel(self)
        self.closeButton = hp.make_qta_btn(self, "cross")
        self.iconWidget = QtSeverityLabel(self)
        self.iconWidget.severity = icon

        self.hBoxLayout = QHBoxLayout(self)
        self.textLayout = QHBoxLayout() if self.orient == Qt.Orientation.Horizontal else QVBoxLayout()
        self.widgetLayout = QHBoxLayout() if self.orient == Qt.Orientation.Horizontal else QVBoxLayout()

        self.opacityEffect = QGraphicsOpacityEffect(self)
        self.opacityAni = QPropertyAnimation(self.opacityEffect, b"opacity", self)

        self.lightBackgroundColor = None
        self.darkBackgroundColor = None

        self.__initWidget()

    def __initWidget(self):
        self.opacityEffect.setOpacity(1)
        self.setGraphicsEffect(self.opacityEffect)

        self.closeButton.setFixedSize(36, 36)
        self.closeButton.setIconSize(QSize(12, 12))
        self.closeButton.setCursor(Qt.CursorShape.PointingHandCursor)
        self.closeButton.setVisible(self.is_closable)

        self.__setQss()
        self.__initLayout()

        self.closeButton.clicked.connect(self.close)

    def __initLayout(self):
        self.hBoxLayout.setContentsMargins(6, 6, 6, 6)
        self.hBoxLayout.setSizeConstraint(QVBoxLayout.SetMinimumSize)
        self.textLayout.setSizeConstraint(QHBoxLayout.SetMinimumSize)
        self.textLayout.setAlignment(Qt.AlignTop)
        self.textLayout.setContentsMargins(1, 8, 0, 8)

        self.hBoxLayout.setSpacing(0)
        self.textLayout.setSpacing(5)

        # add icon to layout
        self.hBoxLayout.addWidget(self.iconWidget, 0, Qt.AlignTop | Qt.AlignLeft)

        # add title to layout
        self.textLayout.addWidget(self.titleLabel, 1, Qt.AlignTop)
        self.titleLabel.setVisible(bool(self.title))

        # add content label to layout
        if self.orient == Qt.Horizontal:
            self.textLayout.addSpacing(7)

        self.textLayout.addWidget(self.contentLabel, 1, Qt.AlignTop)
        self.contentLabel.setVisible(bool(self.content))
        self.hBoxLayout.addLayout(self.textLayout)

        # add widget layout
        if self.orient == Qt.Horizontal:
            self.hBoxLayout.addLayout(self.widgetLayout)
            self.widgetLayout.setSpacing(10)
        else:
            self.textLayout.addLayout(self.widgetLayout)

        # add close button to layout
        self.hBoxLayout.addSpacing(12)
        self.hBoxLayout.addWidget(self.closeButton, 0, Qt.AlignTop | Qt.AlignLeft)

        self._adjustText()

    def __setQss(self):
        self.titleLabel.setObjectName("titleLabel")
        self.contentLabel.setObjectName("contentLabel")
        if isinstance(self.icon, Enum):
            self.setProperty("type", self.icon.value)

    def __fadeOut(self):
        """Fade out."""
        self.opacityAni.setDuration(200)
        self.opacityAni.setStartValue(1)
        self.opacityAni.setEndValue(0)
        self.opacityAni.finished.connect(self.close)
        self.opacityAni.start()

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
        """Add widget to info bar."""
        self.widgetLayout.addSpacing(6)
        align = Qt.AlignTop if self.orient == Qt.Vertical else Qt.AlignVCenter
        self.widgetLayout.addWidget(widget, stretch, Qt.AlignLeft | align)

    def setCustomBackgroundColor(self, light, dark):
        """Set the custom background color.

        Parameters
        ----------
        light, dark: str | Qt.GlobalColor | QColor
            background color in light/dark theme mode
        """
        self.lightBackgroundColor = QColor(light)
        self.darkBackgroundColor = QColor(dark)
        self.update()

    def eventFilter(self, obj, e: QEvent):
        if obj is self.parent():
            if e.type() in [QEvent.Resize, QEvent.WindowStateChange]:
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
        if self.lightBackgroundColor is None:
            return

        painter = QPainter(self)
        painter.setRenderHints(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)

        if is_dark():
            painter.setBrush(self.darkBackgroundColor)
        else:
            painter.setBrush(self.lightBackgroundColor)

        rect = self.rect().adjusted(1, 1, -1, -1)
        painter.drawRoundedRect(rect, 6, 6)

    @classmethod
    def new(
        cls,
        icon,
        title,
        content,
        orientation: Qt.Orientation = Qt.Orientation.Horizontal,
        is_closable=True,
        duration=1000,
        position=ToastPosition.TOP_RIGHT,
        parent=None,
    ):
        w = QtInfoToast(icon, title, content, orientation, is_closable, duration, position, parent)
        w.show()
        return w

    @classmethod
    def info(
        cls,
        title: str,
        content: str,
        orientation: Qt.Orientation = Qt.Orientation.Horizontal,
        is_closable: bool = True,
        duration: int = 1000,
        position: ToastPosition = ToastPosition.TOP_RIGHT,
        parent: QWidget | None = None,
    ):
        return cls.new("info", title, content, orientation, is_closable, duration, position, parent)

    @classmethod
    def success(
        cls,
        title: str,
        content: str,
        orientation: Qt.Orientation = Qt.Orientation.Horizontal,
        is_closable: bool = True,
        duration: int = 1000,
        position: ToastPosition = ToastPosition.TOP_RIGHT,
        parent: QWidget | None = None,
    ):
        return cls.new("success", title, content, orientation, is_closable, duration, position, parent)

    @classmethod
    def warning(
        cls,
        title: str,
        content: str,
        orientation: Qt.Orientation = Qt.Orientation.Horizontal,
        is_closable: bool = True,
        duration: int = 1000,
        position: ToastPosition = ToastPosition.TOP_RIGHT,
        parent: QWidget | None = None,
    ):
        return cls.new("warning", title, content, orientation, is_closable, duration, position, parent)

    @classmethod
    def error(
        cls,
        title: str,
        content: str,
        orientation: Qt.Orientation = Qt.Orientation.Horizontal,
        is_closable: bool = True,
        duration: int = 1000,
        position: ToastPosition = ToastPosition.TOP_RIGHT,
        parent: QWidget | None = None,
    ):
        return cls.new("error", title, content, orientation, is_closable, duration, position, parent)


class QtInfoToastManager(QObject):
    """Info bar manager."""

    _instance = None
    managers = {}

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls, *args, **kwargs)
            cls._instance.__initialized = False

        return cls._instance

    def __init__(self):
        super().__init__()
        if self.__initialized:
            return

        self.spacing = 16
        self.margin = 24
        self._toast = weakref.WeakKeyDictionary()
        self._animation_groups = weakref.WeakKeyDictionary()
        self._slide_animations = []
        self._drop_animations = []
        self.__initialized = True

    def add(self, toast: QtInfoToast):
        """Add info bar."""
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
            dropAni = QPropertyAnimation(toast, b"pos")
            dropAni.setDuration(200)

            self._animation_groups[p].addAnimation(dropAni)
            self._drop_animations.append(dropAni)

            toast.setProperty("dropAni", dropAni)

        # add slide animation
        self._toast[p].append(toast)
        slideAni = self._createSlideAni(toast)
        self._slide_animations.append(slideAni)

        toast.setProperty("slideAni", slideAni)
        toast.evt_closed.connect(lambda: self.remove(toast))

        slideAni.start()

    def remove(self, toast: QtInfoToast):
        """Remove info bar."""
        p = toast.parent()
        if p not in self._toast:
            return

        if toast not in self._toast[p]:
            return

        self._toast[p].remove(toast)

        # remove drop animation
        dropAni = toast.property("dropAni")  # type: QPropertyAnimation
        if dropAni:
            self._animation_groups[p].removeAnimation(dropAni)
            self._drop_animations.remove(dropAni)

        # remove slider animation
        slideAni = toast.property("slideAni")
        if slideAni:
            self._slide_animations.remove(slideAni)

        # adjust the position of the remaining info bars
        self._updateDropAni(p)
        self._animation_groups[p].start()

    def _createSlideAni(self, toast: QtInfoToast):
        slideAni = QPropertyAnimation(toast, b"pos")
        slideAni.setEasingCurve(QEasingCurve.OutQuad)
        slideAni.setDuration(200)

        slideAni.setStartValue(self._slideStartPos(toast))
        slideAni.setEndValue(self._pos(toast))

        return slideAni

    def _updateDropAni(self, parent):
        for bar in self._toast[parent]:
            ani = bar.property("dropAni")
            if not ani:
                continue

            ani.setStartValue(bar.pos())
            ani.setEndValue(self._pos(bar))

    def _pos(self, toast: QtInfoToast, parentSize=None) -> QPoint:
        """Return the position of info bar."""
        raise NotImplementedError

    def _slideStartPos(self, toast: QtInfoToast) -> QPoint:
        """Return the start position of slide animation."""
        raise NotImplementedError

    def eventFilter(self, obj, e: QEvent):
        if obj not in self._toast:
            return False

        if e.type() in [QEvent.Resize, QEvent.WindowStateChange]:
            size = e.size() if e.type() == QEvent.Resize else None
            for bar in self._toast[obj]:
                bar.move(self._pos(bar, size))

        return super().eventFilter(obj, e)

    @classmethod
    def register(cls, name):
        """Register menu animation manager.

        Parameters
        ----------
        name: Any
            the name of manager, it should be unique
        """

        def wrapper(Manager):
            if name not in cls.managers:
                cls.managers[name] = Manager

            return Manager

        return wrapper

    @classmethod
    def make(cls, position: ToastPosition):
        """Mask info bar manager according to the display position."""
        if position not in cls.managers:
            raise ValueError(f"`{position}` is an invalid animation type.")

        return cls.managers[position]()


@QtInfoToastManager.register(ToastPosition.TOP)
class TopQtInfoToastManager(QtInfoToastManager):
    """Top position info bar manager."""

    def _pos(self, toast: QtInfoToast, parentSize=None):
        p = toast.parent()

        x = (toast.parent().width() - toast.width()) // 2
        y = self.margin
        index = self._toast[p].index(toast)
        for bar in self._toast[p][0:index]:
            y += bar.height() + self.spacing

        return QPoint(x, y)

    def _slideStartPos(self, toast: QtInfoToast):
        pos = self._pos(toast)
        return QPoint(pos.x(), pos.y() - 16)


@QtInfoToastManager.register(ToastPosition.TOP_RIGHT)
class TopRightQtInfoToastManager(QtInfoToastManager):
    """Top right position info bar manager."""

    def _pos(self, toast: QtInfoToast, parentSize=None):
        p = toast.parent()
        parentSize = parentSize or p.size()

        x = parentSize.width() - toast.width() - self.margin
        y = self.margin
        index = self._toast[p].index(toast)
        for bar in self._toast[p][0:index]:
            y += bar.height() + self.spacing

        return QPoint(x, y)

    def _slideStartPos(self, toast: QtInfoToast):
        return QPoint(toast.parent().width(), self._pos(toast).y())


@QtInfoToastManager.register(ToastPosition.BOTTOM_RIGHT)
class BottomRightQtInfoToastManager(QtInfoToastManager):
    """Bottom right position info bar manager."""

    def _pos(self, toast: QtInfoToast, parentSize=None) -> QPoint:
        p = toast.parent()
        parentSize = parentSize or p.size()

        x = parentSize.width() - toast.width() - self.margin
        y = parentSize.height() - toast.height() - self.margin

        index = self._toast[p].index(toast)
        for bar in self._toast[p][0:index]:
            y -= bar.height() + self.spacing

        return QPoint(x, y)

    def _slideStartPos(self, toast: QtInfoToast):
        return QPoint(toast.parent().width(), self._pos(toast).y())


@QtInfoToastManager.register(ToastPosition.TOP_LEFT)
class TopLeftQtInfoToastManager(QtInfoToastManager):
    """Top left position info bar manager."""

    def _pos(self, toast: QtInfoToast, parentSize=None) -> QPoint:
        p = toast.parent()

        y = self.margin
        index = self._toast[p].index(toast)

        for bar in self._toast[p][0:index]:
            y += bar.height() + self.spacing

        return QPoint(self.margin, y)

    def _slideStartPos(self, toast: QtInfoToast):
        return QPoint(-toast.width(), self._pos(toast).y())


@QtInfoToastManager.register(ToastPosition.BOTTOM_LEFT)
class BottomLeftQtInfoToastManager(QtInfoToastManager):
    """Bottom left position info bar manager."""

    def _pos(self, toast: QtInfoToast, parentSize: QSize = None) -> QPoint:
        p = toast.parent()
        parentSize = parentSize or p.size()

        y = parentSize.height() - toast.height() - self.margin
        index = self._toast[p].index(toast)

        for bar in self._toast[p][0:index]:
            y -= bar.height() + self.spacing

        return QPoint(self.margin, y)

    def _slideStartPos(self, toast: QtInfoToast):
        return QPoint(-toast.width(), self._pos(toast).y())


@QtInfoToastManager.register(ToastPosition.BOTTOM)
class BottomQtInfoToastManager(QtInfoToastManager):
    """Bottom position info bar manager."""

    def _pos(self, toast: QtInfoToast, parentSize: QSize = None) -> QPoint:
        p = toast.parent()
        parentSize = parentSize or p.size()

        x = (parentSize.width() - toast.width()) // 2
        y = parentSize.height() - toast.height() - self.margin
        index = self._toast[p].index(toast)

        for bar in self._toast[p][0:index]:
            y -= bar.height() + self.spacing

        return QPoint(x, y)

    def _slideStartPos(self, toast: QtInfoToast):
        pos = self._pos(toast)
        return QPoint(pos.x(), pos.y() + 16)


if __name__ == "__main__":  # pragma: no cover

    def _main():  # type: ignore[no-untyped-def]
        import sys
        from random import choice

        from qtextra.config import THEMES
        from qtextra.utils.dev import qframe, theme_toggle_btn

        def _popup_notif() -> None:
            pop = [QtInfoToast.info, QtInfoToast.success, QtInfoToast.warning, QtInfoToast.error]
            pop = choice(pop)
            pop = pop(
                "Title",
                "Here is a message.\nA couple of lines long.\nAnother line",
                parent=frame,
                position=choice(list(ToastPosition)),
                duration=3000,
            )

            THEMES.set_theme_stylesheet(pop)

        app, frame, ha = qframe(False, set_style=True)
        frame.setMinimumSize(600, 600)

        btn2 = hp.make_btn(frame, "Create random notification")
        btn2.clicked.connect(_popup_notif)
        ha.addWidget(btn2)
        ha.addWidget(theme_toggle_btn(frame))
        ha.addStretch(1)

        frame.show()
        sys.exit(app.exec_())

    _main()
