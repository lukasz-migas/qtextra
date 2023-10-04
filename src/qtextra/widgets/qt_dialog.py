"""Base dialog."""
import typing as ty
from contextlib import contextmanager

import numpy as np
from loguru import logger
from qtpy.QtCore import QEasingCurve, QPoint, QPropertyAnimation, QRect, QSize, Qt, QTimer, Signal
from qtpy.QtGui import QCursor, QGuiApplication
from qtpy.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QLayout,
    QVBoxLayout,
    QWidget,
)

import qtextra.helpers as hp
from qtextra.config import EVENTS
from qtextra.mixins import CloseMixin, ConfigMixin, DocumentationMixin, IndicatorMixin, TimerMixin

if ty.TYPE_CHECKING:
    from qtextra.widgets.qt_image_button import QtExpandButton
# FIXME: if the user has one screen, make sure the panel is on the correct screen


class ScreenManager:
    """Simple class that handles multi-screen logic."""

    def __init__(self):
        from qtpy.QtWidgets import QApplication

        self.screens = QApplication.screens()
        self.widths = [screen.geometry().width() for screen in self.screens]
        self.width = sum(self.widths)
        self.heights = [screen.geometry().height() for screen in self.screens]
        self.height = sum(self.heights)

    def get_minimum_size(self, width: int, height: int):
        """Get size that is suggested for current screen sizes."""
        self.widths.append(width)
        self.heights.append(height)
        return np.min(self.widths), np.min(self.heights)

    def verify_position(self, point: QPoint, width: int, height: int) -> QPoint:
        """Verify widget position is within the available geometry."""
        x_left, y_top = point.x(), point.y()
        # verify position horizontally
        if x_left < 0:
            x_left = 0
        x_right = x_left + width
        if x_right > self.width:
            x_right = self.width
            x_left = x_right - width
        # verify position vertically
        if y_top < 0:
            y_top = 0
        y_bottom = y_top - height
        if y_bottom > self.height:
            y_bottom = self.height
            y_top = y_bottom - height
        return QPoint(x_left, y_top)


class DialogMixin:
    """Mixin class for dialogs."""

    def show_above_widget(self, widget: QWidget, show: bool = True, y_offset: int = 14, x_offset: int = 0):
        """Show popup dialog above the widget."""
        rect = widget.rect()
        pos = widget.mapToGlobal(QPoint(rect.left() + rect.width() / 2, rect.top()))
        if show:
            self.show()
        sz_hint = self.size()
        pos -= QPoint((sz_hint.width() / 2) + x_offset, sz_hint.height() + y_offset)
        self.move(pos)

    def show_above_mouse(self, show: bool = True):
        """Show popup dialog above the mouse cursor position."""
        pos = QCursor().pos()  # mouse position
        sz_hint = self.sizeHint()
        pos -= QPoint(sz_hint.width() / 2, sz_hint.height() + 14)
        self.move(pos)
        if show:
            self.show()

    def show_below_widget(self, widget: QWidget, show: bool = True, y_offset: int = 14):
        """Show popup dialog above the widget."""
        rect = widget.rect()
        pos = widget.mapToGlobal(QPoint(rect.left() + rect.width() / 2, rect.top()))
        sz_hint = self.size()
        pos -= QPoint(sz_hint.width() / 2, -y_offset)
        self.move(pos)
        if show:
            self.show()

    def show_below_mouse(self, show: bool = True):
        """Show popup dialog above the mouse cursor position."""
        pos = QCursor().pos()  # mouse position
        sz_hint = self.sizeHint()
        pos -= QPoint(sz_hint.width() / 2, -14)
        self.move(pos)
        if show:
            self.show()

    def show_right_of_widget(self, widget: QWidget, show: bool = True, x_offset: int = 14):
        """Show popup dialog above the widget."""
        rect = widget.rect()
        pos = widget.mapToGlobal(QPoint(rect.left() + rect.width() / 2, rect.top()))
        sz_hint = self.size()
        pos -= QPoint(-x_offset, sz_hint.height() / 4)
        self.move(pos)
        if show:
            self.show()

    def show_right_of_mouse(self, show: bool = True):
        """Show popup dialog on the right hand side of the mouse cursor position."""
        pos = QCursor().pos()  # mouse position
        sz_hint = self.sizeHint()
        pos -= QPoint(-14, sz_hint.height() / 4)
        self.move(pos)
        if show:
            self.show()

    def show_left_of_widget(self, widget: QWidget, show: bool = True, x_offset: int = 14):
        """Show popup dialog above the widget."""
        rect = widget.rect()
        pos = widget.mapToGlobal(QPoint(rect.left(), rect.top()))
        sz_hint = self.size()
        pos -= QPoint(sz_hint.width() + x_offset, sz_hint.height() / 4)
        self.move(pos)
        if show:
            self.show()

    def show_left_of_mouse(self, show: bool = True):
        """Show popup dialog on the left hand side of the mouse cursor position."""
        pos = QCursor().pos()  # mouse position
        sz_hint = self.sizeHint()
        pos -= QPoint(sz_hint.width() + 14, sz_hint.height() / 4)
        self.move(pos)
        if show:
            self.show()

    def set_on_widget(self, widget: QWidget, x_mult: float = 2.5, y_mult: float = 0.0):
        """Set position of the popup above the widget."""
        # calculate position information about the widget
        widget_rect = widget.rect()
        widget_pos = widget.mapToGlobal(QPoint(widget_rect.left(), widget_rect.top()))
        widget_width = widget.width()

        # calculate sizing of the window
        rect = self.rect()
        x_pos = widget_pos.x() + widget_width + rect.width() * x_mult
        y_pos = widget_pos.y() + rect.height() * y_mult
        pos = QPoint(x_pos, y_pos)

        m = ScreenManager()
        pos = m.verify_position(pos, rect.width(), rect.height())
        self.move(pos)

    def set_on_mouse(self, x_mult: float = 2.5, y_mult: float = 0.0):
        """Set on mouse position."""
        pos = QCursor.pos()
        rect = self.rect()
        pos = QPoint(pos.x() - rect.width() * x_mult, pos.y() - rect.height() * y_mult)

        m = ScreenManager()
        pos = m.verify_position(pos, rect.width(), rect.height())
        self.move(pos)

    def center_on_screen(self, show: bool = False):
        """Center dialog on screen."""
        screen = QApplication.desktop().screenGeometry()
        x = (screen.width() - self.width()) / 2
        y = (screen.height() - self.height()) / 2
        self.move(x, y)
        if show:
            self.show()

    def center_on_parent(self, show: bool = False):
        """Center on parent."""
        parent = self.parent()
        if not parent:
            self.center_on_screen()
        else:
            screen = parent.geometry()
            x = (screen.width() - self.width()) / 2
            y = (screen.height() - self.height()) / 2
            self.move(x, y)
        if show:
            self.show()

    def move_to(self, position="top", *, win_ratio=0.9, min_length=0):
        """Move popup to a position relative to the QMainWindow.

        Parameters
        ----------
        position : {str, tuple}, optional
            position in the QMainWindow to show the pop, by default 'top'
            if str: must be one of {'top', 'bottom', 'left', 'right' }
            if tuple: must be length 4 with (left, top, width, height)
        win_ratio : float, optional
            Fraction of the width (for position = top/bottom) or height (for
            position = left/right) of the QMainWindow that the popup will
            occupy.  Only valid when isinstance(position, str).
            by default 0.9
        min_length : int, optional
            Minimum size of the long dimension (width for top/bottom or
            height fort left/right).

        Raises
        ------
        ValueError
            if position is a string and not one of
            {'top', 'bottom', 'left', 'right' }
        """
        if isinstance(position, str):
            window = self.parent().window() if self.parent() else None
            if not window:
                raise ValueError(
                    "Specifying position as a string is only possible if the popup has a parent",
                )
            left = window.pos().x()
            top = window.pos().y()
            if position in ("top", "bottom"):
                width = window.width() * win_ratio
                width = max(width, min_length)
                left += (window.width() - width) / 2
                height = self.sizeHint().height()
                top += 24 if position == "top" else (window.height() - height - 12)
            elif position in ("left", "right"):
                height = window.height() * win_ratio
                height = max(height, min_length)
                # 22 is for the title bar
                top += 22 + (window.height() - height) / 2
                width = self.sizeHint().width()
                left += 12 if position == "left" else (window.width() - width - 12)
            else:
                raise ValueError(
                    'position must be one of ["top", "left", "bottom", "right"]',
                )
        elif isinstance(position, (tuple, list)):
            assert len(position) == 4, "`position` argument must have length 4"
            left, top, width, height = position
        else:
            raise ValueError(
                f"Wrong type of position {position}",
            )

        # necessary for transparent round corners
        self.resize(self.sizeHint())
        # make sure the popup is completely on the screen
        # In Qt ≥5.10 we can use screenAt to know which monitor the mouse is on

        if hasattr(QGuiApplication, "screenAt"):
            screen_geometry: QRect = QGuiApplication.screenAt(QCursor.pos()).geometry()
        else:
            # This widget is deprecated since Qt 5.11
            from qtpy.QtWidgets import QDesktopWidget

            screen_num = QDesktopWidget().screenNumber(QCursor.pos())
            screen_geometry = QGuiApplication.screens()[screen_num].geometry()

        left = max(min(screen_geometry.right() - width, left), screen_geometry.left())
        top = max(min(screen_geometry.bottom() - height, top), screen_geometry.top())
        self.setGeometry(left, top, width, height)

    def move_to_widget(self, widget: QWidget, position: str = "right"):
        """Move tutorial to specified widget."""
        x_pad, y_pad = 5, 5
        size = self.size()
        rect = widget.rect()
        if position == "left":
            x = rect.left() - size.width() - x_pad
            y = rect.center().y() - (size.height() * 0.5)
        elif position == "right":
            x = rect.right() + x_pad
            y = rect.center().y() - (size.height() * 0.5)
        elif position == "top":
            x = rect.center().x() - (size.width() * 0.5)
            y = rect.top() - size.height() - y_pad
        elif position == "bottom":
            x = rect.center().x() - (size.width() * 0.5)
            y = rect.bottom() + y_pad
        pos = widget.mapToGlobal(QPoint(x, y))
        self.move(pos)


class ScreenshotMixin:
    """Mixin class for taking screenshots."""

    @contextmanager
    def run_with_screenshot(self):
        """Must implement."""
        yield

    def _screenshot(self):
        return self.grab().toImage()

    def to_screenshot(self):
        """Get screenshot."""
        from napari._qt.dialogs.screenshot_dialog import ScreenshotDialog

        dialog = ScreenshotDialog(self.screenshot, self, history=[])
        if dialog.exec_():
            pass

    def screenshot(self, path: ty.Optional[str] = None):
        """Take screenshot of the viewer."""
        from napari._qt.utils import QImg2array

        with self.run_with_screenshot():
            img = self._screenshot()
        if path is not None:
            from skimage.io import imsave

            imsave(path, QImg2array(img))
        return QImg2array(img)

    def clipboard(self):
        """Take screenshot af the viewer and put it in the clipboard."""
        from qtextra.widgets.qt_clipboard_button import copy_image_to_clipboard

        with self.run_with_screenshot():
            img = self._screenshot()
        copy_image_to_clipboard(img)
        hp.add_flash_animation(self)

    def _get_save_screenshot_menu(self):
        """Get normalization menu."""
        menu = hp.make_menu(self)
        menu_save = hp.make_menu_item(self, "Save screenshot to file...", menu=menu)
        menu_save.triggered.connect(self.to_screenshot)
        menu_clip = hp.make_menu_item(self, "Copy screenshot to clipboard", menu=menu)
        menu_clip.triggered.connect(self.clipboard)
        return menu


class QtBase(ConfigMixin, DocumentationMixin, IndicatorMixin, TimerMixin, ScreenshotMixin):
    """Mixin class with common functionality for Dialogs and Tabs."""

    _main_layout = None
    _title = ""

    def __init__(self, parent=None, title: str = "", delay: bool = False):
        self.logger = logger.bind(src=self.__class__.__name__)
        # Qt stuff
        if hasattr(self, "setWindowTitle"):
            self.setWindowTitle(QApplication.translate(str(self), self._title or title, None, -1))
        if hasattr(self, "setAttribute"):
            self.setAttribute(Qt.WA_DeleteOnClose)
        # Own attributes
        self._parent = parent
        # Make interface
        self.make_gui()
        # Update values
        self.on_set_from_config()
        # Connect signals
        if not delay:
            self.connect_events()

    def make_panel(self) -> QLayout:
        """Make panel."""

    def make_gui(self):
        """Make and arrange main panel."""
        layout = self.make_panel()
        if layout is None:
            raise ValueError("Expected layout")
        if not layout.parent():
            self.setLayout(layout)
        self._main_layout = layout

    def on_apply(self, *args):
        """Update config."""

    def _on_teardown(self):
        """Teardown."""

    def connect_events(self, state: bool = True):
        """Connect events."""

    def closeEvent(self, event):
        """Hide rather than close."""
        self._on_teardown()
        self.connect_events(False)
        if hasattr(self, "evt_close"):
            self.evt_close.emit()
        self.close()


class QtTab(QWidget, QtBase):
    """Dialog base class."""

    _description: ty.Dict = None
    _tab_index: ty.Optional[ty.Dict] = None

    def __init__(self, parent, title: str = "Panel"):
        QWidget.__init__(self, parent)
        QtBase.__init__(self, parent, title)

    def _make_html_description(self) -> str:
        """Make nicely formatted description that can be used in tooltip information."""
        if not self._description:
            return ""
        return f"<p style='white-space:pre'><h2>{self._description.get('title', 'Panel')}</h2></p>"
        # return f"<p style''white-space:pre'><h2><b>{self._description.get('title', 'Panel')}</b></h2></p>"
        # return f"""
        # <h2><b>{self._description.get("title", "Panel")}</b></h2>
        # <h3><b>Description</b></h3>
        # {self._description.get("description", "")}
        # """

    def _make_html_metadata(self) -> ty.Tuple[str, str, str]:
        """Make nicely formatted description that can be used to provide help information about widget."""
        if not self._description:
            return "", "", ""
        return (
            self._description.get("title", "Panel"),
            self._description.get("description", ""),
            self._description.get("docs", ""),
        )


class QtDialog(QDialog, DialogMixin, QtBase, CloseMixin):
    """Dialog base class."""

    _main_layout = None

    # events
    evt_resized = Signal()
    evt_close = Signal()

    def __init__(self, parent=None, title: str = "Dialog", delay: bool = False):
        QDialog.__init__(self, parent)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
        QtBase.__init__(self, parent, title, delay=delay)

        EVENTS.evt_force_exit.connect(self.close)

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
    _title_label: QLabel
    _old_window_pos, _move_handle = None, None

    def __init__(
        self,
        parent: ty.Optional[QWidget],
        title: str = "",
        position: ty.Any = None,
        flags: ty.Any = Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Popup,
    ):
        super().__init__(parent, title)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setWindowFlags(flags)
        if position is not None:
            self.move(position)

    def _make_title_handle(self, title: str = "") -> QHBoxLayout:
        """Make handle button that helps move the window around."""
        self._title_label = hp.make_label(self, title, bold=True, alignment=Qt.AlignLeft | Qt.AlignVCenter)

        layout = hp.make_hbox_layout(spacing=0)
        layout.addWidget(self._title_label)
        layout.addStretch(1)
        self._title_layout = layout
        return layout

    def _make_move_handle(self, title: str = "") -> QHBoxLayout:
        """Make handle button that helps move the window around."""
        self._title_label = hp.make_label(self, title, bold=True, alignment=Qt.AlignLeft | Qt.AlignVCenter)
        self._move_handle = hp.make_qta_label(
            self, "move_handle", tooltip="Click here and drag the mouse around to move the window."
        )
        self._move_handle.setCursor(Qt.PointingHandCursor)

        layout = hp.make_hbox_layout(spacing=0)
        layout.addWidget(self._title_label)
        layout.addStretch(1)
        layout.addWidget(self._move_handle)
        self._title_layout = layout
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
            super().closeEvent(event)

    def close(self) -> bool:
        """Hide dialog rather than delete it."""
        if self.HIDE_WHEN_CLOSE:
            self.hide()
            self.clearFocus()
            return False
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
    ):
        super().__init__(parent, title, position, flags)


class QtCollapsibleFramelessTool(QtFramelessTool):
    """Collapsible tool."""

    GEOM_TIME = 250

    expand_btn: "QtExpandButton"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.timer = QTimer()
        self.geom_anim = QPropertyAnimation(self, b"geometry", self)

    def mousePressEvent(self, event):
        """Mouse press event."""
        event.ignore()

    def closeEvent(self, event):
        """Cannot close popup."""
        event.ignore()

    @property
    def is_expanded(self) -> bool:
        """Checks whether text is expanded."""
        return self.property("expanded")

    def toggle_expansion(self):
        """Toggle the expanded state of the notification frame."""
        self.contract() if self.is_expanded else self.expand()
        self.timer.stop()

    def expand(self):
        """Expanded widget to maximum size."""
        sz = self.parent().size() - QSize(self.size().width(), self.parent().size().height())
        self.geom_anim.setDuration(self.GEOM_TIME)
        self.geom_anim.setStartValue(self.geometry())
        size = self.maximumSize()
        self.geom_anim.setEndValue(
            QRect(
                sz.width() - size.width() + self.minimumSize().width() - 20,
                sz.height() + 20,
                size.width(),
                size.height(),
            )
        )
        self.geom_anim.setEasingCurve(QEasingCurve.OutQuad)
        self.geom_anim.start()
        self.expand_btn.expanded = True
        self.setProperty("expanded", True)
        self._widget.show()

    def contract(self):
        """Contract widget to minimum size."""
        sz = self.parent().size() - QSize(self.size().width(), self.parent().size().height())
        self.geom_anim.setDuration(self.GEOM_TIME)
        self.geom_anim.setStartValue(self.geometry())
        size = self.minimumSize()
        self.geom_anim.setEndValue(
            QRect(
                sz.width() + self.maximumSize().width() - size.width() - 20,
                sz.height() + 20,
                size.width(),
                size.height(),
            )
        )
        self.geom_anim.setEasingCurve(QEasingCurve.OutQuad)
        self.geom_anim.start()
        self.expand_btn.expanded = False
        self.setProperty("expanded", False)
        hp.polish_widget(self.expand_btn)
        self._widget.hide()

    def move_to_top_right(self, offset=(-20, 20)):
        """Position widget at the top right edge of the parent."""
        if not self.parent():
            return
        sz = self.parent().size() - QSize(self.size().width(), self.parent().size().height()) + QSize(*offset)
        self.move(QPoint(sz.width(), sz.height()))

    def move_to_bottom_right(self, offset=(20, 20)):
        """Position widget at the top right edge of the parent."""
        if not self.parent():
            return
        sz = self.parent().size() - self.size() - QSize(*offset)
        # sz = self.parent().size() - QSize(self.size().width(), self.parent().size().height()) + QSize(*offset)
        self.move(QPoint(sz.width(), sz.height()))


class QtTransparentPopup(QDialog, DialogMixin):
    """A generic popup window.

    The seemingly extra frame here is to allow rounded corners on a truly
    transparent background.  New items should be added to QtPopup.frame

    +----------------------------------
    | Dialog
    |  +-------------------------------
    |  | QVBoxLayout
    |  |  +----------------------------
    |  |  | QFrame
    |  |  |  +-------------------------
    |  |  |  |
    |  |  |  |  (add a new layout here)

    Parameters
    ----------
    parent : qtpy.QtWidgets:QWidget
        Parent widget of the popup dialog box.

    Attributes
    ----------
    frame : qtpy.QtWidgets.QFrame
        Frame of the popup dialog box.
    layout : qtpy.QtWidgets.QVBoxLayout
        Layout of the popup dialog box.
    """

    def __init__(self, parent):
        super().__init__(parent)
        self.setObjectName("QtModalPopup")
        self.setModal(False)  # if False, then clicking anywhere else closes it
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        self.setLayout(QVBoxLayout())

        self.frame = QFrame()
        self.frame.setObjectName("QtPopupFrame")
        self.layout().addWidget(self.frame)
        self.layout().setContentsMargins(0, 0, 0, 0)

        EVENTS.evt_force_exit.connect(self.close)

    def keyPressEvent(self, event):
        """Close window on return, else pass event through to super class.

        Parameters
        ----------
        event : qtpy.QtCore.QEvent
            Event from the Qt context.
        """
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            return self.close()
        super().keyPressEvent(event)


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
