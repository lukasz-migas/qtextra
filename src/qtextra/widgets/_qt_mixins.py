"""Mixin classes for Qt widgets."""

import time
import typing as ty
from contextlib import contextmanager

import numpy as np
from koyo.timer import report_time
from loguru import logger
from qtpy.QtCore import QPoint, QRect, Qt, QTimer
from qtpy.QtGui import QCursor, QGuiApplication
from qtpy.QtWidgets import QApplication, QLayout, QWidget

import qtextra.helpers as hp


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


class TimerMixin:
    """Timer mixin."""

    def _add_periodic_timer(self, interval: int, fcn, start: bool = True):
        """Create timer to execute some action."""
        timer = QTimer(self)
        timer.setInterval(interval)
        if fcn:
            timer.timeout.connect(fcn)

        if start:
            timer.start()
        logger.debug(f"Added periodic timer event that runs every {interval / 1000}s")
        return timer

    def _add_single_shot_timer(self, delay: int, fcn) -> QTimer:
        timer = QTimer(self)
        timer.singleShot(delay, fcn)
        return timer

    @contextmanager
    def measure_time(self, message: str = "Task took", func: ty.Callable = logger.trace):
        """Measure time."""
        t_start = time.time()
        yield
        func(f"{message} {report_time(t_start)}")


class MinimizeMixin:
    """Mixin class to enable hiding of popup."""

    def _make_hide_handle(self):
        hide_handle = hp.make_qta_btn(self, "minimise", tooltip="Click here to minimize the popup window")
        hide_handle.clicked.connect(self.on_hide)

        handle_layout = self._make_move_handle()
        handle_layout.addWidget(hide_handle)
        return hide_handle, handle_layout

    def on_hide(self):
        """Hide."""
        self.hide()
        self.clearFocus()

    def closeEvent(self, event):
        """Hide."""
        self.on_hide()
        event.ignore()


# noinspection PyUnresolvedReferences
class CloseMixin:
    """Mixin class to enable closing of popup."""

    HIDE_WHEN_CLOSE = False

    def _make_close_handle(self, title: str = ""):
        close_btn = hp.make_qta_btn(self, "cross", tooltip="Click here to close the popup window")
        close_btn.clicked.connect(self.close)

        handle_layout = self._make_move_handle()
        handle_layout.addWidget(close_btn)
        self._title_label.setText(title)
        return close_btn, handle_layout

    def _make_hide_handle(self, title: str = ""):
        self.HIDE_WHEN_CLOSE = True
        return self._make_close_handle(title)


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

    def show_below_mouse(self, show: bool = True, x_offset: int = 0, y_offset: int = -14):
        """Show popup dialog above the mouse cursor position."""
        pos = QCursor().pos()  # mouse position
        sz_hint = self.sizeHint()
        pos -= QPoint(sz_hint.width() - x_offset / 2, y_offset)
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
        from qtextra.widgets.qt_button_clipboard import copy_image_to_clipboard

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


class QtBase(TimerMixin, ScreenshotMixin):
    """Mixin class with common functionality for Dialogs and Tabs."""

    _main_layout = None

    DELAY_CONNECTION = False

    def __init__(self, parent=None, title: str = ""):
        self.logger = logger.bind(src=self.__class__.__name__)
        # Qt stuff
        if hasattr(self, "setWindowTitle"):
            self.setWindowTitle(str(title))
        if hasattr(self, "setAttribute"):
            self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        # Own attributes
        self._parent = parent
        # Make interface
        self.make_gui()
        # Connect signals
        if not self.DELAY_CONNECTION:
            self.connect_events()

    def make_panel(self) -> QLayout:
        """Make panel."""

    def make_gui(self):
        """Make and arrange main panel."""
        layout = self.make_panel()
        if layout is None:
            raise ValueError("Expected layout")
        if not layout.parent() and not self.layout():
            self.setLayout(layout)
        self._main_layout = layout

    def on_apply(self, *args):
        """Update config."""

    def on_teardown(self) -> None:
        """Teardown."""

    def connect_events(self, state: bool = True) -> None:
        """Connect events."""

    def closeEvent(self, event):
        """Hide rather than close."""
        self._on_teardown()
        self.connect_events(False)
        if hasattr(self, "evt_close"):
            self.evt_close.emit()
        self.close()
