"""Notifications."""
from __future__ import annotations

import sys
import threading
import warnings
from datetime import datetime
from enum import auto
from types import TracebackType
from typing import Callable, List, Optional, Sequence, Tuple, Type, Union

from loguru import logger
from napari.utils.misc import StringEnum

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

ActionSequence = Sequence[Tuple[str, Callable[[], None]]]


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
        severity: Union[str, NotificationSeverity] = NotificationSeverity.WARNING,
        actions: ActionSequence = (),
        auto_close: bool = True,
        **kwargs,
    ):
        self.severity = NotificationSeverity(severity)
        super().__init__(type=str(self.severity).lower(), **kwargs)
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
        return f"{self.date}: {self.message}"

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

    def as_plain_str(self) -> str:
        """Render as string."""
        import traceback

        return "".join(traceback.format_stack())

    def __str__(self):
        """Render as string."""
        from napari.utils._tracebacks import get_tb_formatter

        fmt = get_tb_formatter()
        exception = self.exception
        exc_info = (
            exception.__class__,
            exception,
            exception.__traceback__,
        )
        return fmt(exc_info, as_html=False)


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

    records: List[Notification]
    _instance: Optional[NotificationManager] = None

    def __init__(self) -> None:
        self.records: List[Notification] = []
        self.exit_on_error = False
        self.notification_ready = self.changed = EventEmitter(source=self, event_class=Notification)
        self.records_cleared = EventEmitter(source=self, event_class=Event)
        self._originals_except_hooks = []
        self._original_showwarnings_hooks = []
        self._originals_thread_except_hooks = []

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
        from ionglow.config import get_settings

        # if getattr(threading, "excepthook", None):
        #     # TODO: we might want to display the additional thread information
        #     self._originals_thread_except_hooks.append(threading.excepthook)
        #     threading.excepthook = self.receive_thread_error
        # else:
        #     # Patch for Python < 3.8
        #     _setup_thread_excepthook()

        if not get_settings().telemetry.enabled:
            self._originals_except_hooks.append(sys.excepthook)
            self._original_showwarnings_hooks.append(warnings.showwarning)
            sys.excepthook = self.receive_error

    # warnings.showwarning = self.receive_warning

    def restore_hooks(self):
        """Remove hooks installed by `install_hooks` and restore previous hooks."""
        if getattr(threading, "excepthook", None):
            # `threading.excepthook` available only for Python >= 3.8
            if self._originals_thread_except_hooks:
                threading.excepthook = self._originals_thread_except_hooks.pop()

        if self._originals_except_hooks:
            sys.excepthook = self._originals_except_hooks.pop()
        if self._original_showwarnings_hooks:
            warnings.showwarning = self._original_showwarnings_hooks.pop()

    def dispatch(self, notification: Notification):
        """Dispatch notification."""
        self.records.append(notification)
        self.notification_ready(notification)

    #         if isinstance(notification, ErrorNotification):
    #             logger_call[notification.severity](notification.as_plain_str())

    def receive_thread_error(self, args: threading.ExceptHookArgs):
        """Receive error from thread."""
        self.receive_error(*args)

    def receive_error(
        self,
        exctype: Optional[Type[BaseException]] = None,
        value: Optional[BaseException] = None,
        traceback: Optional[TracebackType] = None,
        thread: Optional[threading.Thread] = None,
    ):
        """Receive error."""
        if isinstance(value, KeyboardInterrupt):
            sys.exit("Closed by KeyboardInterrupt")
        if self.exit_on_error:
            sys.__excepthook__(exctype, value, traceback)
            sys.exit("Exit on error")

        try:
            notif = Notification.from_exception(value)
            self.dispatch(notif)
        except Exception:
            logger.error("Encountered a problem while parsing an error.")

    def receive_warning(
        self,
        message: Warning,
        category: Type[Warning],
        filename: str,
        lineno: int,
        file=None,
        line=None,
    ):
        """Receive warning."""
        self.dispatch(Notification.from_warning(message, filename=filename, lineno=lineno))

    def receive_info(self, message: str):
        """Receive information message."""
        self.dispatch(Notification(message, NotificationSeverity.INFO))


NOTIFICATION_MANAGER: NotificationManager = NotificationManager()


def show_info(message: str):
    """Show message."""
    NOTIFICATION_MANAGER.receive_info(message)


def _setup_thread_excepthook():
    """Workaround for `sys.excepthook` thread bug from: http://bugs.python.org/issue1230540."""
    _init = threading.Thread.__init__

    def init(self, *args, **kwargs):
        _init(self, *args, **kwargs)
        _run = self.run

        def run_with_except_hook(*args2, **kwargs2):
            try:
                _run(*args2, **kwargs2)
            except Exception:
                sys.excepthook(*sys.exc_info())

        self.run = run_with_except_hook

    threading.Thread.__init__ = init
