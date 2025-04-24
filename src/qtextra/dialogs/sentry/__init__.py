"""Sentry monitoring service."""

from __future__ import annotations

import typing as ty
from contextlib import suppress
from pathlib import Path

import sentry_sdk
from qtpy.QtWidgets import QWidget

from qtextra.dialogs.sentry.feedback import FeedbackDialog
from qtextra.dialogs.sentry.telemetry import TelemetryOptInDialog
from qtextra.dialogs.sentry.utilities import SENTRY_SETTINGS, _get_tags, get_sample_event

INSTALLED = False


__all__ = [
    "FeedbackDialog",
    "TelemetryOptInDialog",
    "ask_opt_in",
    "capture_exception",
    "get_sample_event",
    "install_error_monitor",
]

capture_exception = sentry_sdk.capture_exception


class Settings(ty.Protocol):
    """Settings protocol."""

    telemetry_enabled: bool
    telemetry_with_locals: bool


def ask_opt_in(settings: Settings, force: bool = False, parent: QWidget | None = None) -> Settings:
    """Show the dialog asking the user to opt in.

    Parameters
    ----------
    settings
        Settings object.
    force : bool, optional
        If True, will show opt_in even if user has already opted in/out,
        by default False.
    parent : QWidget, optional
        Parent widget, by default None.

    Returns
    -------
    SettingsDict
        [description].
    """
    assert settings is not None, "Settings must be provided."

    enabled_attr = "enabled" if hasattr(settings, "enabled") else "telemetry_enabled"
    with_locals_attr = "with_locals" if hasattr(settings, "with_locals") else "telemetry_with_locals"

    assert hasattr(settings, enabled_attr), f"Settings must have '{enabled_attr}' attribute."
    assert hasattr(settings, with_locals_attr), f"Settings must have '{with_locals_attr}' attribute."

    if not force and getattr(settings, enabled_attr) is not None:
        return settings

    dlg = TelemetryOptInDialog(parent=parent, with_locals=getattr(settings, with_locals_attr))
    send: ty.Optional[bool] = None
    if bool(dlg.exec()):
        send = True  # pragma: no cover
    elif dlg._no:
        send = False  # pragma: no cover

    if send is not None:
        setattr(settings, enabled_attr, send)
        setattr(settings, with_locals_attr, dlg._send_locals)
    return settings


def install_error_monitor(settings: Settings, **extra_kws: ty.Any) -> None:
    """Initialize the error monitor with sentry.io."""
    global INSTALLED
    if INSTALLED:
        return

    enabled_attr = "enabled" if hasattr(settings, "enabled") else "telemetry_enabled"
    with_locals_attr = "with_locals" if hasattr(settings, "with_locals") else "telemetry_with_locals"

    settings = ask_opt_in(settings)
    if not getattr(settings, enabled_attr):
        return

    _settings = SENTRY_SETTINGS.copy()
    _settings["include_local_variables"] = getattr(settings, with_locals_attr)
    sentry_sdk.init(**_settings)
    for k, v in _get_tags().items():
        sentry_sdk.set_tag(k, v)
    if extra_kws:
        set_extra_tags(**extra_kws)
    INSTALLED = True


def set_extra_tags(**kwargs: ty.Any) -> None:
    """Set extra tags."""
    for k, v in kwargs.items():
        sentry_sdk.set_tag(k, v)


def report_memory_usage() -> str:
    """Report memory usage for current process."""
    import tempfile

    import psutil
    from koyo.faulthandler import submit_sentry_attachment
    from koyo.utilities import human_readable_byte_size

    tmp = Path(tempfile.gettempdir())
    path = tmp / "memory_usage.txt"
    memory_text = f"Total memory: {human_readable_byte_size(psutil.virtual_memory().total)}\n"
    memory_text += f"Available memory: {human_readable_byte_size(psutil.virtual_memory().available)}\n"
    with suppress(Exception):
        process = psutil.Process()
        pid = process.pid
        mem = process.memory_info()

        memory_text += f"RMS ({pid}): {human_readable_byte_size(mem.rss)}\n"
        memory_text += f"VMS ({pid}): {human_readable_byte_size(mem.rss)}\n"
    path.write_text(memory_text)
    submit_sentry_attachment("Current memory usage - encountered memory issues", path)
    with suppress(Exception):
        path.unlink()
    return memory_text
