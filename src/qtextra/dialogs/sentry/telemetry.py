from pprint import pformat

from qtpy.QtCore import Qt
from qtpy.QtWidgets import (
    QCheckBox,
    QDialogButtonBox,
    QLabel,
    QTextEdit,
    QVBoxLayout,
)

from qtextra.dialogs.sentry.utilities import PACKAGE, get_sample_event
from qtextra.helpers import get_parent
from qtextra.widgets.qt_dialog import QtDialog


class TelemetryOptInDialog(QtDialog):
    """Opt-in widget."""

    def __init__(self, parent=None, with_locals=False) -> None:
        parent = get_parent(parent)
        super().__init__(parent=parent, title=f"{PACKAGE} Error Reporting")
        self._mock_initialized = False
        self._no = False
        self._send_locals = False

        self.send_locals.setChecked(with_locals)
        self._update_example()
        self.resize(760, 900)

    # noinspection PyAttributeOutsideInit
    def make_panel(self) -> QVBoxLayout:
        """Create the telemetry/error-reporting opt-in dialog panel and return its layout."""
        btn_box = QDialogButtonBox()
        btn_box.addButton("Enable error reporting", QDialogButtonBox.ButtonRole.AcceptRole)
        no = btn_box.addButton("Not now", QDialogButtonBox.ButtonRole.RejectRole)
        no.clicked.connect(self._set_no)

        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)

        info = QLabel(
            f"""
            <h3>Help improve {PACKAGE}</h3>
            <p>
            If {PACKAGE} crashes or raises an unexpected exception, you can let it send an error
            report to <a href="https://sentry.io/">Sentry</a>. The report helps maintainers fix
            bugs faster without asking you to manually collect logs.
            </p>
            <p>
            The preview below shows the kind of structured event payload that would be sent. You can
            decide whether local variables from stack frames should be included.
            </p>
            """,
        )
        info.setWordWrap(True)
        info.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        info.setOpenExternalLinks(True)

        summary = QLabel(
            """
            <b>Included by default</b>:
            <ul style="margin-top: 2px; margin-bottom: 6px; padding-left: 18px;">
                <li>traceback</li>
                <li>package version</li>
                <li>Qt backend</li>
                <li>platform metadata</li>
            </ul>
            <b>Optional</b>:
            <ul style="margin-top: 2px; margin-bottom: 6px; padding-left: 18px;">
                <li>local variables from stack frames</li>
            </ul>
            <b>Not shown in this preview</b>:
            <ul style="margin-top: 2px; margin-bottom: 0; padding-left: 18px;">
                <li>any custom tags your application adds during startup</li>
            </ul>
            """,
        )
        summary.setWordWrap(True)

        preview_title = QLabel("<b>Example payload</b>")
        preview_title.setToolTip("This is a sample event generated locally so you can inspect the payload shape.")

        self.txt = QTextEdit()
        self.txt.setReadOnly(True)
        self.txt.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.txt.setToolTip("A sample Sentry event showing the metadata and traceback that would be sent.")
        self.txt.setObjectName("sentry_payload_preview")

        self.send_locals = QCheckBox("Include local variables")
        self.send_locals.stateChanged.connect(self._update_example)
        self.send_locals.setToolTip(
            "When enabled, local variables from the failing stack frame are attached to the event. "
            "This is often the most useful debugging context, but it can include sensitive values.",
        )

        locals_hint = QLabel(
            "<small>Recommended for development builds. Disable it if your application handles "
            "sensitive file paths, tokens, or document contents.</small>",
        )
        locals_hint.setWordWrap(True)
        locals_hint.setStyleSheet("color: #999;")

        footer = QLabel(
            "<small>You can change this choice later from your application's settings or Help menu.</small>"
        )
        footer.setStyleSheet("color: #999;")
        footer.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        main_layout = QVBoxLayout()
        main_layout.addWidget(info)
        main_layout.addWidget(summary)
        main_layout.addWidget(preview_title)
        main_layout.addWidget(self.txt)
        main_layout.addWidget(self.send_locals)
        main_layout.addWidget(locals_hint)
        main_layout.addWidget(btn_box)
        main_layout.addWidget(footer)
        return main_layout

    def _set_no(self):
        self._no = True

    def _update_example(self) -> None:
        """Update example event."""
        self._send_locals = self.send_locals.isChecked()
        event = get_sample_event(include_local_variables=self._send_locals)

        try:
            import yaml

            estring = yaml.safe_dump(event, indent=4, width=120)
        except ImportError:
            estring = pformat(event, indent=2, width=120)
        except yaml.YAMLError:
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
