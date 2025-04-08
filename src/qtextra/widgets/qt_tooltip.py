"""tool tip widget."""

from __future__ import annotations

import typing as ty
from enum import Enum

from qtpy.QtCore import QEvent, QObject, QPoint, QPointF, QPropertyAnimation, Qt, QTimer
from qtpy.QtGui import QColor, QIcon, QImage, QPainter, QPainterPath, QPixmap, QPolygonF
from qtpy.QtWidgets import QGraphicsDropShadowEffect, QHBoxLayout, QWidget

import qtextra.helpers as hp
from qtextra.config import THEMES
from qtextra.widgets.qt_popout import PopoutView, PopoutViewBase


class TipPosition(Enum):
    """tool tip tail position."""

    TOP = 0
    BOTTOM = 1
    LEFT = 2
    RIGHT = 3
    TOP_LEFT = 4
    TOP_RIGHT = 5
    BOTTOM_LEFT = 6
    BOTTOM_RIGHT = 7
    LEFT_TOP = 8
    LEFT_BOTTOM = 9
    RIGHT_TOP = 10
    RIGHT_BOTTOM = 11
    NONE = 12


class ImagePosition(Enum):
    """Image position."""

    TOP = 0
    BOTTOM = 1
    LEFT = 2
    RIGHT = 3


class QtToolTipView(PopoutView):
    """tool tip view."""

    def __init__(
        self,
        title: str,
        content: str,
        icon: ty.Union[QIcon, str] = None,
        image: ty.Union[str, QPixmap, QImage] = None,
        is_closable: bool = True,
        tail_position: TipPosition = TipPosition.BOTTOM,
        parent=None,
    ):
        self.manager = ToolTipManager.make(tail_position)
        self.hBoxLayout = QHBoxLayout()
        self.hBoxLayout.setContentsMargins(0, 0, 0, 0)
        super().__init__(title, content, icon, image, is_closable, parent)

    def _adjustImage(self):
        if self.manager._get_image_position() in [ImagePosition.TOP, ImagePosition.BOTTOM]:
            return super()._adjustImage()

        h = self.vBoxLayout.sizeHint().height() - 2
        self.imageLabel.scaledToHeight(h)

    def _addImageToLayout(self):
        self.imageLabel.setHidden(self.imageLabel.isNull())
        pos = self.manager._get_image_position()

        if pos == ImagePosition.TOP:
            self.imageLabel.setBorderRadius(8, 8, 0, 0)
            self.vBoxLayout.insertWidget(0, self.imageLabel)
        elif pos == ImagePosition.BOTTOM:
            self.imageLabel.setBorderRadius(0, 0, 8, 8)
            self.vBoxLayout.addWidget(self.imageLabel)
        elif pos == ImagePosition.LEFT:
            self.vBoxLayout.removeItem(self.vBoxLayout.itemAt(0))
            self.hBoxLayout.addLayout(self.viewLayout)
            self.vBoxLayout.addLayout(self.hBoxLayout)

            self.imageLabel.setBorderRadius(8, 0, 8, 0)
            self.hBoxLayout.insertWidget(0, self.imageLabel)
        elif pos == ImagePosition.RIGHT:
            self.vBoxLayout.removeItem(self.vBoxLayout.itemAt(0))
            self.hBoxLayout.addLayout(self.viewLayout)
            self.vBoxLayout.addLayout(self.hBoxLayout)

            self.imageLabel.setBorderRadius(0, 8, 0, 8)
            self.hBoxLayout.addWidget(self.imageLabel)

    def paintEvent(self, e):
        pass


class ToolTipBubble(QWidget):
    """tool tip bubble."""

    def __init__(self, view: PopoutViewBase, tail_position: TipPosition = TipPosition.BOTTOM, parent=None):
        super().__init__(parent=parent)
        self.manager = ToolTipManager.make(tail_position)
        self.hBoxLayout = QHBoxLayout(self)
        self.view = view

        self.manager._update_layout(self)
        self.hBoxLayout.addWidget(self.view)

    def setView(self, view: QWidget):
        self.hBoxLayout.removeWidget(self.view)
        self.view.deleteLater()
        self.view = view
        self.hBoxLayout.addWidget(view)

    def paintEvent(self, e):
        painter = QPainter(self)
        painter.setRenderHints(QPainter.RenderHint.Antialiasing)

        painter.setBrush(QColor(40, 40, 40) if THEMES.is_dark else QColor(248, 248, 248))
        painter.setPen(QColor(23, 23, 23) if THEMES.is_dark else QColor(0, 0, 0, 17))

        self.manager.draw(self, painter)


class QtToolTip(QWidget):
    """tool tip."""

    def __init__(
        self,
        view: PopoutViewBase,
        target: QWidget,
        duration: int = 1000,
        tail_position: TipPosition = TipPosition.BOTTOM,
        parent=None,
        delete_on_close: bool = True,
    ):
        """
        Parameters
        ----------
        target: QWidget
            the target widget to show tip

        view: PopoutViewBase
            tool tip view

        duration: int
            the time for tool tip to display in milliseconds. If duration is less than zero,
            tool tip will never disappear.

        tail_position: TipPosition
            the position of bubble tail

        parent: QWidget
            parent widget

        delete_on_close: bool
            whether delete flyout automatically when flyout is closed
        """
        super().__init__(parent=parent)
        self.target = target
        self.duration = duration
        self.isDeleteOnClose = delete_on_close
        self.manager = ToolTipManager.make(tail_position)

        self.hBoxLayout = QHBoxLayout(self)
        self.opacity_animation = QPropertyAnimation(self, b"windowOpacity", self)

        self.bubble = ToolTipBubble(view, tail_position, self)

        self.hBoxLayout.setContentsMargins(15, 8, 15, 20)
        self.hBoxLayout.addWidget(self.bubble)
        self.setShadowEffect()

        # set style
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint)

        if parent and parent.window():
            parent.window().installEventFilter(self)

    def setShadowEffect(self, blurRadius=35, offset=(0, 8)):
        """Add shadow to dialog."""
        color = QColor(0, 0, 0, 80 if THEMES.is_dark else 30)
        self.shadowEffect = QGraphicsDropShadowEffect(self.bubble)
        self.shadowEffect.setBlurRadius(blurRadius)
        self.shadowEffect.setOffset(*offset)
        self.shadowEffect.setColor(color)
        self.bubble.setGraphicsEffect(None)
        self.bubble.setGraphicsEffect(self.shadowEffect)

    def _fadeOut(self):
        """Fade out."""
        self.opacity_animation.setDuration(167)
        self.opacity_animation.setStartValue(1)
        self.opacity_animation.setEndValue(0)
        self.opacity_animation.finished.connect(self.close)
        self.opacity_animation.start()

    def showEvent(self, e):
        if self.duration >= 0:
            QTimer.singleShot(self.duration, self._fadeOut)

        self.move(self.manager._get_position(self))
        self.adjustSize()
        self.opacity_animation.setDuration(167)
        self.opacity_animation.setStartValue(0)
        self.opacity_animation.setEndValue(1)
        self.opacity_animation.start()
        super().showEvent(e)

    def closeEvent(self, e):
        if self.isDeleteOnClose:
            self.deleteLater()

        super().closeEvent(e)

    def eventFilter(self, obj, e: QEvent):
        if self.parent() and obj is self.parent().window():
            if e.type() in [QEvent.Type.Resize, QEvent.Type.WindowStateChange, QEvent.Type.Move]:
                self.move(self.manager._get_position(self))

        return super().eventFilter(obj, e)

    def addWidget(self, widget: QWidget, stretch=0, align=Qt.AlignmentFlag.AlignLeft):
        """Add widget to tool tip."""
        self.view.addSpacing(8)
        self.view.addWidget(widget, stretch, align)

    @property
    def view(self):
        return self.bubble.view

    def setView(self, view):
        self.bubble.setView(view)

    @classmethod
    def _init(
        cls,
        view: PopoutViewBase,
        target: QWidget,
        duration=1000,
        tail_position=TipPosition.BOTTOM,
        parent=None,
        delete_on_close=True,
    ):
        """
        Parameters
        ----------
        view: PopoutViewBase
            tool tip view

        target: QWidget
            the target widget to show tip

        duration: int
            the time for tool tip to display in milliseconds. If duration is less than zero,
            tool tip will never disappear.

        tail_position: TipPosition
            the position of bubble tail

        parent: QWidget
            parent widget

        delete_on_close: bool
            whether delete flyout automatically when flyout is closed
        """
        w = cls(view, target, duration, tail_position, parent, delete_on_close)
        w.show()
        return w

    @classmethod
    def init(
        cls,
        target: QWidget,
        title: str,
        content: str,
        icon: ty.Union[QIcon, str] | None = None,
        image: ty.Union[str, QPixmap, QImage] | None = None,
        is_closable: bool = True,
        duration: int = 1000,
        tail_position=TipPosition.BOTTOM,
        parent=None,
        delete_on_close=True,
    ):
        """
        Parameters
        ----------
        target: QWidget
            the target widget to show tip

        title: str
            the title of tool tip

        content: str
            the content of tool tip

        icon:  QIcon | str
            the icon of tool tip

        image: str | QPixmap | QImage
            the image of tool tip

        is_closable: bool
            whether to show the close button

        duration: int
            the time for tool tip to display in milliseconds. If duration is less than zero,
            tool tip will never disappear.
        parent: QWidget
            parent widget
        tail_position: TipPosition
            the position of bubble tail
        delete_on_close: bool
            whether delete flyout automatically when flyout is closed
        """
        view = QtToolTipView(title, content, icon, image, is_closable, tail_position)
        w = cls._init(view, target, duration, tail_position, parent, delete_on_close)
        view.evt_closed.connect(w.close)
        return w


class PopupToolTip(QtToolTip):
    """Pop up tool tip."""

    def __init__(
        self,
        view: PopoutViewBase,
        target: QWidget,
        duration=1000,
        tail_position=TipPosition.BOTTOM,
        parent=None,
        delete_on_close=True,
    ):
        super().__init__(view, target, duration, tail_position, parent, delete_on_close)
        self.setWindowFlags(
            Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint | Qt.WindowType.NoDropShadowWindowHint
        )


class ToolTipManager(QObject):
    """tool tip manager."""

    def __init__(self):
        super().__init__()

    def _update_layout(self, tip: ToolTipBubble):
        """Manage the layout of tip."""
        tip.hBoxLayout.setContentsMargins(0, 0, 0, 0)

    def _get_image_position(self):
        return ImagePosition.TOP

    def _get_position(self, tip: QtToolTip) -> QPoint:
        pos = self._pos(tip)
        rect = hp.get_current_screen_geometry()
        x = max(rect.left(), min(pos.x(), rect.right() - tip.width() - 4))
        y = max(rect.top(), min(pos.y(), rect.bottom() - tip.height() - 4))
        return QPoint(x, y)

    def draw(self, tip: ToolTipBubble, painter: QPainter):
        """Draw the shape of bubble."""
        rect = tip.rect().adjusted(1, 1, -1, -1)
        painter.drawRoundedRect(rect, 8, 8)

    def _pos(self, tip: QtToolTip):
        """Return the poisition of tip."""
        return tip.pos()

    @staticmethod
    def make(position: TipPosition):
        """Mask tool tip manager according to the display position."""
        managers = {
            TipPosition.TOP: TopTailToolTipManager,
            TipPosition.BOTTOM: BottomTailToolTipManager,
            TipPosition.LEFT: LeftTailToolTipManager,
            TipPosition.RIGHT: RightTailToolTipManager,
            TipPosition.TOP_RIGHT: TopRightTailTeachingTipManager,
            TipPosition.BOTTOM_RIGHT: BottomRightTailTeachingTipManager,
            TipPosition.TOP_LEFT: TopLeftTailTeachingTipManager,
            TipPosition.BOTTOM_LEFT: BottomLeftTailTeachingTipManager,
            TipPosition.LEFT_TOP: LeftTopTailTeachingTipManager,
            TipPosition.LEFT_BOTTOM: LeftBottomTailTeachingTipManager,
            TipPosition.RIGHT_TOP: RightTopTailTeachingTipManager,
            TipPosition.RIGHT_BOTTOM: RightBottomTailTeachingTipManager,
            TipPosition.NONE: ToolTipManager,
        }

        if position not in managers:
            raise ValueError(f"`{position}` is an invalid tool tip position.")

        return managers[position]()


class TopTailToolTipManager(ToolTipManager):
    """Top tail tool tip manager."""

    def _update_layout(self, tip):
        tip.hBoxLayout.setContentsMargins(0, 8, 0, 0)

    def _get_image_position(self):
        return ImagePosition.BOTTOM

    def draw(self, tip, painter):
        w, h = tip.width(), tip.height()
        pt = tip.hBoxLayout.contentsMargins().top()

        path = QPainterPath()
        path.addRoundedRect(1, pt, w - 2, h - pt - 1, 8, 8)
        path.addPolygon(QPolygonF([QPointF(w / 2 - 7, pt), QPointF(w / 2, 1), QPointF(w / 2 + 7, pt)]))

        painter.drawPath(path.simplified())

    def _pos(self, tip: QtToolTip):
        target = tip.target
        pos = target.mapToGlobal(QPoint(0, target.height()))
        x = pos.x() + target.width() // 2 - tip.sizeHint().width() // 2
        y = pos.y() - tip.layout().contentsMargins().top()
        return QPoint(x, y)


class BottomTailToolTipManager(ToolTipManager):
    """Bottom tail tool tip manager."""

    def _update_layout(self, tip):
        tip.hBoxLayout.setContentsMargins(0, 0, 0, 8)

    def draw(self, tip, painter):
        w, h = tip.width(), tip.height()
        pb = tip.hBoxLayout.contentsMargins().bottom()

        path = QPainterPath()
        path.addRoundedRect(1, 1, w - 2, h - pb - 1, 8, 8)
        path.addPolygon(QPolygonF([QPointF(w / 2 - 7, h - pb), QPointF(w / 2, h - 1), QPointF(w / 2 + 7, h - pb)]))

        painter.drawPath(path.simplified())

    def _pos(self, tip: QtToolTip):
        target = tip.target
        pos = target.mapToGlobal(QPoint())
        x = pos.x() + target.width() // 2 - tip.sizeHint().width() // 2
        y = pos.y() - tip.sizeHint().height() + tip.layout().contentsMargins().bottom()
        return QPoint(x, y)


class LeftTailToolTipManager(ToolTipManager):
    """Left tail tool tip manager."""

    def _update_layout(self, tip):
        tip.hBoxLayout.setContentsMargins(8, 0, 0, 0)

    def _get_image_position(self):
        return ImagePosition.RIGHT

    def draw(self, tip, painter):
        w, h = tip.width(), tip.height()
        pl = 8

        path = QPainterPath()
        path.addRoundedRect(pl, 1, w - pl - 2, h - 2, 8, 8)
        path.addPolygon(QPolygonF([QPointF(pl, h / 2 - 7), QPointF(1, h / 2), QPointF(pl, h / 2 + 7)]))

        painter.drawPath(path.simplified())

    def _pos(self, tip: QtToolTip):
        target = tip.target
        m = tip.layout().contentsMargins()
        pos = target.mapToGlobal(QPoint(target.width(), 0))
        x = pos.x() - m.left()
        y = pos.y() - tip.view.sizeHint().height() // 2 + target.height() // 2 - m.top()
        return QPoint(x, y)


class RightTailToolTipManager(ToolTipManager):
    """Left tail tool tip manager."""

    def _update_layout(self, tip):
        tip.hBoxLayout.setContentsMargins(0, 0, 8, 0)

    def _get_image_position(self):
        return ImagePosition.LEFT

    def draw(self, tip, painter):
        w, h = tip.width(), tip.height()
        pr = 8

        path = QPainterPath()
        path.addRoundedRect(1, 1, w - pr - 1, h - 2, 8, 8)
        path.addPolygon(QPolygonF([QPointF(w - pr, h / 2 - 7), QPointF(w - 1, h / 2), QPointF(w - pr, h / 2 + 7)]))

        painter.drawPath(path.simplified())

    def _pos(self, tip: QtToolTip):
        target = tip.target
        m = tip.layout().contentsMargins()
        pos = target.mapToGlobal(QPoint(0, 0))
        x = pos.x() - tip.sizeHint().width() + m.right()
        y = pos.y() - tip.view.sizeHint().height() // 2 + target.height() // 2 - m.top()
        return QPoint(x, y)


class TopLeftTailTeachingTipManager(TopTailToolTipManager):
    """Top left tail tool tip manager."""

    def draw(self, tip, painter):
        w, h = tip.width(), tip.height()
        pt = tip.hBoxLayout.contentsMargins().top()

        path = QPainterPath()
        path.addRoundedRect(1, pt, w - 2, h - pt - 1, 8, 8)
        path.addPolygon(QPolygonF([QPointF(20, pt), QPointF(27, 1), QPointF(34, pt)]))

        painter.drawPath(path.simplified())

    def _pos(self, tip: QtToolTip):
        target = tip.target
        pos = target.mapToGlobal(QPoint(0, target.height()))
        x = pos.x() - tip.layout().contentsMargins().left()
        y = pos.y() - tip.layout().contentsMargins().top()
        return QPoint(x, y)


class TopRightTailTeachingTipManager(TopTailToolTipManager):
    """Top right tail tool tip manager."""

    def draw(self, tip, painter):
        w, h = tip.width(), tip.height()
        pt = tip.hBoxLayout.contentsMargins().top()

        path = QPainterPath()
        path.addRoundedRect(1, pt, w - 2, h - pt - 1, 8, 8)
        path.addPolygon(QPolygonF([QPointF(w - 20, pt), QPointF(w - 27, 1), QPointF(w - 34, pt)]))

        painter.drawPath(path.simplified())

    def _pos(self, tip: QtToolTip):
        target = tip.target
        pos = target.mapToGlobal(QPoint(target.width(), target.height()))
        x = pos.x() - tip.sizeHint().width() + tip.layout().contentsMargins().left()
        y = pos.y() - tip.layout().contentsMargins().top()
        return QPoint(x, y)


class BottomLeftTailTeachingTipManager(BottomTailToolTipManager):
    """Bottom left tail tool tip manager."""

    def draw(self, tip, painter):
        w, h = tip.width(), tip.height()
        pb = tip.hBoxLayout.contentsMargins().bottom()

        path = QPainterPath()
        path.addRoundedRect(1, 1, w - 2, h - pb - 1, 8, 8)
        path.addPolygon(QPolygonF([QPointF(20, h - pb), QPointF(27, h - 1), QPointF(34, h - pb)]))

        painter.drawPath(path.simplified())

    def _pos(self, tip: QtToolTip):
        target = tip.target
        pos = target.mapToGlobal(QPoint())
        x = pos.x() - tip.layout().contentsMargins().left()
        y = pos.y() - tip.sizeHint().height() + tip.layout().contentsMargins().bottom()
        return QPoint(x, y)


class BottomRightTailTeachingTipManager(BottomTailToolTipManager):
    """Bottom right tail tool tip manager."""

    def draw(self, tip, painter):
        w, h = tip.width(), tip.height()
        pb = tip.hBoxLayout.contentsMargins().bottom()

        path = QPainterPath()
        path.addRoundedRect(1, 1, w - 2, h - pb - 1, 8, 8)
        path.addPolygon(QPolygonF([QPointF(w - 20, h - pb), QPointF(w - 27, h - 1), QPointF(w - 34, h - pb)]))

        painter.drawPath(path.simplified())

    def _pos(self, tip: QtToolTip):
        target = tip.target
        pos = target.mapToGlobal(QPoint(target.width(), 0))
        x = pos.x() - tip.sizeHint().width() + tip.layout().contentsMargins().left()
        y = pos.y() - tip.sizeHint().height() + tip.layout().contentsMargins().bottom()
        return QPoint(x, y)


class LeftTopTailTeachingTipManager(LeftTailToolTipManager):
    """Left top tail tool tip manager."""

    def _get_image_position(self):
        return ImagePosition.BOTTOM

    def draw(self, tip, painter):
        w, h = tip.width(), tip.height()
        pl = 8

        path = QPainterPath()
        path.addRoundedRect(pl, 1, w - pl - 2, h - 2, 8, 8)
        path.addPolygon(QPolygonF([QPointF(pl, 10), QPointF(1, 17), QPointF(pl, 24)]))

        painter.drawPath(path.simplified())

    def _pos(self, tip: QtToolTip):
        target = tip.target
        m = tip.layout().contentsMargins()
        pos = target.mapToGlobal(QPoint(target.width(), 0))
        x = pos.x() - m.left()
        y = pos.y() - m.top()
        return QPoint(x, y)


class LeftBottomTailTeachingTipManager(LeftTailToolTipManager):
    """Left bottom tail tool tip manager."""

    def _get_image_position(self):
        return ImagePosition.TOP

    def draw(self, tip, painter):
        w, h = tip.width(), tip.height()
        pl = 9

        path = QPainterPath()
        path.addRoundedRect(pl, 1, w - pl - 1, h - 2, 8, 8)
        path.addPolygon(QPolygonF([QPointF(pl, h - 10), QPointF(1, h - 17), QPointF(pl, h - 24)]))

        painter.drawPath(path.simplified())

    def _pos(self, tip: QtToolTip):
        target = tip.target
        m = tip.layout().contentsMargins()
        pos = target.mapToGlobal(QPoint(target.width(), target.height()))
        x = pos.x() - m.left()
        y = pos.y() - tip.sizeHint().height() + m.bottom()
        return QPoint(x, y)


class RightTopTailTeachingTipManager(RightTailToolTipManager):
    """Right top tail tool tip manager."""

    def _get_image_position(self):
        return ImagePosition.BOTTOM

    def draw(self, tip, painter):
        w, h = tip.width(), tip.height()
        pr = 8

        path = QPainterPath()
        path.addRoundedRect(1, 1, w - pr - 1, h - 2, 8, 8)
        path.addPolygon(QPolygonF([QPointF(w - pr, 10), QPointF(w - 1, 17), QPointF(w - pr, 24)]))

        painter.drawPath(path.simplified())

    def _pos(self, tip: QtToolTip):
        target = tip.target
        m = tip.layout().contentsMargins()
        pos = target.mapToGlobal(QPoint(0, 0))
        x = pos.x() - tip.sizeHint().width() + m.right()
        y = pos.y() - m.top()
        return QPoint(x, y)


class RightBottomTailTeachingTipManager(RightTailToolTipManager):
    """Right bottom tail tool tip manager."""

    def _get_image_position(self):
        return ImagePosition.TOP

    def draw(self, tip, painter):
        w, h = tip.width(), tip.height()
        pr = 8

        path = QPainterPath()
        path.addRoundedRect(1, 1, w - pr - 1, h - 2, 8, 8)
        path.addPolygon(QPolygonF([QPointF(w - pr, h - 10), QPointF(w - 1, h - 17), QPointF(w - pr, h - 24)]))

        painter.drawPath(path.simplified())

    def _pos(self, tip: QtToolTip):
        target = tip.target
        m = tip.layout().contentsMargins()
        pos = target.mapToGlobal(QPoint(0, target.height()))
        x = pos.x() - tip.sizeHint().width() + m.right()
        y = pos.y() - tip.sizeHint().height() + m.bottom()
        return QPoint(x, y)


if __name__ == "__main__":  # pragma: no cover

    def _main():  # type: ignore[no-untyped-def]
        import sys
        from random import choice

        from qtextra.utils.dev import qframe

        app, frame, ha = qframe()

        def _popup():
            QtToolTip.init(
                btn,
                title="Title",
                content="Here is some text that should be displayed below the title",
                icon="success",
                parent=frame,
                tail_position=choice(list(TipPosition)),
                is_closable=True,
                duration=3000,
            )

        btn = hp.make_btn(frame, "Show Popout", func=_popup)

        ha.addWidget(btn)
        frame.show()
        sys.exit(app.exec_())

    _main()  # type: ignore[no-untyped-call]
