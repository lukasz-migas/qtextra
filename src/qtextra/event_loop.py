"""Event loop."""

import os
import sys
from typing import Optional
from warnings import warn

from qtpy.QtCore import Qt
from qtpy.QtGui import QIcon
from qtpy.QtWidgets import QApplication

from qtextra import __version__

APP_ID: str = os.getenv("QTEXTRA_APP_ID", f"qtextra.qtextra.{__version__}")
APP_NAME: str = os.getenv("QTEXTRA_APP_NAME", "qtextra")
APP_ORG_NAME: str = os.getenv("QTEXTRA_APP_ORG_NAME", "qtextra")
APP_ORG_DOMAIN: str = os.getenv("QTEXTRA_APP_ORG_DOMAIN", "")


# store reference to QApplication to prevent garbage collection
_app_ref = None


def set_app_id(app_id):
    """Set app ID."""
    if os.name == "nt" and app_id and not getattr(sys, "frozen", False):
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)


_defaults = {
    "app_name": APP_NAME,
    "app_version": __version__,
    # "icon": ICON_PNG,
    "org_name": APP_ORG_NAME,
    "org_domain": APP_ORG_DOMAIN,
    "app_id": APP_ID,
}


def get_app(
    *,
    app_name: Optional[str] = None,
    app_version: Optional[str] = None,
    icon: Optional[str] = None,
    org_name: Optional[str] = None,
    org_domain: Optional[str] = None,
    app_id: Optional[str] = None,
) -> QApplication:
    """Get or create the Qt QApplication.

    There is only one global QApplication instance, which can be retrieved by
    calling get_app again, (or by using QApplication.instance())

    Parameters
    ----------
    app_name : str, optional
        Set app name (if creating for the first time), by default 'qtextra'
    app_version : str, optional
        Set app version (if creating for the first time), by default __version__
    icon : str, optional
        Set app icon (if creating for the first time), by default
        ICON_PNG
    org_name : str, optional
        Set organization name (if creating for the first time), by default
        'qtextra'
    org_domain : str, optional
        Set organization domain (if creating for the first time), by default
        'qtextra.org'
    app_id : str, optional
        Set organization domain (if creating for the first time).  Will be
        passed to set_app_id (which may also be called independently), by
        default APP_ID

    Returns
    -------
    QApplication
        [description]

    Notes
    -----
    Substitutes QApplicationWithTracing when the QTEXTRA_PERFMON env variable
    is set.

    If the QApplication already exists, we call convert_app_for_tracing() which
    deletes the QApplication and creates a new one. However here with get_app
    we need to create the correct QApplication up front, or we will crash
    because we'd be deleting the QApplication after we created QWidgets with
    it, such as we do for the splash screen.
    """
    # qtextra defaults are all-or nothing.  If any of the keywords are used
    # then they are all used.
    set_values = {k for k, v in locals().items() if v}
    kwargs = locals() if set_values else _defaults
    global _app_ref

    # Note: this MUST be set before the QApplication is instantiated

    app = QApplication.instance()
    if app:
        set_values.discard("ipy_interactive")
        if set_values:
            warn(
                f"QApplication already existed, these arguments to to 'get_app' were ignored: {set_values}",
                stacklevel=2,
            )
    else:
        # automatically determine monitor DPI.
        # Note: this MUST be set before the QApplication is instantiated
        os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
        if hasattr(Qt, "AA_EnableHighDpiScaling"):
            QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        if hasattr(Qt, "AA_UseHighDpiPixmaps"):
            QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
        if hasattr(Qt, "AA_UseStyleSheetPropagationInWidgetStyles"):
            QApplication.setAttribute(Qt.AA_UseStyleSheetPropagationInWidgetStyles, True)
        if hasattr(Qt, "AA_ShareOpenGLContexts"):
            QApplication.setAttribute(Qt.AA_ShareOpenGLContexts, True)
        app = QApplication(sys.argv)

    # if this is the first time the Qt app is being instantiated, we set
    # the name and metadata
    app.setApplicationName(kwargs.get("app_name"))
    app.setApplicationVersion(kwargs.get("app_version"))
    app.setOrganizationName(kwargs.get("org_name"))
    app.setOrganizationDomain(kwargs.get("org_domain"))
    app.setWindowIcon(QIcon(kwargs.get("icon")))
    set_app_id(kwargs.get("app_id"))

    # if perf_config and not perf_config.patched:
    #     # Will patch based on config file.
    #     perf_config.patch_callables()

    # if not _ipython_has_eventloop():
    #     NOTIFICATION_MANAGER.notification_ready.connect(QtNotification.show_notification)
    # NOTIFICATION_MANAGER.notification_ready.connect(show_console_notification)

    if app.windowIcon().isNull():
        app.setWindowIcon(QIcon(kwargs.get("icon")))

    if not _app_ref:  # running get_app for the first time
        # When a new theme is added, at it to the search path.
        from qtpy.QtCore import QDir

        from qtextra.config import THEMES

        # see docstring of `wait_for_workers_to_quit` for caveats on killing
        # workers at shutdown.
        # app.aboutToQuit.connect(wait_for_workers_to_quit)
        # Setup search paths for currently installed themes.
        for name in THEMES.themes:
            QDir.addSearchPath(f"theme_{name}", str(THEMES.get_theme_path(name)))

    _app_ref = app  # prevent garbage collection
    return app


def _ipython_has_eventloop() -> bool:
    """Return True if IPython %gui qt is active.

    Using this is better than checking ``QApp.thread().loopLevel() > 0``,
    because IPython starts and stops the event loop continuously to accept code
    at the prompt.  So it will likely "appear" like there is no event loop
    running, but we still don't need to start one.
    """
    try:
        from IPython import get_ipython

        return get_ipython().active_eventloop == "qt"
    except (ImportError, AttributeError):
        return False


def run(*, force=False, max_loop_level=1, _func_name="run"):
    """Start the Qt Event Loop.

    Parameters
    ----------
    force : bool, optional
        Force the application event_loop to start, even if there are no top
        level widgets to show.
    max_loop_level : int, optional
        The maximum allowable "loop level" for the execution thread.  Every
        time `QApplication.exec_()` is called, Qt enters the event loop,
        increments app.thread().loopLevel(), and waits until exit() is called.
        This function will prevent calling `exec_()` if the application already
        has at least ``max_loop_level`` event loops running.  By default, 1.
    _func_name : str, optional
        name of calling function, by default 'run'.  This is only here to
        provide functions like `gui_qt` a way to inject their name into the
        warning message.

    Raises
    ------
    RuntimeError
        (To avoid confusion) if no widgets would be shown upon starting the
        event loop.
    """
    # from ionglow.utils.notifications import NOTIFICATION_MANAGER

    from qtextra.dialogs.sentry import install_error_monitor

    if _ipython_has_eventloop():
        # If %gui qt is active, we don't need to block again.
        return

    app = QApplication.instance()
    if not app:
        raise RuntimeError(
            "No Qt app has been created. One can be created by calling `get_app()` or qtpy.QtWidgets.QApplication([])"
        )
    if not app.topLevelWidgets() and not force:
        warn(
            "Refusing to run a QApplication with no topLevelWidgets. "
            f"To run the app anyway, use `{_func_name}(force=True)`",
            stacklevel=2,
        )
        return

    if app.thread().loopLevel() >= max_loop_level:
        loops = app.thread().loopLevel()
        s = "s" if loops > 1 else ""
        warn(
            f"A QApplication is already running with {loops} event loop{s}."
            "To enter *another* event loop, use "
            f"`{_func_name}(max_loop_level={loops + 1})`",
            stacklevel=2,
        )
        return
    install_error_monitor()
    app.exec_()
