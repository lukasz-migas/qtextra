"""Feedback dialog."""

from __future__ import annotations

import getpass
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from loguru import logger
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QFormLayout, QLabel, QWidget

import qtextra.helpers as hp
from qtextra.widgets.qt_dialog import QtDialog

SENTRY_DSN: str = os.getenv("QTEXTRA_TELEMETRY_SENTRY_DSN", "")
ORGANIZATION_SLUG: str = os.getenv("QTEXTRA_TELEMETRY_ORGANIZATION", "")
PROJECT_SLUG: str = os.getenv("QTEXTRA_TELEMETRY_PROJECT", "")

FEEDBACK_URL = f"https://sentry.io/api/0/projects/{ORGANIZATION_SLUG}/{PROJECT_SLUG}/user-feedback/"


class FeedbackDialog(QtDialog):
    """Dialog to give the user an option to provide feedback."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent=parent, title="Share Feedback")
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
            "<b>Send feedback</b><br><br>"
            "Use this form for product feedback, missing features, and rough edges. "
            "For crash reporting, use the telemetry prompt instead.",
            alignment=Qt.AlignmentFlag.AlignHCenter,
        )
        self.name = hp.make_line_edit(self, getpass.getuser(), placeholder="Your name")
        self.name.setToolTip("Used as the display name on the feedback item in Sentry.")

        self.email = hp.make_line_edit(self, "", placeholder="Your email address")
        self.email.setToolTip("Optional. Add this if you want the maintainer to contact you.")

        self.title = hp.make_line_edit(self, "User feedback", placeholder="Short summary")
        self.title.setToolTip("A short title that summarizes the feedback.")
        self.message = hp.make_text_edit(self, "", placeholder="Your feedback")
        self.message.setToolTip("Include what happened, what you expected, and any useful repro steps.")

        self.submit_btn = hp.make_btn(self, "Submit", func=self.accept)
        self.cancel_btn = hp.make_btn(self, "Cancel", func=self.reject)

        btn_layout = hp.make_h_layout(self.submit_btn, self.cancel_btn)

        layout = hp.make_form_layout()
        layout.addRow(self.info)
        if not is_feedback_configured():
            notice = QLabel(
                "<small>Feedback is not configured because the Sentry DSN, organization slug, "
                "or project slug is missing.</small>",
            )
            notice.setWordWrap(True)
            notice.setStyleSheet("color: #999;")
            layout.addRow(notice)
        layout.addRow(hp.make_label(self, "Name (required)"), self.name)
        layout.addRow(hp.make_label(self, "Email address (optional)"), self.email)
        layout.addRow(hp.make_label(self, "Title"), self.title)
        layout.addRow(hp.make_label(self, "Message"))
        layout.addRow(self.message)
        layout.addRow(btn_layout)
        return layout


def get_feedback_url() -> str:
    """Return the Sentry user-feedback endpoint."""
    return FEEDBACK_URL


def is_feedback_configured() -> bool:
    """Return whether user feedback can be submitted."""
    return bool(SENTRY_DSN and ORGANIZATION_SLUG and PROJECT_SLUG)


def _post_feedback(data: dict[str, str]) -> bool:
    """Post feedback to Sentry."""
    url = get_feedback_url()
    request = Request(  # noqa: S310
        url=url,
        data=urlencode(data).encode("utf-8"),
        headers={"Authorization": f"DSN {SENTRY_DSN}"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=5) as response:  # noqa: S310
            status = getattr(response, "status", response.getcode())
            logger.trace(f"Submitted extra feedback. Status code: {status}.")
            return 200 <= status < 300
    except HTTPError as exc:
        logger.warning(f"Feedback submission failed with HTTP {exc.code}.")
    except URLError as exc:
        logger.warning(f"Feedback submission failed: {exc}.")
    return False


def submit_feedback(title: str, message: str, name: str = "", email: str = ""):
    """Submit feedback."""
    import sentry_sdk

    if not is_feedback_configured():
        logger.warning("Feedback submission skipped because Sentry feedback is not configured.")
        return None

    username = name or getpass.getuser()
    sender_email = email or "unknown@unknown.com"

    with sentry_sdk.new_scope() as scope:
        scope.set_extra("feedback.name", username)
        scope.set_extra("feedback.email", sender_email)
        scope.set_extra("feedback.message", message)
        event_id = sentry_sdk.capture_message(message=title, level="info", scope=scope)

    if not event_id:
        logger.debug("Feedback submission failed because no event id was returned.")
        return None

    submitted = _post_feedback(
        {
            "comments": message,
            "event_id": event_id,
            "email": sender_email,
            "name": username,
        },
    )
    logger.debug(f"Submitted feedback. Return: {event_id if submitted else None}")
    return event_id if submitted else None


if __name__ == "__main__":  # pragma: no cover
    import sys

    from qtextra.dialogs.sentry import install_error_monitor
    from qtextra.utils.dev import apply_style, qapplication

    class _Settings:
        telemetry_enabled = True
        telemetry_with_locals = True

    app = qapplication(1)
    install_error_monitor(_Settings())
    dlg = FeedbackDialog(None)
    apply_style(dlg)
    dlg.show()
    sys.exit(app.exec_())
