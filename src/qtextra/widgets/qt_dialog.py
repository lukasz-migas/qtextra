"""Qt dialog widgets."""
from qtpy.QtCore import QEasingCurve, QPoint, QPropertyAnimation, QSize, Qt, Signal
from qtpy.QtWidgets import QDialog, QGraphicsOpacityEffect, QHBoxLayout

import qtextra.helpers as hp
from qtextra.widgets._qt_mixins import CloseMixin, DialogMixin, QtBase


class QtDialog(QDialog, DialogMixin, QtBase, CloseMixin):
    """Dialog base class."""

    _main_layout = None

    # events
    evt_resized = Signal()
    evt_close = Signal()

    def __init__(self, parent=None, title: str = "Dialog"):
        QDialog.__init__(self, parent)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
        QtBase.__init__(self, parent, title)

    def is_valid_(self) -> bool:
        """Check whether object is valid."""
        try:
            self.isVisible()
        except RuntimeError:
            return False
        return True

    def resizeEvent(self, event):
        """Resize event."""
        self.evt_resized.emit()
        return super().resizeEvent(event)


class QtFramelessPopup(QtDialog, CloseMixin):
    """Frameless dialog."""

    # attributes used to move windows around
    _title_label, _old_window_pos, _move_handle = None, None, None

    def __init__(
        self,
        parent,
        title="",
        position=None,
        flags=Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Popup,
    ):
        super().__init__(parent, title)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setWindowFlags(flags)
        if position is not None:
            self.move(position)

    def _make_move_handle(self) -> QHBoxLayout:
        """Make handle button that helps move the window around."""
        self._title_label = hp.make_label(self, "", bold=True, alignment=Qt.AlignLeft | Qt.AlignVCenter)
        self._move_handle = hp.make_qta_label(
            self, "move_handle", tooltip="Click here and drag the mouse around to move the window."
        )
        self._move_handle.setCursor(Qt.PointingHandCursor)

        layout = hp.make_hbox_layout(spacing=0)
        layout.addWidget(self._title_label)
        layout.addStretch(1)
        layout.addWidget(self._move_handle)
        return layout

    def mousePressEvent(self, event):
        """Mouse press event."""
        super().mousePressEvent(event)
        # allow movement of the window when user uses right-click and the move handle button does not exist
        if event.button() == Qt.RightButton:  # and self._move_handle is None:
            self._old_window_pos = event.x(), event.y()
        elif self._move_handle is None:
            self._old_window_pos = None
        elif self.childAt(event.pos()) == self._move_handle:
            self._old_window_pos = event.x(), event.y()

    def mouseMoveEvent(self, event):
        """Mouse move event - ensures its possible to move the window to new location."""
        super().mouseMoveEvent(event)
        if self._old_window_pos is not None:
            self.move(event.globalX() - self._old_window_pos[0], event.globalY() - self._old_window_pos[1])

    def mouseReleaseEvent(self, event):
        """Mouse release event."""
        super().mouseReleaseEvent(event)
        self._old_window_pos = None

    def disable_while_open(self, *widgets):
        """Disable widgets while the window is open."""
        self.evt_close.connect(lambda: hp.disable_widgets(*widgets, disabled=False))
        hp.disable_widgets(*widgets, disabled=True)

    def closeEvent(self, event):
        """Hide rather than close."""
        if self.HIDE_WHEN_CLOSE:
            self.hide()
            self.clearFocus()
            event.ignore()
        else:
            self._on_teardown()
            self.connect_events(False)
            if hasattr(self, "evt_close"):
                self.evt_close.emit()
            self.logger.debug("Teardown")
            super().closeEvent(event)

    def close(self):
        """Hide dialog rather than delete it."""
        if self.HIDE_WHEN_CLOSE:
            self.hide()
            self.clearFocus()
        else:
            super().close()


class QtFramelessTool(QtFramelessPopup):
    """Frameless dialog that stays on top."""

    def __init__(
        self,
        parent,
        title: str = "",
        position=None,
        flags=Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool,
        delay: bool = False,
    ):
        super().__init__(parent, title, position, flags, delay)


class SubWindowBase(QDialog):
    """Sub-window mixin."""

    # Animation attributes
    FADE_IN_RATE = 220
    FADE_OUT_RATE = 120
    MAX_OPACITY = 0.9
    # Window attributes
    MIN_WIDTH = 250
    MAX_WIDTH = 350
    MIN_HEIGHT = 40

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setWindowFlags(Qt.SubWindow)
        self.setSizeGripEnabled(False)
        self.setModal(False)
        self.setMouseTracking(True)

        self.setMinimumWidth(self.MIN_WIDTH)
        self.setMaximumWidth(self.MAX_WIDTH)
        self.setMinimumHeight(self.MIN_HEIGHT)

        # opacity effect
        self.opacity = QGraphicsOpacityEffect()
        self.setGraphicsEffect(self.opacity)
        self.opacity_anim = QPropertyAnimation(self.opacity, b"opacity", self)
        # geometry effect
        self.geom_anim = QPropertyAnimation(self, b"geometry", self)

    def move_to(self, location):
        """Move to location."""
        if location == "top_right":
            self.move_to_top_right()
        elif location == "top_left":
            self.move_to_top_left()
        elif location == "bottom_right":
            self.move_to_bottom_right()
        elif location == "bottom_left":
            self.move_to_bottom_left()

    def move_to_top_right(self, offset=(-10, 10)):
        """Position widget at the top right edge of the parent."""
        if not self.parent():
            return
        psz = self.parent().size()
        sz = psz - QSize(self.size().width(), psz.height()) + QSize(*offset)
        self.move(QPoint(sz.width(), sz.height()))

    def move_to_bottom_right(self, offset=(8, 8)):
        """Position widget at the bottom right edge of the parent."""
        if not self.parent():
            return
        sz = self.parent().size() - self.size() - QSize(*offset)
        self.move(QPoint(sz.width(), sz.height()))

    def move_to_top_left(self, offset=(8, 8)):
        """Position widget at the bottom right edge of the parent."""
        if not self.parent():
            return
        self.move(QPoint(*offset))

    def move_to_bottom_left(self, offset=(8, 8)):
        """Position widget at the bottom right edge of the parent."""
        if not self.parent():
            return
        sz = self.parent().size() - self.size()
        self.move(QPoint(offset[0], sz.height() - offset[1]))

    def slide_in(self):
        """Run animation that fades in the dialog with a slight slide up."""
        geom = self.geometry()
        self.geom_anim.setDuration(self.FADE_IN_RATE)
        self.geom_anim.setStartValue(geom.translated(0, -20))
        self.geom_anim.setEndValue(geom)
        self.geom_anim.setEasingCurve(QEasingCurve.OutQuad)
        # fade in
        self.opacity_anim.setDuration(self.FADE_IN_RATE)
        self.opacity_anim.setStartValue(0)
        self.opacity_anim.setEndValue(self.MAX_OPACITY)
        self.geom_anim.start()
        self.opacity_anim.start()

    def fade_in(self):
        """Run animation that fades in the dialog."""
        self.opacity_anim.setDuration(self.FADE_IN_RATE)
        self.opacity_anim.setStartValue(0)
        self.opacity_anim.setEndValue(self.MAX_OPACITY)
        self.opacity_anim.start()

    def fade_out(self):
        """Run animation that fades out the dialog."""
        self.opacity_anim.setDuration(self.FADE_OUT_RATE)
        self.opacity_anim.setStartValue(self.MAX_OPACITY)
        self.opacity_anim.setEndValue(0)
        self.opacity_anim.start()

    def close(self):
        """Fade out then close."""
        try:
            super().close()
        except (RuntimeError, TypeError):
            pass
