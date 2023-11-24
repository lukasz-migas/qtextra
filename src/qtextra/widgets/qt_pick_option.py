"""Simple dialog to select between two options."""
import typing as ty
from functools import partial

from qtpy.QtWidgets import QDialog, QHBoxLayout, QPushButton, QVBoxLayout, QWidget

import qtextra.helpers as hp


class QtPickOption(QDialog):
    """Select between options."""

    option: ty.Optional[str] = None

    def __init__(self, parent: QWidget, text: str, options: ty.Dict[str, str]):
        super().__init__(parent)
        self.setWindowTitle("Select option")

        self.options = options

        self.responses = {}
        btn_layout = QHBoxLayout()
        btn_layout.addStretch(1)
        for option, label in options.items():
            btn = hp.make_btn(self, label, object_name="pick_option_button",
                              func=partial(self.on_accept, option=option))
            btn_layout.addWidget(btn)
            self.responses[btn.text()] = option
        btn_layout.addStretch(1)

        layout = QVBoxLayout(self)
        layout.addWidget(hp.make_label(self, text, enable_url=True))
        layout.addStretch(1)
        layout.addLayout(btn_layout)

    def on_accept(self, option: str):
        """Set accepted."""
        self.option = option
        self.accept()

    def reject(self):
        self.option = None
        super().reject()
