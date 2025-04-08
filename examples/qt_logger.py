"""QtPopout example."""

from loguru import logger
from qtpy.QtWidgets import QApplication, QVBoxLayout, QWidget

from qtextra.config import THEMES
from qtextra.dialogs.qt_logger import QtLogger

app = QApplication([])

widget = QWidget()
widget.setMinimumSize(600, 300)
THEMES.apply(widget)

layout = QVBoxLayout()
widget.setLayout(layout)
layout.addWidget(QtLogger(widget))

logger.trace("TRACE")
logger.debug("DEBUG")
logger.info("INFO")
logger.warning("WARNING")
logger.error("ERROR")
logger.critical("CRITICAL")
widget.show()

app.exec_()
