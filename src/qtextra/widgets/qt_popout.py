"""Popout."""

from __future__ import annotations

from enum import Enum
from typing import Union

from qtpy.QtCore import (
    QEasingCurve,
    QMargins,
    QObject,
    QParallelAnimationGroup,
    QPoint,
    QPropertyAnimation,
    Qt,
    Signal,
)
from qtpy.QtGui import QColor, QCursor, QIcon, QImage, QPainter, QPixmap
from qtpy.QtWidgets import QApplication, QGraphicsDropShadowEffect, QHBoxLayout, QVBoxLayout, QWidget

import qtextra.helpers as hp
from qtextra.config import is_dark
from qtextra.utils.wrap import TextWrap
from qtextra.widgets.qt_label_image import QImageLabel


class PopoutAnimationType(Enum):
    """Popout animation type."""

    SLIDE_UP = 0
    SLIDE_DOWN = 1
    SLIDE_LEFT = 2
    SLIDE_RIGHT = 3
    FADE_IN = 4
    NONE = 5


class PopoutViewBase(QWidget):
    """Popout view base class."""

    def __init__(self, parent=None):
        super().__init__(parent=parent)

    def addSpacing(self, size):
        raise NotImplementedError("Must implement method")

    def addWidget(self, widget: QWidget, stretch=0, align=Qt.AlignmentFlag.AlignLeft):
        raise NotImplementedError

    def background_color(self):
        """Return the background color."""
        return QColor(40, 40, 40) if is_dark() else QColor(248, 248, 248)

    def border_color(self):
        """Return the border color."""
        return QColor(0, 0, 0, 45) if is_dark() else QColor(0, 0, 0, 17)

    def paintEvent(self, e):
        """Paint event."""
        painter = QPainter(self)
        painter.setRenderHints(QPainter.RenderHint.Antialiasing)

        painter.setBrush(self.background_color())
        painter.setPen(self.border_color())

        rect = self.rect().adjusted(1, 1, -1, -1)
        painter.drawRoundedRect(rect, 8, 8)


class PopoutView(PopoutViewBase):
    """Popout view.

    Parameters
    ----------
    title: str
        the title of teaching tip

    content: str
        the content of teaching tip

    icon: InfoBarIcon | QIcon | str
        the icon of teaching tip

    image: str | QPixmap | QImage
        the image of teaching tip

    is_closable: bool
        whether to show the close button

    parent: QWidget
        parent widget
    """

    evt_closed = Signal()

    def __init__(
        self,
        title: str,
        content: str,
        icon: Union[QIcon, str] = None,
        image: Union[str, QPixmap, QImage] = None,
        is_closable=False,
        parent=None,
    ):
        super().__init__(parent=parent)

        self.icon = icon
        self.title = title
        self.image = image
        self.content = content
        self.is_closable = is_closable

        self.titleLabel = hp.make_label(self, title, bold=True, object_name="titleLabel")
        self.contentLabel = hp.make_label(self, title, object_name="contentLabel", enable_url=True)

        # add icon widget
        self.iconWidget = hp.make_qta_label(self, icon or "")
        if not self.title or not self.content:
            self.iconWidget.setFixedHeight(36)

        self.imageLabel = QImageLabel(self)
        self.imageLabel.setImage(self.image)

        self.closeButton = hp.make_qta_btn(self, "cross", func=self.evt_closed, average=True, hide=self.is_closable)
        self.closeButton.clicked.connect(self.evt_closed)

        self.titleLabel.setVisible(bool(self.title))
        self.contentLabel.setVisible(bool(self.content))
        self.iconWidget.setHidden(self.icon is None)

        self.viewLayout = QHBoxLayout()
        self.viewLayout.setSpacing(4)

        self.widgetLayout = QVBoxLayout()
        self.widgetLayout.setContentsMargins(0, 8, 0, 8)
        self.widgetLayout.setSpacing(0)

        self.vBoxLayout = QVBoxLayout(self)
        self.vBoxLayout.setContentsMargins(1, 1, 1, 1)
        self.vBoxLayout.setSpacing(0)
        self.vBoxLayout.addLayout(self.viewLayout)

        self.viewLayout.addWidget(self.iconWidget, 0, Qt.AlignmentFlag.AlignVCenter)

        # add text
        self._adjustText()
        self.widgetLayout.addWidget(self.titleLabel)
        self.widgetLayout.addWidget(self.contentLabel)
        self.viewLayout.addLayout(self.widgetLayout)

        # add close button
        self.closeButton.setVisible(self.is_closable)
        self.viewLayout.addWidget(self.closeButton, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        # adjust content margins
        margins = QMargins(6, 5, 6, 5)
        margins.setLeft(20 if not self.icon else 5)
        margins.setRight(20 if not self.is_closable else 6)
        self.viewLayout.setContentsMargins(margins)

        # add image
        self._adjustImage()
        self._addImageToLayout()

    def addSpacing(self, size):
        """Add spacing to view."""
        self.widgetLayout.addSpacing(size)

    def addWidget(self, widget: QWidget, stretch=0, align=Qt.AlignmentFlag.AlignLeft):
        """Add widget to view."""
        self.widgetLayout.addSpacing(8)
        self.widgetLayout.addWidget(widget, stretch, align)

    def _addImageToLayout(self):
        self.imageLabel.setBorderRadius(8, 8, 0, 0)
        self.imageLabel.setHidden(self.imageLabel.isNull())
        self.vBoxLayout.insertWidget(0, self.imageLabel)

    def _adjustText(self):
        w = min(900, QApplication.screenAt(QCursor.pos()).geometry().width() - 200)

        # adjust title
        chars = max(min(w / 10, 120), 30)
        self.titleLabel.setText(TextWrap.wrap(self.title, chars, False)[0])

        # adjust content
        chars = max(min(w / 9, 120), 30)
        self.contentLabel.setText(TextWrap.wrap(self.content, chars, False)[0])

    def _adjustImage(self):
        w = self.vBoxLayout.sizeHint().width() - 2
        self.imageLabel.scaledToWidth(w)

    def showEvent(self, e):
        """Show event."""
        super().showEvent(e)
        self._adjustImage()
        self.adjustSize()


class QtPopout(QWidget):
    """Popout."""

    evt_closed = Signal()

    def __init__(self, view: PopoutViewBase, parent=None, close_on_delete=True):
        super().__init__(parent=parent)
        self.view = view
        self.hBoxLayout = QHBoxLayout(self)
        self.aniManager = None  # type: PopoutAnimationManager
        self.close_on_delete = close_on_delete

        self.hBoxLayout.setContentsMargins(15, 8, 15, 20)
        self.hBoxLayout.addWidget(self.view)
        self.setShadowEffect()

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowFlags(
            Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint | Qt.WindowType.NoDropShadowWindowHint
        )

    def setShadowEffect(self, blurRadius=35, offset=(0, 8)):
        """Add shadow to dialog."""
        color = QColor(0, 0, 0, 80 if is_dark() else 30)
        self.shadowEffect = QGraphicsDropShadowEffect(self.view)
        self.shadowEffect.setBlurRadius(blurRadius)
        self.shadowEffect.setOffset(*offset)
        self.shadowEffect.setColor(color)
        self.view.setGraphicsEffect(None)
        self.view.setGraphicsEffect(self.shadowEffect)

    def closeEvent(self, e):
        """Close event."""
        if self.close_on_delete:
            self.deleteLater()

        super().closeEvent(e)
        self.evt_closed.emit()

    def showEvent(self, e):
        # fixes #780
        self.activateWindow()
        super().showEvent(e)

    def exec(self, pos: QPoint, animation_type=PopoutAnimationType.SLIDE_UP):
        """Show calendar view."""
        self.aniManager = PopoutAnimationManager.make(animation_type, self)
        self.show()
        self.aniManager.exec(pos)

    @classmethod
    def _init(
        cls,
        view: PopoutViewBase,
        target: Union[QWidget, QPoint] = None,
        parent=None,
        animation_type: PopoutAnimationType = PopoutAnimationType.SLIDE_UP,
        close_on_delete: bool = True,
    ):
        """Create and show a Popout.

        Parameters
        ----------
        view: PopoutViewBase
            Popout view

        target: QWidget | QPoint
            the target widget or position to show Popout

        parent: QWidget
            parent window

        animation_type: PopoutAnimationType
            Popout animation type

        close_on_delete: bool
            whether delete Popout automatically when Popout is evt_closed
        """
        w = cls(view, parent, close_on_delete)

        if target is None:
            return w

        # show Popout first so that we can get the correct size
        w.show()

        # move Popout to the top of target
        if isinstance(target, QWidget):
            target = PopoutAnimationManager.make(animation_type, w).position(target)

        w.exec(target, animation_type)
        return w

    @classmethod
    def init(
        cls,
        title: str,
        content: str,
        icon: Union[QIcon, str] = None,
        image: Union[str, QPixmap, QImage] = None,
        is_closable=False,
        target: Union[QWidget, QPoint] = None,
        parent=None,
        animation_type: PopoutAnimationType = PopoutAnimationType.SLIDE_UP,
        close_on_delete=True,
    ):
        """Create and show a Popout using the default view.

        Parameters
        ----------
        title: str
            the title of teaching tip

        content: str
            the content of teaching tip

        icon: InfoBarIcon | QIcon | str
            the icon of teaching tip

        image: str | QPixmap | QImage
            the image of teaching tip

        is_closable: bool
            whether to show the close button

        target: QWidget | QPoint
            the target widget or position to show Popout

        parent: QWidget
            parent window

        animation_type: PopoutAnimationType
            Popout animation type

        close_on_delete: bool
            whether delete Popout automatically when Popout is evt_closed
        """
        view = PopoutView(title, content, icon, image, is_closable)
        w = cls._init(view, target, parent, animation_type, close_on_delete)
        view.evt_closed.connect(w.close)
        return w

    def fade_out(self) -> None:
        self.fadeOutAni = QPropertyAnimation(self, b"windowOpacity", self)
        self.fadeOutAni.finished.connect(self.close)
        self.fadeOutAni.setStartValue(1)
        self.fadeOutAni.setEndValue(0)
        self.fadeOutAni.setDuration(120)
        self.fadeOutAni.start()


class PopoutAnimationManager(QObject):
    """Popout animation manager."""

    managers = {}

    def __init__(self, popout: QtPopout):
        super().__init__()
        self._popout = popout
        self.aniGroup = QParallelAnimationGroup(self)
        self.slideAni = QPropertyAnimation(popout, b"pos", self)
        self.opacityAni = QPropertyAnimation(popout, b"windowOpacity", self)

        self.slideAni.setDuration(187)
        self.opacityAni.setDuration(187)

        self.opacityAni.setStartValue(0)
        self.opacityAni.setEndValue(1)

        self.slideAni.setEasingCurve(QEasingCurve.Type.OutQuad)
        self.opacityAni.setEasingCurve(QEasingCurve.Type.OutQuad)
        self.aniGroup.addAnimation(self.slideAni)
        self.aniGroup.addAnimation(self.opacityAni)

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

    def exec(self, pos: QPoint):
        """Start animation."""
        raise NotImplementedError

    def _adjustPosition(self, pos):
        rect = hp.get_current_screen_geometry()
        w, h = self._popout.sizeHint().width() + 5, self._popout.sizeHint().height()
        x = max(rect.left(), min(pos.x(), rect.right() - w))
        y = max(rect.top(), min(pos.y() - 4, rect.bottom() - h + 5))
        return QPoint(x, y)

    def position(self, target: QWidget):
        """Return the top left position relative to the target."""
        raise NotImplementedError

    @classmethod
    def make(cls, animation_type: PopoutAnimationType, popup: QtPopout) -> PopoutAnimationManager:
        """Mask animation manager."""
        if animation_type not in cls.managers:
            raise ValueError(f"`{animation_type}` is an invalid animation type.")

        return cls.managers[animation_type](popup)


@PopoutAnimationManager.register(PopoutAnimationType.SLIDE_UP)
class PullUpPopoutAnimationManager(PopoutAnimationManager):
    """Pull up Popout animation manager."""

    def position(self, target: QWidget):
        w = self._popout
        pos = target.mapToGlobal(QPoint())
        x = pos.x() + target.width() // 2 - w.sizeHint().width() // 2
        y = pos.y() - w.sizeHint().height() + w.layout().contentsMargins().bottom()
        return QPoint(x, y)

    def exec(self, pos: QPoint):
        pos = self._adjustPosition(pos)
        self.slideAni.setStartValue(pos + QPoint(0, 8))
        self.slideAni.setEndValue(pos)
        self.aniGroup.start()


@PopoutAnimationManager.register(PopoutAnimationType.SLIDE_DOWN)
class DropDownPopoutAnimationManager(PopoutAnimationManager):
    """Drop down Popout animation manager."""

    def position(self, target: QWidget):
        w = self._popout
        pos = target.mapToGlobal(QPoint(0, target.height()))
        x = pos.x() + target.width() // 2 - w.sizeHint().width() // 2
        y = pos.y() - w.layout().contentsMargins().top() + 8
        return QPoint(x, y)

    def exec(self, pos: QPoint):
        pos = self._adjustPosition(pos)
        self.slideAni.setStartValue(pos - QPoint(0, 8))
        self.slideAni.setEndValue(pos)
        self.aniGroup.start()


@PopoutAnimationManager.register(PopoutAnimationType.SLIDE_LEFT)
class SlideLeftPopoutAnimationManager(PopoutAnimationManager):
    """Slide left Popout animation manager."""

    def position(self, target: QWidget):
        w = self._popout
        pos = target.mapToGlobal(QPoint(0, 0))
        x = pos.x() - w.sizeHint().width() + 8
        y = pos.y() - w.sizeHint().height() // 2 + target.height() // 2 + w.layout().contentsMargins().top()
        return QPoint(x, y)

    def exec(self, pos: QPoint):
        pos = self._adjustPosition(pos)
        self.slideAni.setStartValue(pos + QPoint(8, 0))
        self.slideAni.setEndValue(pos)
        self.aniGroup.start()


@PopoutAnimationManager.register(PopoutAnimationType.SLIDE_RIGHT)
class SlideRightPopoutAnimationManager(PopoutAnimationManager):
    """Slide right Popout animation manager."""

    def position(self, target: QWidget):
        w = self._popout
        pos = target.mapToGlobal(QPoint(0, 0))
        x = pos.x() + target.width() - 8
        y = pos.y() - w.sizeHint().height() // 2 + target.height() // 2 + w.layout().contentsMargins().top()
        return QPoint(x, y)

    def exec(self, pos: QPoint):
        pos = self._adjustPosition(pos)
        self.slideAni.setStartValue(pos - QPoint(8, 0))
        self.slideAni.setEndValue(pos)
        self.aniGroup.start()


@PopoutAnimationManager.register(PopoutAnimationType.FADE_IN)
class FadeInPopoutAnimationManager(PopoutAnimationManager):
    """Fade in Popout animation manager."""

    def position(self, target: QWidget):
        w = self._popout
        pos = target.mapToGlobal(QPoint())
        x = pos.x() + target.width() // 2 - w.sizeHint().width() // 2
        y = pos.y() - w.sizeHint().height() + w.layout().contentsMargins().bottom()
        return QPoint(x, y)

    def exec(self, pos: QPoint):
        self._popout.move(self._adjustPosition(pos))
        self.aniGroup.removeAnimation(self.slideAni)
        self.aniGroup.start()


@PopoutAnimationManager.register(PopoutAnimationType.NONE)
class DummyPopoutAnimationManager(PopoutAnimationManager):
    """Dummy Popout animation manager."""

    def exec(self, pos: QPoint):
        """Start animation."""
        self._popout.move(self._adjustPosition(pos))

    def position(self, target: QWidget):
        """Return the top left position relative to the target."""
        m = self._popout.hBoxLayout.contentsMargins()
        return target.mapToGlobal(QPoint(-m.left(), -self._popout.sizeHint().height() + m.bottom() - 8))


if __name__ == "__main__":  # pragma: no cover

    def _main():  # type: ignore[no-untyped-def]
        import sys
        from random import choice

        from qtextra.utils.dev import qframe

        app, frame, ha = qframe()

        def _popup():
            QtPopout.init(
                "Hello World",
                "Here is some text that should be displayed below the title",
                parent=frame,
                animation_type=choice(list(PopoutAnimationType)),
                target=btn,
                is_closable=True,
            )

        def _popup2():
            class MyPopoutView(PopoutView):
                def __init__(self, title, content, icon=None, image=None, parent=None):
                    super().__init__(title, content, icon, image, True, parent=parent)
                    self.addWidget(hp.make_btn(self, "Button 1"))
                    self.addWidget(hp.make_btn(self, "Button 2"))
                    self.addWidget(hp.make_btn(self, "Button 3"))

            pop = MyPopoutView(
                "Hello World",
                "Here is some text that should be displayed below the title",
                parent=frame,
            )
            pop.show()

        btn = hp.make_btn(frame, "Show Popout", func=_popup)
        ha.addWidget(btn)
        btn2 = hp.make_btn(frame, "Show Popout with buttons", func=_popup2)
        ha.addWidget(btn2)

        frame.show()
        sys.exit(app.exec_())

    _main()  # type: ignore[no-untyped-call]
