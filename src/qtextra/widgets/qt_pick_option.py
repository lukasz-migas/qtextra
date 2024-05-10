"""Simple dialog to select between two options."""

from __future__ import annotations

import typing as ty
from functools import partial

from qtpy.QtWidgets import QDialog, QHBoxLayout, QVBoxLayout, QWidget

import qtextra.helpers as hp


class QtPickOptionBase(QDialog):
    """Select between options."""

    option: ty.Optional[str] = None

    def __init__(self, parent: QWidget, text: str, options: ty.Dict[str, str]):
        super().__init__(parent)
        self.setWindowTitle("Select option")

        self.text = text
        self.options = options
        self.responses = {}
        self._setup_ui()

    def _get_layout_widget(self) -> tuple[QWidget | None, QWidget | None]:
        """Get layout widget."""
        raise NotImplementedError("Must implement method")

    def _setup_ui(self) -> None:
        area, widget = self._get_layout_widget()
        btn_layout = QHBoxLayout(area)
        btn_layout.addStretch(1)
        for option, label in self.options.items():
            btn = hp.make_btn(
                self, label, object_name="pick_option_button", func=partial(self.on_accept, option=option)
            )
            btn_layout.addWidget(btn)
            self.responses[btn.text()] = option
        btn_layout.addStretch(1)

        layout = QVBoxLayout(self)
        layout.addWidget(hp.make_label(self, self.text, enable_url=True, wrap=True, object_name="pick_option_label"))
        layout.addStretch(1)
        if widget:
            layout.addWidget(widget)
        else:
            layout.addLayout(btn_layout)

    def on_accept(self, option: str):
        """Set accepted."""
        self.option = option
        self.accept()

    def reject(self):
        """Set rejected."""
        self.option = None
        super().reject()


class QtPickOption(QtPickOptionBase):
    """Select between options."""

    def _get_layout_widget(self) -> tuple[QWidget | None, QWidget | None]:
        """Get layout widget."""
        return None, None


class QtScrollablePickOption(QtPickOptionBase):
    """Select between options."""

    def __init__(self, parent: QWidget, text: str, options: ty.Dict[ty.Any, str]):
        super().__init__(parent, text, options)
        size = self.sizeHint()
        size.setWidth(max(size.width(), 500))
        size.setHeight(min(400, 40 * len(options) + 70))
        self.setMinimumSize(size)

    def _get_layout_widget(self) -> tuple[QWidget | None, QWidget | None]:
        """Get layout widget."""
        scroll_area, scroll_widget = hp.make_scroll_area(self)
        return scroll_area, scroll_widget
