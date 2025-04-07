"""Qt Logging module.

Copied and modified from this post: http://plumberjack.blogspot.com/2019/11/a-qt-gui-for-logging.html
"""

from __future__ import annotations

import typing as ty
from contextlib import suppress

from koyo.logging import LOG_FMT
from koyo.typing import PathLike
from loguru import logger
from qtpy.QtCore import QObject, Qt, Signal, Slot
from qtpy.QtGui import QFont
from qtpy.QtWidgets import QHBoxLayout, QPlainTextEdit, QVBoxLayout, QWidget

from qtextra.utils.utilities import connect
from qtextra.widgets.qt_dialog import QtFramelessTool
from qtextra.widgets.qt_toolbar_mini import QtMiniToolbar


class QtHandler(QObject):
    """Qt Log Handler."""

    evt_signal = Signal(object)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def write(self, message: str):
        """Emit message."""
        with suppress(RuntimeError):
            self.evt_signal.emit(message)


class QtLogger(QWidget):
    """Logger window."""

    THEME_COLORS: ty.ClassVar[dict] = {
        "light": {
            "BACKGROUND": "white",
            "TEXT": "black",
            "TRACE": "darkblue",
            "DEBUG": "green",
            "INFO": "black",
            "WARNING": "orange",
            "ERROR": "red",
            "CRITICAL": "darkred",
        },
        "dark": {
            "BACKGROUND": "black",
            "TEXT": "white",
            "TRACE": "lightblue",
            "DEBUG": "green",
            "INFO": "white",
            "WARNING": "orange",
            "ERROR": "red",
            "CRITICAL": "darkred",
        },
    }
    THEMES: ty.ClassVar[list] = list(THEME_COLORS.keys())
    LOG_LEVELS: ty.ClassVar[dict] = {
        "[TRACE ": "TRACE",
        "[DEBUG ": "DEBUG",
        "[INFO ": "INFO",
        "[WARNING ": "WARNING",
        "[ERROR ": "ERROR",
        "[CRITICAL ": "CRITICAL",
    }
    THEME: str
    COLORS: ty.Dict[str, str]
    TEXT_COLOR: str

    def __init__(self, parent: QWidget | None = None, log_dir: PathLike | None = None):
        super().__init__(parent)
        self.log_dir = log_dir

        # Set whatever the default monospace font is for the platform
        self.textedit = QPlainTextEdit(self)
        font = QFont("monospace")
        self.textedit.setFont(font)
        self.textedit.setReadOnly(True)

        toolbar = QtMiniToolbar(self, Qt.Orientation.Vertical)
        toolbar.insert_qta_tool(
            "folder", tooltip="Open directory with logs", func=self.on_open_log_dir, hidden=self.log_dir is None
        )
        toolbar.insert_qta_tool("paint_palette", tooltip="Change theme", func=self.swap_theme)

        # Lay out all the widgets
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.textedit, stretch=1)
        layout.addWidget(toolbar)
        layout.setSpacing(0)

        # setup theme
        self.set_theme("dark")

        # setup logging
        self.handler = QtHandler(parent=self)
        connect(self.handler.evt_signal, self.update_log, state=True)
        self.log_id = logger.add(
            self.handler, level=0, backtrace=True, diagnose=True, catch=True, enqueue=True, format=LOG_FMT
        )

    def closeEvent(self, evt):
        """Close."""
        with suppress(Exception):
            logger.remove(self.log_id)
        connect(self.handler.evt_signal, self.update_log, state=False)
        return super().closeEvent(evt)

    @Slot(str)
    @Slot(object)
    def update_log(self, message):
        """Update log record."""
        record = message.record
        level = record["level"].name if hasattr(record["level"], "name") else record["level"]
        color = self.COLORS.get(level, self.TEXT_COLOR)
        self.append_log_entry(color, message)

    def append_log_entry(self, color: str | list, message: str) -> None:
        """Add log entry to the window."""
        self.textedit.appendHtml(f'<pre><font color="{color}">{message}</font></pre>')
        # self.textedit.appendHtml(f'<span><font color="{color}">{message}</font></span>')

    def on_open_log_dir(self):
        """Open directory containing log files."""
        from koyo.path import open_directory_alt

        if self.log_dir is None:
            logger.warning("Log directory is not set.")
            return
        open_directory_alt(self.log_dir)

    def swap_theme(self):
        """Swap theme."""
        current_theme = self.THEME
        new_theme = "light" if current_theme == "dark" else "dark"
        self.set_theme(new_theme)

    def set_theme(self, theme):
        """Update color theme of the logger."""
        if theme not in self.THEMES:
            raise ValueError(f"Theme must be one of `{self.THEMES}`")

        self.COLORS = self.THEME_COLORS[theme]
        self.TEXT_COLOR = self.THEME_COLORS[theme]["TEXT"]
        self.THEME = theme

        # update background color
        self.textedit.setStyleSheet("QPlainTextEdit {{background-color: {}}}".format(self.COLORS["BACKGROUND"]))
        self.recolor_old_text()

    def recolor_old_text(self):
        """Iteratively go through each line of the previous log and change the color to match the current theme."""

        def _get_log_level():
            for _level in self.LOG_LEVELS.keys():
                if _level in status:
                    return self.LOG_LEVELS[_level]

        old_log = self.textedit.toPlainText()
        old_log = old_log.split("\n")
        self.textedit.clear()

        for status in old_log:
            level = _get_log_level()
            color = self.COLORS.get(level, self.TEXT_COLOR)
            self.append_log_entry(color, status)


class QtLoggerDialog(QtFramelessTool):
    """Logger popup."""

    HIDE_WHEN_CLOSE = True

    def __init__(self, parent: ty.Optional[QWidget] = None, log_dir: PathLike | None = None) -> None:
        self.log_dir = log_dir
        super().__init__(parent)
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)  # type: ignore

    # noinspection PyAttributeOutsideInit
    def make_panel(self) -> QVBoxLayout:
        """Make panel."""
        _, header_layout = self._make_hide_handle()
        self._title_label.setText("Logger")

        self.logger = QtLogger(self, log_dir=self.log_dir)

        layout = QVBoxLayout()
        layout.addLayout(header_layout)
        layout.addWidget(self.logger, stretch=True)
        layout.setSpacing(2)
        layout.setContentsMargins(6, 6, 6, 6)
        return layout


if __name__ == "__main__":  # pragma: no cover
    import sys

    from qtextra.utils.dev import apply_style, qapplication

    app = qapplication(1)
    dlg = QtLoggerDialog()
    apply_style(dlg)
    dlg.show()

    logger.trace("TRACE")
    logger.debug("DEBUG")
    logger.info("INFO")
    logger.warning("WARNING")
    logger.error("ERROR")
    logger.critical("CRITICAL")

    sys.exit(app.exec_())
