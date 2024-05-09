from pprint import pformat

from qtpy.QtCore import Qt
from qtpy.QtWidgets import (
    QCheckBox,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from qtextra.dialogs.sentry.utilities import PACKAGE, get_sample_event
from qtextra.helpers import get_parent
from qtextra.widgets.qt_dialog import QtDialog


class TelemetryOptInDialog(QtDialog):
    """Opt-in widget."""

    def __init__(self, parent=None, with_locals=False) -> None:
        parent = get_parent(parent)
        super().__init__(parent=parent)
        self._mock_initialized = False
        self._no = False
        self._send_locals = False

        self.send_locals.setChecked(with_locals)
        self._update_example()
        self.resize(720, 740)

    # noinspection PyAttributeOutsideInit
    def make_panel(self) -> QVBoxLayout:
        """Dialog to provide feedback."""
        btn_box = QDialogButtonBox()
        btn_box.addButton(f"Yes, send my bug reports to {PACKAGE}", QDialogButtonBox.AcceptRole)
        no = btn_box.addButton("No, I'd prefer not to send bug reports", QDialogButtonBox.RejectRole)
        no.clicked.connect(self._set_no)

        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)

        info = QLabel(
            f"""<h3>{PACKAGE} error reporting</h3>
            <br><br>
            Would you like to help us improve '{PACKAGE}' by automatically sending
            bug reports when an error is detected in '{PACKAGE}'?
            <br><br>
            Reports are collected via <a href="https://sentry.io/">Sentry.io</a>
            <br><br>
            Here is an example error log that would be sent from your system:
            """
        )
        info.setWordWrap(True)
        info.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        info.setOpenExternalLinks(True)

        self.txt = QTextEdit()
        self.txt.setReadOnly(True)

        self.send_locals = QCheckBox("Include local variables")
        self.send_locals.stateChanged.connect(self._update_example)
        self.send_locals.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        _lbl = QLabel(
            "<small><b>greatly</b> improves interpretability of errors, but may "
            "leak personal identifiable information like file paths</small>"
        )
        _lbl.setWordWrap(True)
        _lbl.setStyleSheet("color: #999;")

        _lbl2 = QLabel("<small>You may change your settings at any time in the Help menu.</small>")
        _lbl2.setStyleSheet("color: #999;")
        _lbl2.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        w = QWidget()
        layout = QHBoxLayout()
        layout.addWidget(self.send_locals)
        layout.addWidget(_lbl)
        layout.setContentsMargins(0, 0, 0, 0)
        w.setLayout(layout)

        main_layout = QVBoxLayout()
        main_layout.addWidget(info)
        main_layout.addWidget(self.txt)
        main_layout.addWidget(w)
        main_layout.addWidget(btn_box)
        main_layout.addWidget(_lbl2)
        return main_layout

    def _set_no(self):
        self._no = True

    def _update_example(self):
        self._send_locals = self.send_locals.isChecked()
        event = get_sample_event(include_local_variables=self._send_locals)

        try:
            import yaml

            estring = yaml.safe_dump(event, indent=4, width=120)
        except Exception:
            estring = pformat(event, indent=2, width=120)
        self.txt.setText(estring)


if __name__ == "__main__":  # pragma: no cover
    import sys

    from qtextra.utils.dev import apply_style, qapplication

    app = qapplication(1)
    dlg = TelemetryOptInDialog(None)
    dlg.setMinimumSize(1200, 500)
    apply_style(dlg)

    dlg.show()
    sys.exit(app.exec_())
