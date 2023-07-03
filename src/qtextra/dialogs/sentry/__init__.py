"""Sentry monitoring service."""
"""Init."""
import typing as ty

import sentry_sdk

from qtextra.dialogs.sentry.utilities import SENTRY_SETTINGS, _get_tags, get_sample_event
from qtextra.dialogs.sentry.telemetry import TelemetryOptInDialog
from qtextra.dialogs.sentry.feedback import FeedbackDialog

INSTALLED = False


__all__ = [
    "ask_opt_in",
    "capture_exception",
    "get_sample_event",
    "install_error_monitor",
    "TelemetryOptInDialog",
]

capture_exception = sentry_sdk.capture_exception


def ask_opt_in(settings, force=False, parent=None):
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
    assert hasattr(settings, "telemetry_enabled"), "Settings must have telemetry_enabled attribute."
    assert hasattr(settings, "telemetry_with_locals"), "Settings must have telemetry_with_locals attribute."

    if not force and settings.telemetry_enabled:
        return settings

    dlg = TelemetryOptInDialog(parent=parent, with_locals=settings.telemetry_with_locals)
    send: ty.Optional[bool] = None
    if bool(dlg.exec()):
        send = True  # pragma: no cover
    elif dlg._no:
        send = False  # pragma: no cover

    if send is not None:
        settings.telemetry_enabled = send
        settings.telemetry_with_locals = dlg._send_locals
    return settings


def install_error_monitor(settings):
    """Initialize the error monitor with sentry.io."""
    global INSTALLED
    if INSTALLED:
        return

    settings = ask_opt_in(settings)
    if not settings.telemetry_enabled:
        return

    _settings = SENTRY_SETTINGS.copy()
    _settings["with_locals"] = settings.telemetry_with_locals
    sentry_sdk.init(**_settings)
    for k, v in _get_tags().items():
        sentry_sdk.set_tag(k, v)
    INSTALLED = True
