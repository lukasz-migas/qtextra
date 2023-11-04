"""Utilities for QtExtra widgets."""
import os
import sys
import typing as ty

from qtpy.QtCore import QEvent, Qt, QTimer, Signal
from qtpy.QtWidgets import QApplication, QMainWindow, QWidget

if ty.TYPE_CHECKING:
    from qtreload.qt_reload import QtReloadWidget


def disable_warnings():
    """Disable warnings."""
    import warnings

    # disable warnings
    warnings.filterwarnings("ignore", category=DeprecationWarning, module="vispy")
    warnings.filterwarnings("ignore", category=DeprecationWarning, module="pydantic")
    warnings.filterwarnings("ignore", category=DeprecationWarning, module="numpy")
    warnings.filterwarnings("ignore", category=FutureWarning, module="shiboken2")
    warnings.filterwarnings("ignore", category=FutureWarning, module="pandas")
    warnings.filterwarnings("ignore", category=FutureWarning, module="xgboost")
    warnings.filterwarnings("ignore", category=ResourceWarning, module="sentry_sdk")


def qdev(parent=None, modules: ty.Iterable[str] = ("qtextra", "koyo")) -> "QtReloadWidget":
    """Create reload widget."""
    from qtreload.qt_reload import QtReloadWidget

    return QtReloadWidget(modules, parent=parent)


def qapplication(test_time: int = 3):
    """Return QApplication instance.

    Creates it if it doesn't already exist.

    Parameters
    ----------
    test_time: int
        Time to maintain open the application when testing. It's given in seconds
    """
    import faulthandler

    disable_warnings()

    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    if hasattr(Qt, "AA_EnableHighDpiScaling"):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, "AA_UseHighDpiPixmaps"):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    if hasattr(Qt, "AA_UseStyleSheetPropagationInWidgetStyles"):
        QApplication.setAttribute(Qt.AA_UseStyleSheetPropagationInWidgetStyles, True)
    if hasattr(Qt, "AA_ShareOpenGLContexts"):
        QApplication.setAttribute(Qt.AA_ShareOpenGLContexts, True)

    faulthandler.enable()

    Application = MacApplication if sys.platform == "darwin" else QApplication
    app = Application.instance()
    if app is None:
        # Set Application name for Gnome 3
        # https://groups.google.com/forum/#!topic/pyside/24qxvwfrRDs
        app = Application(["qtextra"])

        # Set application name for KDE. See spyder-ide/spyder#2207.
        app.setApplicationName("qtextra")

    test_ci = os.environ.get("TEST_CI_WIDGETS", None)
    if test_ci is not None:
        timer_shutdown = QTimer(app)
        timer_shutdown.timeout.connect(app.quit)
        timer_shutdown.start(test_time * 1000)
    return app


def qframe(horz: bool = True, with_layout: bool = True, add_reload: bool = True, set_style: bool = True):
    """Create frame widget."""
    from qtpy import QtWidgets

    app = qapplication()
    frame = QtWidgets.QWidget()
    ha = None
    if with_layout:
        if horz:
            ha = QtWidgets.QHBoxLayout()
        else:
            ha = QtWidgets.QVBoxLayout()
        if add_reload:
            w = qdev()
            ha.addWidget(w)
        frame.setLayout(ha)
    if set_style:
        apply_style(frame)
    return app, frame, ha


def apply_style(widget: QWidget) -> None:
    """Apply stylesheet(s) on the widget."""
    from qtextra.config.theme import THEMES

    THEMES.set_theme_stylesheet(widget)


def qmain(horz: bool = True, set_style: bool = True):
    """Create main widget."""
    from qtpy import QtWidgets

    app = qapplication()
    main = QtWidgets.QMainWindow()
    if horz:
        ha = QtWidgets.QHBoxLayout()
    else:
        ha = QtWidgets.QVBoxLayout()
    main.setCentralWidget(QtWidgets.QWidget())
    main.centralWidget().setLayout(ha)
    if set_style:
        apply_style(main)
    return app, main, ha


def get_parent(parent):
    """Get top level parent."""
    if parent is None:
        app = QApplication.instance()
        if app:
            for i in app.topLevelWidgets():
                if isinstance(i, QMainWindow):  # pragma: no cover
                    parent = i
                    break
    return parent


class MacApplication(QApplication):
    """Subclass to be able to open external files with our Mac app."""

    sig_open_external_file = Signal(str)

    def __init__(self, *args):
        QApplication.__init__(self, *args)
        self._never_shown = True
        self._has_started = False
        self._pending_file_open = []
        self._original_handlers = {}

    def event(self, event):
        if event.type() == QEvent.FileOpen:
            fname = str(event.file())
            if sys.argv and sys.argv[0] == fname:
                # Ignore requests to open own script
                # Later, mainwindow.initialize() will set sys.argv[0] to ''
                pass
            elif self._has_started:
                self.sig_open_external_file.emit(fname)
        return QApplication.event(self, event)
