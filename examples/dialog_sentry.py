"""Sentry dialog examples."""

from qtpy.QtWidgets import QApplication

from qtextra.config import THEMES
from qtextra.dialogs.sentry.telemetry import TelemetryOptInDialog

app = QApplication([])

widget = TelemetryOptInDialog(with_locals=True)
widget.setMinimumSize(900, 620)
THEMES.apply(widget)
widget.show()

app.exec_()
