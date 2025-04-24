"""Feedback dialog."""

import getpass
import os
import typing as ty

from loguru import logger
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QFormLayout, QWidget

import qtextra.helpers as hp
from qtextra.widgets.qt_dialog import QtDialog

SENTRY_DSN: str = os.getenv("QTEXTRA_TELEMETRY_SENTRY_DSN", "")
ORGANIZATION_SLUG: str = os.getenv("QTEXTRA_TELEMETRY_ORGANIZATION", "")
PROJECT_SLUG: str = os.getenv("QTEXTRA_TELEMETRY_PROJECT", "")

FEEDBACK_URL = f"https://sentry.io/api/0/projects/{ORGANIZATION_SLUG}/{PROJECT_SLUG}/user-feedback/"


class FeedbackDialog(QtDialog):
    """Dialog to give the user an option to provide feedback."""

    def __init__(self, parent: ty.Optional[QWidget] = None):
        super().__init__(parent=parent, title="Feedback")
        self.setMinimumSize(600, 400)

    def accept(self):
        """Submit message."""
        self.on_apply()
        title = self.title.text()
        message = self.message.toPlainText()
        if not message:
            hp.warn_pretty(self, "Please write-in a message before continuing.")
            return
        event_id = submit_feedback(title, message)
        hp.toast(
            self.parent(),
            title="Feedback",
            message="Feedback submitted successfully."
            if event_id
            else "Feedback submission failed. Please try again later.",
            icon="success" if event_id else "error",
            position="top_left",
        )
        super().accept()

    # noinspection PyAttributeOutsideInit
    def make_panel(self) -> QFormLayout:
        """Dialog to provide feedback."""
        self.info = hp.make_label(
            self,
            "<b>Send feedback</b><br><br>We always welcome user feedback, whether its good or bad. Please type in"
            " your thoughts and send them onwards.<br>",
            alignment=Qt.AlignmentFlag.AlignHCenter,
        )
        self.name = hp.make_line_edit(self, getpass.getuser(), placeholder="Your name")

        self.email = hp.make_line_edit(self, "", placeholder="Your email address")

        self.title = hp.make_line_edit(self, "User feedback", placeholder="Feedback title")
        self.message = hp.make_text_edit(self, "", placeholder="Your feedback")

        self.submit_btn = hp.make_btn(self, "Submit", func=self.accept)
        self.cancel_btn = hp.make_btn(self, "Cancel", func=self.reject)

        btn_layout = hp.make_h_layout(self.submit_btn, self.cancel_btn)

        layout = hp.make_form_layout()
        layout.addRow(self.info)
        layout.addRow(hp.make_label(self, "Name (required)"), self.name)
        layout.addRow(hp.make_label(self, "Email address (optional)"), self.email)
        layout.addRow(hp.make_label(self, "Title"), self.title)
        layout.addRow(hp.make_label(self, "Message"))
        layout.addRow(self.message)
        layout.addRow(btn_layout)
        return layout


def submit_feedback(title: str, message: str, name: str = "", email: str = ""):
    """Submit feedback."""
    import getpass

    import requests
    import sentry_sdk

    with sentry_sdk.push_scope() as scope:
        scope.set_extra("name", name or getpass.getuser())
        scope.set_extra("email", email or "unknown@unknown.com")
        scope.set_extra("message", message)
    event_id = sentry_sdk.capture_message(message=title, level="debug", scope=scope)
    if event_id:
        data = {
            "comments": message,
            "event_id": event_id,
            "email": email or "unknown@unknown.com",
            "name": name or "",
        }

        res = requests.post(
            url=FEEDBACK_URL,
            data=data,
            headers={"Authorization": f"DSN {SENTRY_DSN}"},
            timeout=5,
        )
        logger.trace(f"Submitted extra feedback. Status code: {res.status_code}.")
    logger.debug(f"Submitted feedback. Return: {event_id}")
    return event_id


if __name__ == "__main__":  # pragma: no cover
    import sys

    from qtextra.dialogs.sentry import install_error_monitor
    from qtextra.utils.dev import apply_style, qapplication

    app = qapplication(1)
    install_error_monitor()
    dlg = FeedbackDialog(None)
    apply_style(dlg)
    dlg.show()
    sys.exit(app.exec_())
