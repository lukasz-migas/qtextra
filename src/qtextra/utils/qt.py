"""Qt utilities."""

from __future__ import annotations

import os
import re
import sys

import qtpy
from qtpy.QtWidgets import QApplication

RICH_TEXT_PATTERN = re.compile("<[^\n]+>")


def _ipython_has_eventloop() -> bool:
    """Return True if IPython %gui qt is active.

    Using this is better than checking ``QApp.thread().loopLevel() > 0``,
    because IPython starts and stops the event loop continuously to accept code
    at the prompt.  So it will likely "appear" like there is no event loop
    running, but we still don't need to start one.
    """
    ipy_module = sys.modules.get("IPython")
    if not ipy_module:
        return False

    shell = ipy_module.get_ipython()
    if not shell:
        return False

    return shell.active_eventloop == "qt"


def _pycharm_has_eventloop(app: QApplication) -> bool:
    """Return true if running in PyCharm and eventloop is active.

    Explicit checking is necessary because PyCharm runs a custom interactive
    shell which overrides `InteractiveShell.enable_gui()`, breaking some
    superclass behaviour.
    """
    in_pycharm = "PYCHARM_HOSTED" in os.environ
    in_event_loop = getattr(app, "_in_event_loop", False)
    return in_pycharm and in_event_loop


def qt_might_be_rich_text(text) -> bool:
    """Check if a text might be rich text in a cross-binding compatible way."""
    if qtpy.PYSIDE2:
        from qtpy.QtGui import Qt as _Qt
    else:
        from qtpy.QtCore import Qt as _Qt

    try:
        return _Qt.mightBeRichText(text)
    except Exception:  # noqa: BLE001
        return bool(RICH_TEXT_PATTERN.search(text))
