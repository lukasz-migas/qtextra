"""Simple dialog to select between two options."""

import typing as ty
from functools import partial

from qtpy.QtWidgets import QDialog, QHBoxLayout, QVBoxLayout, QWidget

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
            btn = hp.make_btn(
                self, label, object_name="pick_option_button", func=partial(self.on_accept, option=option)
            )
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
        """Set rejected."""
        self.option = None
        super().reject()


class QtScrollablePickOption(QDialog):
    """Select between options."""

    option: ty.Optional[str] = None

    def __init__(self, parent: QWidget, text: str, options: ty.Dict[str, str]):
        super().__init__(parent)
        self.setWindowTitle("Select option")
        min_height = min(400, 40 * len(options) + 70)

        self.setMinimumSize(500, min_height)

        self.options = options
        self.responses = {}

        scroll_area, scroll_widget = hp.make_scroll_area(self)
        scroll_layout = QVBoxLayout(scroll_area)
        scroll_layout.addStretch(1)
        for option, label in options.items():
            btn = hp.make_btn(
                self, label, object_name="pick_option_button", func=partial(self.on_accept, option=option)
            )
            scroll_layout.addWidget(btn)
            self.responses[btn.text()] = option
        scroll_layout.addStretch(1)

        layout = QVBoxLayout(self)
        layout.addWidget(hp.make_label(self, text, enable_url=True))
        layout.addWidget(scroll_widget)

    def on_accept(self, option: str):
        """Set accepted."""
        self.option = option
        self.accept()

    def reject(self):
        """Set rejected."""
        self.option = None
        super().reject()
