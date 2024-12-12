"""Confirm action by typing requested text."""

import typing as ty

from qtpy.QtCore import Qt
from qtpy.QtWidgets import QDialog, QWidget

import qtextra.helpers as hp


class ConfirmWithTextDialog(QDialog):
    """Confirm action by typing requested text."""

    def __init__(
        self,
        parent: ty.Optional[QWidget] = None,
        title: str = "Please confirm...",
        message: str = "Please type 'confirm' to continue.",
        request: str = "confirm",
    ):
        super().__init__(parent)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)  # type: ignore
        self.setObjectName("confirm_dialog")
        self.setMinimumSize(350, 200)
        self.setWindowTitle(title)
        self.request = request

        layout = hp.make_v_layout()
        layout.addWidget(hp.make_label(self, message, enable_url=True, wrap=True), stretch=True)
        self.request_edit = hp.make_line_edit(self, "", placeholder=request, func_changed=self.validate)
        layout.addWidget(self.request_edit, stretch=True)

        self.ok_btn = hp.make_btn(self, "Yes", func=self.accept)
        layout.addLayout(
            hp.make_h_layout(
                self.ok_btn,
                hp.make_btn(self, "No", func=self.reject),
            )
        )
        self.setLayout(layout)
        self.validate()
        self.request_edit.setFocus()

    def validate(self) -> None:
        """Validate the input."""
        self.ok_btn.setEnabled(self.request_edit.text() == self.request)
