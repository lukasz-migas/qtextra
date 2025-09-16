"""Base dialog."""

from __future__ import annotations

import typing as ty
from contextlib import contextmanager, suppress

import numpy as np
from loguru import logger
from qtpy.QtCore import (  # type: ignore[attr-defined]
    QEasingCurve,
    QObject,
    QPoint,
    QPropertyAnimation,
    QRect,
    QSize,
    Qt,
    QTimer,
    Signal,
)
from qtpy.QtGui import QCloseEvent, QCursor, QGuiApplication, QKeyEvent, QMouseEvent, QResizeEvent
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
    from qtextra.widgets.qt_button_icon import QtExpandButton


class ScreenManager:
    """Simple class that handles multi-screen logic."""

    def __init__(self) -> None:
        from qtpy.QtWidgets import QApplication

        self.screens = QApplication.screens()
        self.widths = [screen.geometry().width() for screen in self.screens]
        self.width = sum(self.widths)
        self.heights = [screen.geometry().height() for screen in self.screens]
        self.height = max(self.heights)

    @classmethod
    def get_minimum_size(cls, width: int, height: int) -> tuple[int, int]:
        """Get size that is suggested for current screen sizes."""
        obj = cls()
        obj.widths.append(width)
        obj.heights.append(height)
        return np.min(obj.widths), np.min(obj.heights)

    @classmethod
    def trim_size(cls, width: int, height: int) -> tuple[int, int]:
        """Trim size of widget/dialog so that it's never bigger than the screen size."""
        obj = cls()
        width = min(width, obj.width)
        height = min(height, obj.height)
        return width, height

    @classmethod
    def verify_position(cls, point: QPoint, width: int, height: int) -> QPoint:
        """Verify widget position is within the available geometry."""
        obj = cls()
        x_left, y_top = point.x(), point.y()
        # verify position horizontally
        if x_left < 0:
            x_left = 0
        x_right = x_left + width
        if x_right > obj.width:
            x_right = obj.width
            x_left = x_right - width
        # verify position vertically
        if y_top < 0:
            y_top = 0
        y_bottom = y_top - height
        if y_bottom > obj.height:
            y_bottom = obj.height
            y_top = y_bottom - height
        return QPoint(x_left, y_top)


class DialogMixin:
    """Mixin class for dialogs."""

    def show_on_mouse(self, show: bool = True) -> None:
        """Show popup dialog in the center of mouse cursor position."""
        hp.show_on_mouse(self, show)

    def show_right_of_mouse(self, show: bool = True, x_offset: int = 0, y_offset: int = 0) -> None:
        """Show popup dialog on the right-hand side of the mouse cursor position."""
        hp.show_right_of_mouse(self, show, x_offset=x_offset, y_offset=y_offset)

    def show_left_of_mouse(self, show: bool = True, x_offset: int = 0, y_offset: int = 0) -> None:
        """Show popup dialog on the left-hand side of the mouse cursor position."""
        hp.show_left_of_mouse(self, show, x_offset=x_offset, y_offset=y_offset)

    def show_above_mouse(self, show: bool = True, x_offset: int = 0, y_offset: int = 0) -> None:
        """Show popup dialog above the mouse cursor position."""
        hp.show_above_mouse(self, show, x_offset=x_offset, y_offset=y_offset)

    def show_below_mouse(self, show: bool = True, x_offset: int = 0, y_offset: int = -0) -> None:
        """Show popup dialog above the mouse cursor position."""
        hp.show_below_mouse(self, show, x_offset=x_offset, y_offset=y_offset)

    def show_in_center_of_screen(self, show: bool = True) -> None:
        """Show dialog in the center of the widget."""
        hp.show_in_center_of_screen(self, show)

    def show_in_center_of_widget(self, widget: QWidget, show: bool = True) -> None:
        """Show dialog in the center of the widget."""
        hp.show_in_center_of_widget(self, widget, show)

    def show_above_widget(self, parent: QWidget, show: bool = True, x_offset: int = 0, y_offset: int = 0) -> None:
        """Show popup dialog above the widget."""
        hp.show_above_widget(self, parent, show, x_offset=x_offset, y_offset=y_offset)

    def show_below_widget(self, parent: QWidget, show: bool = True, x_offset: int = 0, y_offset: int = 0) -> None:
        """Show popup dialog below the widget."""
        hp.show_below_widget(self, parent, show, x_offset=x_offset, y_offset=y_offset)

    def show_right_of_widget(self, parent: QWidget, show: bool = True, x_offset: int = 0, y_offset: int = 0) -> None:
        """Show popup dialog right of the widget."""
        hp.show_right_of_widget(self, parent, show, x_offset=x_offset, y_offset=y_offset)

    def show_left_of_widget(
        self, parent: QObject | None, show: bool = True, x_offset: int = 0, y_offset: int = 0
    ) -> None:
        """Show popup dialog left of the widget."""
        hp.show_left_of_widget(self, parent, show, x_offset=x_offset, y_offset=y_offset)

    def move_to(self, position="top", *, win_ratio=0.9, min_length=0) -> None:
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

    def move_to_widget(self, widget: QWidget, position: str = "right") -> None:
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
        pos = widget.mapToGlobal(QPoint(int(x), int(y)))
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

    def on_show_save_screenshot_menu(self):
        """Get normalization menu."""
        menu = hp.make_menu(self)
        menu_save = hp.make_menu_item(self, "Save screenshot to file...", menu=menu)
        menu_save.triggered.connect(self.to_screenshot)
        menu_clip = hp.make_menu_item(self, "Copy screenshot to clipboard", menu=menu)
        menu_clip.triggered.connect(self.clipboard)
        hp.show_menu(menu)


class QtBase(ConfigMixin, DocumentationMixin, IndicatorMixin, TimerMixin, ScreenshotMixin):
    """Mixin class with common functionality for Dialogs and Tabs."""

    _is_init = False
    _main_layout = None
    _title = ""

    DELAY_CONNECTION: ty.ClassVar[bool] = False
    setLayout: ty.Callable[[QLayout], None]

    def __init__(self, parent: QWidget | None = None, title: str = "", delay: bool = False):
        if self._is_init:
            return

        self.logger = logger.bind(src=self.__class__.__name__)
        # Qt stuff
        if hasattr(self, "setWindowTitle"):
            self.setWindowTitle(QApplication.translate(str(self), self._title or title, None, -1))
        if hasattr(self, "setAttribute"):
            self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        # Own attributes
        self._parent = parent
        # Make interface
        self.make_gui()
        # Update values
        self.on_set_from_config()
        # Connect signals
        if not delay and not self.DELAY_CONNECTION:
            self.connect_events()
        self._is_init = True

    def make_panel(self) -> QLayout:
        """Make panel."""
        raise NotImplementedError("Must implement method")

    def make_gui(self) -> None:
        """Make and arrange main panel."""
        layout = self.make_panel()
        if layout is None:
            raise ValueError("Expected layout")
        if not layout.parent():
            self.setLayout(layout)
        self._main_layout = layout

    def on_apply(self, *args: ty.Any) -> None:
        """Update config."""

    def _on_teardown(self) -> None:
        """Teardown."""

    def connect_events(self, state: bool = True) -> None:
        """Connect events."""

    def closeEvent(self, event: QCloseEvent | None) -> None:
        """Hide rather than close."""
        self._on_teardown()
        self.connect_events(False)
        if hasattr(self, "evt_close"):
            self.evt_close.emit()
        self.close()


class QtTab(QWidget, QtBase):  # type: ignore[misc]
    """Dialog base class."""

    _description: dict | None = None
    _tab_index: dict | None = None

    def __init__(self, parent: QWidget | None, title: str = "Panel"):
        QWidget.__init__(self, parent)
        QtBase.__init__(self, parent, title)

    def _make_html_description(self) -> str:
        """Make nicely formatted description that can be used in tooltip information."""
        if not self._description:
            return ""
        return f"<p style='white-space:pre'><h2>{self._description.get('title', 'Panel')}</h2></p>"

    def _make_html_metadata(self) -> ty.Tuple[str, str, str]:
        """Make nicely formatted description that can be used to provide help information about widget."""
        if not self._description:
            return "", "", ""
        return (
            self._description.get("title", "Panel"),
            self._description.get("description", ""),
            self._description.get("docs", ""),
        )


class QtDialog(QDialog, DialogMixin, QtBase, CloseMixin):  # type: ignore[misc]
    """Dialog base class."""

    _main_layout: QLayout | None = None

    # events
    evt_resized = Signal()
    evt_hide = Signal()
    evt_close = Signal()

    def __init__(self, parent: QWidget | None = None, title: str = "Dialog", delay: bool = False):
        QDialog.__init__(self, parent)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        QtBase.__init__(self, parent, title, delay=delay)

        EVENTS.evt_force_exit.connect(self.close)

    def is_valid_(self) -> bool:
        """Check whether object is valid."""
        try:
            self.isVisible()
        except RuntimeError:
            return False
        return True

    def resizeEvent(self, event: QResizeEvent) -> None:  # type: ignore[override]
        """Resize event."""
        self.evt_resized.emit()
        return super().resizeEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:  # type: ignore[override]
        """Close window on return, else pass event through to super class.

        Parameters
        ----------
        event : qtpy.QtCore.QEvent
            Event from the Qt context.
        """
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            # self.closeEvent(event)
            event.ignore()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event: QCloseEvent | None = None) -> None:
        """Hide rather than close."""
        if self.HIDE_WHEN_CLOSE:
            self.hide()
            self.clearFocus()
            if hasattr(self, "evt_hide"):
                self.evt_hide.emit()
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
            if hasattr(self, "evt_hide"):
                self.evt_hide.emit()
            self.clearFocus()
            return False
        else:
            return super().close()


class QtFramelessPopup(QtDialog, CloseMixin):  # type: ignore[misc]
    """Frameless dialog."""

    # attributes used to move windows around
    _title_label: QLabel
    _old_window_pos, _title_layout, _move_handle = None, None, None

    def __init__(
        self,
        parent: ty.Optional[QWidget],
        title: str = "",
        position: QPoint | None = None,
        flags: ty.Any = Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Popup,
        delay: bool = False,
    ):
        super().__init__(parent, title, delay=delay)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setWindowFlags(flags)
        if position is not None:
            self.move(position)

    def toggle_persist(self) -> None:
        """Enable persist."""
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)

    def toggle_popup(self) -> None:
        """Toggle popup to be temporary."""
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Popup
        )

    def _make_title_handle(self, title: str = "") -> QHBoxLayout:
        """Make handle button that helps move the window around."""
        self._title_label = hp.make_eliding_label2(
            self,
            title,
            bold=True,
            alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            elide=Qt.TextElideMode.ElideRight,
            object_name="window_title",
        )

        layout = hp.make_hbox_layout(spacing=0)
        layout.addWidget(self._title_label, stretch=True)
        layout.addStretch(1)
        self._title_layout = layout
        return layout

    def _make_move_handle(self, title: str = "") -> QHBoxLayout:
        """Make handle button that helps move the window around."""
        self._title_label = hp.make_eliding_label2(
            self,
            title,
            bold=True,
            alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            elide=Qt.TextElideMode.ElideRight,
            object_name="window_title",
        )
        self._move_handle = hp.make_qta_label(
            self, "move_handle", tooltip="Click here and drag the mouse around to move the window.", normal=True
        )
        self._move_handle.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = hp.make_hbox_layout(spacing=0)
        layout.addWidget(self._title_label, stretch=True)
        layout.addWidget(self._move_handle)
        self._title_layout = layout
        return layout

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Mouse press event."""
        super().mousePressEvent(event)
        # allow movement of the window when user uses right-click and the move handle button does not exist
        if event.button() == Qt.MouseButton.RightButton:  # and self._move_handle is None:
            self._old_window_pos = event.x(), event.y()
        elif self._move_handle is None:
            self._old_window_pos = None
        elif self.childAt(event.pos()) == self._move_handle:
            self._old_window_pos = event.x(), event.y()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Mouse move event - ensures its possible to move the window to new location."""
        super().mouseMoveEvent(event)
        if self._old_window_pos is not None:
            self.move(event.globalX() - self._old_window_pos[0], event.globalY() - self._old_window_pos[1])

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """Mouse release event."""
        super().mouseReleaseEvent(event)
        self._old_window_pos = None

    def disable_while_open(self, *widgets: QWidget) -> None:
        """Disable widgets while the window is open."""
        self.evt_close.connect(lambda: hp.disable_widgets(*widgets, disabled=False))
        hp.disable_widgets(*widgets, disabled=True)

    def closeEvent(self, event: QCloseEvent | None = None) -> None:
        """Hide rather than close."""
        if self.HIDE_WHEN_CLOSE:
            self.hide()
            self.clearFocus()
            if hasattr(self, "evt_hide"):
                self.evt_hide.emit()
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
            if hasattr(self, "evt_hide"):
                self.evt_hide.emit()
            self.clearFocus()
            return False
        else:
            return super().close()


class QtFramelessTool(QtFramelessPopup):
    """Frameless dialog that stays on top."""

    def __init__(
        self,
        parent: QWidget | None,
        title: str = "",
        position: QPoint | None = None,
        flags: Qt.WindowType = Qt.WindowType.FramelessWindowHint
        | Qt.WindowType.WindowStaysOnTopHint
        | Qt.WindowType.Tool,
        delay: bool = False,
    ):
        super().__init__(parent, title, position, flags, delay=delay)


class QtCollapsibleFramelessTool(QtFramelessTool):
    """Collapsible tool."""

    GEOM_TIME = 250

    expand_btn: QtExpandButton

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.timer = QTimer()
        self.geom_anim = QPropertyAnimation(self, b"geometry", self)

    def mousePressEvent(self, event):
        """Mouse press event."""
        event.ignore()

    def closeEvent(self, event: QCloseEvent | None) -> None:
        """Cannot close popup."""
        if event:
            event.ignore()

    @property
    def is_expanded(self) -> bool:
        """Checks whether text is expanded."""
        return bool(self.property("expanded"))

    def toggle_expansion(self):
        """Toggle the expanded state of the notification frame."""
        self.contract() if self.is_expanded else self.expand()
        self.timer.stop()

    def expand(self) -> None:
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
        self.geom_anim.setEasingCurve(QEasingCurve.Type.OutQuad)
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
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
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

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setWindowFlags(Qt.WindowType.SubWindow)
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

    def move_to(self, location: str) -> None:
        """Move to location."""
        try:
            if location == "top_right":
                self.move_to_top_right()
            elif location == "top_left":
                self.move_to_top_left()
            elif location == "bottom_right":
                self.move_to_bottom_right()
            elif location == "bottom_left":
                self.move_to_bottom_left()
        except RuntimeError:
            pass

    def move_to_top_right(self, offset=(-10, 10)) -> None:
        """Position widget at the top right edge of the parent."""
        if not self.parent():
            return
        psz = self.parent().size()
        sz = psz - QSize(self.size().width(), psz.height()) + QSize(*offset)
        self.move(QPoint(sz.width(), sz.height()))

    def move_to_bottom_right(self, offset=(8, 8)) -> None:
        """Position widget at the bottom right edge of the parent."""
        if not self.parent():
            return
        sz = self.parent().size() - self.size() - QSize(*offset)
        self.move(QPoint(sz.width(), sz.height()))

    def move_to_top_left(self, offset=(8, 8)) -> None:
        """Position widget at the bottom right edge of the parent."""
        if not self.parent():
            return
        self.move(QPoint(*offset))

    def move_to_bottom_left(self, offset=(8, 8)) -> None:
        """Position widget at the bottom right edge of the parent."""
        if not self.parent():
            return
        sz = self.parent().size() - self.size()
        self.move(QPoint(offset[0], sz.height() - offset[1]))

    def slide_in(self) -> None:
        """Run animation that fades in the dialog with a slight slide up."""
        geom = self.geometry()
        self.geom_anim.setDuration(self.FADE_IN_RATE)
        self.geom_anim.setStartValue(geom.translated(0, -20))
        self.geom_anim.setEndValue(geom)
        self.geom_anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        # fade in
        self.opacity_anim.setDuration(self.FADE_IN_RATE)
        self.opacity_anim.setStartValue(0)
        self.opacity_anim.setEndValue(self.MAX_OPACITY)
        self.geom_anim.start()
        self.opacity_anim.start()

    def fade_in(self) -> None:
        """Run animation that fades in the dialog."""
        self.opacity_anim.setDuration(self.FADE_IN_RATE)
        self.opacity_anim.setStartValue(0)
        self.opacity_anim.setEndValue(self.MAX_OPACITY)
        self.opacity_anim.start()

    def fade_out(self) -> None:
        """Run animation that fades out the dialog."""
        self.opacity_anim.setDuration(self.FADE_OUT_RATE)
        self.opacity_anim.setStartValue(self.MAX_OPACITY)
        self.opacity_anim.setEndValue(0)
        self.opacity_anim.start()

    def deleteLater(self) -> None:
        """Stop all animations and timers before deleting."""
        with suppress(RuntimeError, TypeError):
            self.geom_anim.stop()
            super().deleteLater()

    def close(self) -> None:
        """Close window."""
        with suppress(RuntimeError, TypeError):
            self.geom_anim.stop()
            super().close()

    def close_with_fade(self):
        """Fade out then close."""
        with suppress(RuntimeError, TypeError):
            self.opacity_anim.stop()
            self.geom_anim.stop()

            self.opacity_anim.setDuration(self.FADE_OUT_RATE)
            self.opacity_anim.setStartValue(self.MAX_OPACITY)
            self.opacity_anim.setEndValue(0)
            self.opacity_anim.start()
            self.opacity_anim.finished.connect(self.close)
