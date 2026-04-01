"""Sentry dialog examples."""

from qtpy.QtWidgets import QApplication

from qtextra.dialogs.sentry.telemetry import TelemetryOptInDialog
from qtextra.utils.dev import apply_style

app = QApplication([])

widget = TelemetryOptInDialog(with_locals=True)
widget.setMinimumSize(900, 620)
apply_style(widget)
widget.show()

app.exec_()
