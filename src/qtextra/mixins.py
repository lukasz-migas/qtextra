"""Various mixin classes that can be integrated into other widgets."""

import time
import typing as ty
from contextlib import contextmanager
from functools import partial
from pathlib import Path

from koyo.timer import report_time
from loguru import logger
from qtpy.QtCore import QTimer, Signal
from qtpy.QtWidgets import QHBoxLayout, QPushButton, QWidget

import qtextra.helpers as hp
from qtextra.config import EVENTS, get_settings
from qtextra.utils.utilities import check_url, get_docs_path

# Documentation directory
DOC_DIR = Path(get_docs_path())


class DocumentationMixin:
    """Documentation mixin."""

    DOC_HTML_LINK: str = ""

    def _make_info_layout(
        self, align_right: bool = True, html_link: str = "", parent: QWidget = None
    ) -> ty.Tuple[QPushButton, QHBoxLayout]:
        """Make info button."""
        if not html_link:
            html_link = self.DOC_HTML_LINK

        info_btn = hp.make_qta_btn(
            parent if parent is not None else self.parent(),
            "help",
            flat=True,
            tooltip="Click here to see more information about this panel...",
        )
        info_btn.clicked.connect(partial(self._open_info_link, html_link))

        layout = QHBoxLayout()
        layout.addWidget(info_btn)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        if align_right:
            layout.insertSpacerItem(0, hp.make_h_spacer())
        else:
            layout.addSpacerItem(hp.make_h_spacer())
        return info_btn, layout

    @staticmethod
    def _open_info_link(html_link: str):
        """Open link."""
        # local docs
        if html_link.startswith("docs/"):
            html_link = (DOC_DIR / html_link).as_uri()

        if html_link.startswith("file:///") or check_url(html_link):
            EVENTS.evt_help_request.emit(html_link)
        else:
            EVENTS.evt_msg_warning.emit("The provided link is not valid")


class ConfigMixin:
    """Configuration mixin."""

    _initialized = False
    _is_setting_config = False

    @contextmanager
    def setting_config(self):
        """Disable updates by temporarily setting the `_is_setting_config` flag."""
        self._is_setting_config = True
        yield
        self._is_setting_config = False

    def on_set_from_config(self) -> None:
        """Init from config."""
        with self.setting_config():
            self._on_set_from_config(get_settings())

    def _on_set_from_config(self, settings: ty.Optional = None):
        """Bind events."""


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
        logger.debug(f"Added periodic timer event that runs every {interval/1000}s")
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
        handle_layout.insertWidget(2, hide_handle)
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
        close_btn = hp.make_qta_btn(self, "cross", tooltip="Click here to close the popup window", normal=True)
        close_btn.clicked.connect(self.close)

        handle_layout = self._make_move_handle()
        handle_layout.insertWidget(3, close_btn)
        self._title_label.setText(title)
        return close_btn, handle_layout

    def _make_hide_handle(self, title: str = ""):
        self.HIDE_WHEN_CLOSE = True
        return self._make_close_handle(title)


class IndicatorMixin:
    """Mixin class to instantiate certain methods."""

    evt_indicate = Signal(str)
    evt_indicate_about = Signal(str, str)

    def on_toast(self, title: str, message: str, func: ty.Callable = logger.info):
        """Show notification."""
        from qtextra.widgets.qt_toast import QtToast

        func(message)
        QtToast(self).show_message(title, message)

    @staticmethod
    def on_notify_critical(msg: str, func: ty.Callable = logger.critical) -> None:
        """Notify the user of an error."""
        EVENTS.evt_msg_critical.emit(msg)
        func(msg)

    @staticmethod
    def on_notify_error(msg: str, func: ty.Callable = logger.error) -> None:
        """Notify the user of an error."""
        EVENTS.evt_msg_error.emit(msg)
        func(msg)

    @staticmethod
    def on_notify_warning(msg: str, func: ty.Callable = logger.warning) -> None:
        """Notify the user of a warning."""
        EVENTS.evt_msg_warning.emit(msg)
        func(msg)

    @staticmethod
    def on_notify_info(msg: str, func: ty.Callable = logger.info) -> None:
        """Notify the user of an info."""
        EVENTS.evt_msg_info.emit(msg)
        func(msg)

    @staticmethod
    def on_notify_success(msg: str, func: ty.Callable = logger.success) -> None:
        """Notify the user of an success."""
        EVENTS.evt_msg_success.emit(msg)
        func(msg)

    def _indicate_success(self, source: ty.Optional[str] = None) -> None:
        if source and isinstance(source, str):
            self.evt_indicate_about.emit("success", source)
        else:
            self.evt_indicate.emit("success")

    def _indicate_success_any(self, *_args: ty.Any, **_kwargs: ty.Any) -> None:
        self._indicate_success()

    def _indicate_failure(self, source: ty.Optional[str] = None) -> None:
        if source:
            self.evt_indicate_about.emit("warning", source)
        else:
            self.evt_indicate.emit("warning")
