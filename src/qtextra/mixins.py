"""Various mixin classes that can be integrated into other widgets."""

from __future__ import annotations

import typing as ty
from contextlib import contextmanager
from functools import partial
from pathlib import Path

from koyo.timer import MeasureTimer
from loguru import logger
from qtpy.QtCore import QTimer, Signal  # type: ignore[attr-defined]
from qtpy.QtGui import QCloseEvent
from qtpy.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget

import qtextra.helpers as hp
from qtextra.config import EVENTS, get_settings
from qtextra.utils.utilities import check_url, get_docs_path

# Documentation directory
DOC_DIR = Path(get_docs_path())


class DocumentationMixin:
    """Documentation mixin."""

    DOC_HTML_LINK: str = ""

    parent: ty.Callable[..., QWidget]

    ENABLE_TUTORIAL: bool = False
    _docs_tutorial_btn: QPushButton | None = None

    ENABLE_HTML: bool = True
    _docs_info_btn: QPushButton | None = None

    def _make_info_layout(
        self, align_right: bool = True, html_link: str = "", parent: QWidget | None = None
    ) -> ty.Tuple[QPushButton, QHBoxLayout]:
        """Make info button."""
        if not html_link:
            html_link = self.DOC_HTML_LINK

        self._docs_tutorial_btn = hp.make_qta_btn(
            parent if parent is not None else self.parent(),
            "tutorial",
            tooltip="Click here to launch tutorial for this panel...",
            func=self._open_tutorial,
            hide=not self.ENABLE_TUTORIAL,
        )
        self._docs_info_btn = info_btn = hp.make_qta_btn(
            parent if parent is not None else self.parent(),
            "help",
            tooltip="Click here to see more information about this panel...",
            func=partial(self._open_info_link, html_link),
            hide=not self.ENABLE_HTML,
        )

        layout = QHBoxLayout()
        layout.addWidget(self._docs_tutorial_btn)
        layout.addWidget(self._docs_info_btn)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        if align_right:
            layout.insertSpacerItem(0, hp.make_h_spacer())
        else:
            layout.addSpacerItem(hp.make_h_spacer())
        return info_btn, layout

    def _open_tutorial(self) -> None:
        """Launch tutorial for this panel."""

    @staticmethod
    def _open_info_link(html_link: str) -> None:
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

    _initialized_config: bool = False
    _is_setting_config: bool = False

    @contextmanager
    def setting_config(self) -> ty.Generator[None, None, None]:
        """Disable updates by temporarily setting the `_is_setting_config` flag."""
        self._is_setting_config = True
        yield
        self._is_setting_config = False

    def on_set_from_config(self) -> None:
        """Init from config."""
        with self.setting_config():
            self._on_set_from_config(get_settings())  # type: ignore[no-untyped-call]
        self._initialized_config = True

    def _on_set_from_config(self, settings: ty.Any | None = None) -> None:
        """Bind events."""


class TimerMixin:
    """Timer mixin."""

    def _add_periodic_timer(self, interval: int, fcn: ty.Callable | None, start: bool = True) -> QTimer:
        """Create timer to execute some action."""
        timer = QTimer(self)  # type: ignore[arg-type]
        timer.setInterval(interval)
        if fcn:
            timer.timeout.connect(fcn)

        if start:
            timer.start()
        logger.debug(f"Added periodic timer event that runs every {interval / 1000}s")
        return timer

    def _add_single_shot_timer(self, delay: int, fcn: ty.Callable) -> QTimer:
        timer = QTimer(self)  # type: ignore[arg-type]
        timer.singleShot(delay, fcn)
        return timer

    @contextmanager  # type: ignore[arg-type]
    def measure_time(
        self, message: str = "Task took", func: ty.Callable = logger.trace
    ) -> ty.Generator[None, None, None]:
        """Measure time."""
        with MeasureTimer() as timer:
            yield
        func(f"{message} {timer()}")


class MinimizeMixin:
    """Mixin class to enable hiding of popup."""

    _make_move_handle: ty.Callable[..., ty.Any]
    hide: ty.Callable[..., ty.Any]
    clearFocus: ty.Callable[..., ty.Any]

    def _make_hide_handle(self) -> tuple[QPushButton, QHBoxLayout]:
        hide_btn = hp.make_qta_btn(
            self,  # type: ignore[arg-type]
            "minimise",
            tooltip="Click here to minimize the popup window",
        )
        hide_btn.clicked.connect(self.on_hide)

        hide_layout = self._make_move_handle()
        hide_layout.addWidget(hide_btn)
        return hide_btn, hide_layout

    def on_hide(self) -> None:
        """Hide."""
        self.hide()
        self.clearFocus()

    def closeEvent(self, event: QCloseEvent) -> None:
        """Hide."""
        self.on_hide()
        event.ignore()


# noinspection PyUnresolvedReferences
class CloseMixin:
    """Mixin class to enable closing of popup."""

    HIDE_WHEN_CLOSE: bool = False
    _title_label: QLabel

    close: ty.Callable[..., ty.Any]
    _make_move_handle: ty.Callable[..., ty.Any]
    _close_handle = None

    def _make_close_layout(self, title: str = "") -> QHBoxLayout:
        """Make close layout."""
        return self._make_close_handle(title=title)[1]

    def _make_close_handle(self, title: str = "") -> tuple[QPushButton, QHBoxLayout]:
        self._close_handle = hp.make_qta_btn(
            self,
            "cross",
            tooltip="Click here to close the popup window",
            normal=True,
            func=self.close,
        )

        close_layout = self._make_move_handle()
        close_layout.addWidget(self._close_handle)
        self._title_label.setText(title)
        return self._close_handle, close_layout

    def _make_hide_layout(self, title: str = "") -> QHBoxLayout:
        """Make hide layout."""
        return self._make_hide_handle(title=title)[1]

    def _make_hide_handle(self, title: str = "") -> tuple[QPushButton, QHBoxLayout]:
        self.HIDE_WHEN_CLOSE = True
        return self._make_close_handle(title)


class IndicatorMixin:
    """Mixin class to instantiate certain methods."""

    evt_indicate = Signal(str)
    evt_indicate_about = Signal(str, str)

    def on_toast(self, title: str, message: str, func: ty.Callable = logger.info) -> None:
        """Show notification."""
        from qtextra.widgets.qt_toast import QtToast

        func(message)
        QtToast(self).show_message(title, message)  # type: ignore[arg-type]

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
