"""Utilities for QtExtra widgets."""
import os
import sys
import typing as ty

from qtpy.QtCore import QEvent, Qt, QTimer, Signal
from qtpy.QtWidgets import QApplication

IS_WIN = sys.platform == "win32"
IS_LINUX = sys.platform == "linux"
IS_MAC = sys.platform == "darwin"


def get_module_path(module: str, filename: str) -> str:
    """Get module path."""
    import importlib.resources

    if not filename.endswith(".py"):
        filename += ".py"

    with importlib.resources.path(module, filename) as f:
        path = str(f)
    return path


def qdev(parent=None, modules: ty.List[str] = ("qtextra",)):
    """Create reload widget."""
    from qtreload.qt_reload import QtReloadWidget

    return QtReloadWidget(modules, parent=parent)


def qapplication(test_time: int = 3):
    """
    Return QApplication instance
    Creates it if it doesn't already exist.

    test_time: Time to maintain open the application when testing. It's given
    in seconds
    """
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    QApplication.setAttribute(Qt.AA_UseStyleSheetPropagationInWidgetStyles, True)
    QApplication.setAttribute(Qt.AA_ShareOpenGLContexts, True)

    Application = MacApplication if IS_MAC else QApplication
    app = Application.instance()
    if app is None:
        # Set Application name for Gnome 3
        # https://groups.google.com/forum/#!topic/pyside/24qxvwfrRDs
        app = Application([""])

        # Set application name for KDE. See spyder-ide/spyder#2207.
        app.setApplicationName("")

    test_ci = os.environ.get("TEST_CI_WIDGETS", None)
    if test_ci is not None:
        timer_shutdown = QTimer(app)
        timer_shutdown.timeout.connect(app.quit)
        timer_shutdown.start(test_time * 1000)

    return app


def qframe(horz: bool = True, with_layout: bool = True, add_reload: bool = True):
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
    return app, frame, ha


def qmain(horz: bool = True):
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

    return app, main, ha


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
