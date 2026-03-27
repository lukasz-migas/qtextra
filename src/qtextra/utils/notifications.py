"""Notifications.

Environment variable
QTEXTRA_NOTIFICATION_EXIT_ON_ERROR: 0 (default) or 1, whether to exit on error instead of showing a notification.
QTEXTRA_NOTIFICATION_CATCH_ERROR: 0 (default) or 1, whether to catch error and show notification instead of calling
    the original except hook.
QTEXTRA_NOTIFICATION_HOOKS_ENABLED: 0 (default) or 1, whether to send error information to telemetry instead of showing
    a notification.
QTEXTRA_NOTIFICATION_AUTO_EXPAND: 0 (default) or 1, whether to auto expand the notification when a new notification
    is received.
QTEXTRA_NOTIFICATION_DISMISS_TIME: 5000 (default) or int, time in milliseconds after which the notification is
    automatically dismissed. 0 to disable.
QTEXTRA_NOTIFICATION_LEVEL: "WARNING" (default) or str, minimum severity level to show in the notification manager.
    One of "NONE", "DEBUG", "INFO", "SUCCESS", "WARNING", "ERROR", "CRITICAL".
"""

from __future__ import annotations

import os
import sys
import threading
import typing as ty
import warnings
from collections.abc import Sequence
from datetime import datetime
from enum import auto
from types import TracebackType

from koyo.typing import StringEnum
from loguru import logger

try:
    from napari.utils.events import Event, EventEmitter
except ImportError:
    raise ImportError("please install napari using 'pip install napari'") from None

name2num = {
    "critical": 50,
    "error": 40,
    "warning": 30,
    "info": 20,
    "success": 20,
    "debug": 10,
    "none": 0,
}


class NotificationSeverity(StringEnum):
    """Severity levels for the notification dialog.  Along with icons for each."""

    NONE = auto()
    DEBUG = auto()
    INFO = auto()
    SUCCESS = auto()
    WARNING = auto()
    ERROR = auto()
    CRITICAL = auto()

    def __lt__(self, other):
        return name2num[str(self)] < name2num[str(other)]

    def __le__(self, other):
        return name2num[str(self)] <= name2num[str(other)]

    def __gt__(self, other):
        return name2num[str(self)] > name2num[str(other)]

    def __ge__(self, other):
        return name2num[str(self)] >= name2num[str(other)]


NOTIFICATION_LEVELS = {
    NotificationSeverity.NONE: "None",
    NotificationSeverity.DEBUG: "Debug",
    NotificationSeverity.INFO: "Info",
    NotificationSeverity.SUCCESS: "Success",
    NotificationSeverity.WARNING: "Warning",
    NotificationSeverity.ERROR: "Error",
    NotificationSeverity.CRITICAL: "Critical",
}

ActionSequence = Sequence[ty.Tuple[str, ty.Callable[[], None]]]


logger_call = {
    NotificationSeverity.NONE: logger.debug,
    NotificationSeverity.DEBUG: logger.debug,
    NotificationSeverity.INFO: logger.info,
    NotificationSeverity.SUCCESS: logger.info,
    NotificationSeverity.WARNING: logger.warning,
    NotificationSeverity.ERROR: logger.error,
    NotificationSeverity.CRITICAL: logger.critical,
}


class Notification(Event):
    """A Notification event.  Usually created by :class:`NotificationManager`.

    Parameters
    ----------
    message : str
        The main message/payload of the notification.
    severity : str or NotificationSeverity, optional
        The severity of the notification, by default
        `NotificationSeverity.WARNING`.
    actions : sequence of tuple, optional
        Where each tuple is a `(str, callable)` 2-tuple where the first item
        is a name for the action (which may, for example, be put on a button),
        and the callable is a callback to perform when the action is triggered.
        (for example, one might show a traceback dialog). by default ()
    """

    def __init__(
        self,
        message: str,
        severity: ty.Union[str, NotificationSeverity] = NotificationSeverity.WARNING,
        actions: ActionSequence = (),
        auto_close: bool = True,
        **kwargs,
    ):
        self.severity = NotificationSeverity(severity)
        super().__init__(type_name=str(self.severity).lower(), **kwargs)
        self.message = message
        self.actions = actions
        self.auto_close = auto_close

        # let's store when the object was created;
        self.date = datetime.now()

    @classmethod
    def from_exception(cls, exc: BaseException, **kwargs) -> Notification:
        """Create notification from error."""
        return ErrorNotification(exc, **kwargs)

    @classmethod
    def from_warning(cls, warning: Warning, **kwargs) -> Notification:
        """Create notification from warning."""
        return WarningNotification(warning, **kwargs)

    def __str__(self):
        return f"{self.date} ({str(self.severity).upper()}): {self.message}"

    def as_plain_str(self) -> str:
        """Render as string."""
        return f"{self.date}: {self.message}"


class ErrorNotification(Notification):
    """Error notification."""

    exception: BaseException
    _traceback = None

    def __init__(self, exception: BaseException, *args, **kwargs):
        msg = getattr(exception, "message", str(exception))
        actions = getattr(exception, "actions", ())
        super().__init__(msg, NotificationSeverity.ERROR, actions)
        # extract exception from the tuple
        if isinstance(exception, tuple):
            for value in exception:
                if isinstance(value, Exception):
                    exception = value
                    break
        self.exception = exception
        if hasattr(exception, "__traceback__"):
            self._traceback = exception.__traceback__

    def __str__(self) -> str:
        from napari.utils._tracebacks import get_tb_formatter

        fmt = get_tb_formatter()
        exc_info = (
            self.exception.__class__,
            self.exception,
            self.exception.__traceback__,
        )
        return fmt(exc_info, as_html=False)

    @property
    def traceback(self):
        """Retrieve traceback."""
        if self._traceback is None:
            self._traceback = self.exception.__traceback__
        return self._traceback

    def as_html(self):
        """Render as html."""
        from napari.utils._tracebacks import get_tb_formatter

        fmt = get_tb_formatter()
        exception = self.exception
        exc_info = (
            exception.__class__,
            exception,
            exception.__traceback__,
        )
        return fmt(exc_info, as_html=True)

    def as_text(self) -> str:
        """Render as text."""
        from napari.utils._tracebacks import get_tb_formatter

        fmt = get_tb_formatter()
        exc_info = (
            self.exception.__class__,
            self.exception,
            self.exception.__traceback__,
        )
        return fmt(exc_info, as_html=False, color="NoColor")

    def as_plain_str(self) -> str:
        """Render as string."""
        import traceback

        return "".join(traceback.format_stack())


class WarningNotification(Notification):
    """Warning notification."""

    warning: Warning

    def __init__(self, warning: Warning, filename=None, lineno=None, *args, **kwargs):
        msg = getattr(warning, "message", str(warning))
        actions = getattr(warning, "actions", ())
        super().__init__(msg, NotificationSeverity.WARNING, actions)
        self.warning = warning
        self.filename = filename
        self.lineno = lineno

    def __str__(self):
        category = type(self.warning).__name__
        return f"{self.filename}:{self.lineno}: {category}: {self.warning}!"


class NotificationManager:
    """
    A notification manager, to route all notifications through.

    Only one instance is in general available through napari; as we need
    notification to all flow to a single location that is registered with the
    sys.except_hook  and showwarning hook.

    This can and should be used a context manager; the context manager will
    properly re-entered, and install/remove hooks and keep them in a stack to
    restore them.

    While it might seem unnecessary to make it re-entrant; or to make the
    re-entrancy no-op; one need to consider that this could be used inside
    another context manager that modify except_hook and showwarning.

    Currently the original except and show warnings hooks are not called; but
    this could be changed in the future; this poses some questions with the
    re-entrency of the hooks themselves.
    """

    records: ty.List[Notification]
    _instance: ty.Optional[NotificationManager] = None

    def __init__(self) -> None:
        self.records: ty.List[Notification] = []
        self.exit_on_error = os.getenv("QTEXTRA_NOTIFICATION_EXIT_ON_ERROR") in ("1", "True")
        self.catch_error = os.getenv("QTEXTRA_NOTIFICATION_CATCH_ERROR") in ("1", "True")
        self.notification_ready = self.changed = EventEmitter(source=self, event_class=Notification)
        self.records_cleared = EventEmitter(source=self, event_class=Event)
        self._originals_except_hooks = []
        self._original_showwarnings_hooks = []
        self._originals_thread_except_hooks = []
        self._seen_warnings: set[tuple[str, type, str, int]] = set()

    def __enter__(self):
        self.install_hooks()
        return self

    def __exit__(self, *args, **kwargs):
        self.restore_hooks()

    def clear(self):
        """Remove past notifications from the records list."""
        self.records.clear()
        self.records_cleared(Event("clear"))

    def install_hooks(self):
        """
        Install a `sys.excepthook`, a `showwarning` hook and a
        threading.excepthook to display any message in the UI,
        storing the previous hooks to be restored if necessary.
        """
        enabled = os.getenv("QTEXTRA_NOTIFICATION_HOOKS_ENABLED") in ("1", "True")

        if enabled:
            self._originals_thread_except_hooks.append(threading.excepthook)
            threading.excepthook = self.receive_thread_error

            self._originals_except_hooks.append(sys.excepthook)
            sys.excepthook = self.receive_error

            self._original_showwarnings_hooks.append(warnings.showwarning)
            warnings.showwarning = self.receive_warning

    def restore_hooks(self) -> None:
        """Remove hooks installed by `install_hooks` and restore previous hooks."""
        if getattr(threading, "excepthook", None) and self._originals_thread_except_hooks:
            threading.excepthook = self._originals_thread_except_hooks.pop()

        if self._originals_except_hooks:
            sys.excepthook = self._originals_except_hooks.pop()
        if self._original_showwarnings_hooks:
            warnings.showwarning = self._original_showwarnings_hooks.pop()

    def dispatch(self, notification: Notification) -> None:
        """Dispatch notification."""
        self.records.append(notification)
        self.notification_ready(notification)

    def receive_thread_error(
        self,
        args: tuple[
            type[BaseException],
            BaseException,
            TracebackType | None,
            threading.Thread | None,
        ],
    ) -> None:
        """Receive thread error."""
        self.receive_error(*args)

    def receive_error(
        self,
        exctype: type[BaseException],
        value: BaseException,
        traceback: TracebackType | None = None,
        thread: threading.Thread | None = None,
    ) -> None:
        """Receive error."""
        if isinstance(value, KeyboardInterrupt):
            sys.exit("Closed by KeyboardInterrupt")

        if self.exit_on_error:
            sys.__excepthook__(exctype, value, traceback)
            sys.exit("Exit on error")
        if not self.catch_error:
            sys.__excepthook__(exctype, value, traceback)
            return
        self.dispatch(Notification.from_exception(value))

    def receive_warning(
        self,
        message: Warning,
        category: type[Warning],
        filename: str,
        lineno: int,
        file=None,
        line=None,
    ):
        """Receive warning."""
        msg = message if isinstance(message, str) else message.args[0]
        if (msg, category, filename, lineno) in self._seen_warnings:
            return
        self._seen_warnings.add((msg, category, filename, lineno))
        self.dispatch(
            Notification.from_warning(
                message,
                filename=filename,
                lineno=lineno,
            ),
        )

    def receive_info(self, message: str) -> None:
        """Receive info."""
        self.dispatch(Notification(message, severity="INFO"))


NOTIFICATION_MANAGER: NotificationManager = NotificationManager()


def show_debug(message: str) -> None:
    """Show a debug message in the notification manager."""
    NOTIFICATION_MANAGER.dispatch(
        Notification(message, severity=NotificationSeverity.DEBUG),
    )


def show_info(message: str) -> None:
    """Show an info message in the notification manager."""
    NOTIFICATION_MANAGER.dispatch(
        Notification(message, severity=NotificationSeverity.INFO),
    )


def show_warning(message: str) -> None:
    """Show a warning in the notification manager."""
    NOTIFICATION_MANAGER.dispatch(
        Notification(message, severity=NotificationSeverity.WARNING),
    )


def show_error(message: str) -> None:
    """Show an error in the notification manager."""
    NOTIFICATION_MANAGER.dispatch(
        Notification(message, severity=NotificationSeverity.ERROR),
    )


def _setup_thread_excepthook():
    """Workaround for `sys.excepthook` thread bug from: http://bugs.python.org/issue1230540."""
    _init = threading.Thread.__init__

    def init(self, *args, **kwargs):
        _init(self, *args, **kwargs)
        _run = self.run

        def run_with_except_hook(*args2, **kwargs2):
            try:
                _run(*args2, **kwargs2)
            except Exception:  # noqa: BLE001
                sys.excepthook(*sys.exc_info())

        self.run = run_with_except_hook

    threading.Thread.__init__ = init
