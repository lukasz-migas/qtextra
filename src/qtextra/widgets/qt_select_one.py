"""Simple dialog to select between two options."""

from __future__ import annotations

import typing as ty

from qtpy.QtCore import Qt
from qtpy.QtWidgets import QDialog, QHBoxLayout, QVBoxLayout, QWidget

import qtextra.helpers as hp

Orientation = ty.Literal["horizontal", "vertical"]


class QtPickOptionBase(QDialog):
    """Select between options."""

    option: ty.Optional[str] = None
    orientation: str | Orientation = "horizontal"

    def __init__(self, parent: QWidget, text: str, options: ty.Dict[str, ty.Any]):
        super().__init__(parent)
        self.setWindowTitle("Select option")

        self.text = text
        self.options = options
        self.responses: dict[str, ty.Any] = {}
        self._setup_ui()

    def _get_layout_widget(self) -> tuple[QWidget | None, QWidget | None]:
        """Get layout widget."""
        raise NotImplementedError("Must implement method")

    def _setup_ui(self) -> None:
        from functools import partial

        area, widget = self._get_layout_widget()
        btn_layout = QHBoxLayout(area) if self.orientation == "horizontal" else QVBoxLayout(area)
        # btn_layout.addStretch(1)
        for label, option in self.options.items():
            btn = hp.make_btn(
                self, label, object_name="pick_option_button", func=partial(self.on_accept, option=option), wrap=True
            )
            btn_layout.addWidget(btn)
            self.responses[btn.text()] = option
        # btn_layout.addStretch(1)

        layout = QVBoxLayout(self)
        layout.addWidget(
            hp.make_label(
                self,
                self.text,
                enable_url=True,
                wrap=True,
                object_name="pick_option_label",
                alignment=Qt.AlignmentFlag.AlignCenter,
            )
        )
        if widget:
            layout.addWidget(widget, stretch=True)
        else:
            layout.addLayout(btn_layout, stretch=True)

    def on_accept(self, option: str) -> None:
        """Set accepted."""
        self.option = option
        return self.accept()

    def reject(self) -> None:
        """Set rejected."""
        self.option = None
        return super().reject()


class QtPickOption(QtPickOptionBase):
    """Select between options."""

    def _get_layout_widget(self) -> tuple[QWidget | None, QWidget | None]:
        """Get layout widget."""
        return None, None


class QtScrollablePickOption(QtPickOptionBase):
    """Select between options."""

    def __init__(
        self,
        parent: QWidget,
        text: str,
        options: dict[str, ty.Any],
        orientation: str | Orientation = "horizontal",
        max_width: int = 500,
    ):
        self.orientation = orientation
        super().__init__(parent, text, options)
        size = self.sizeHint()
        size.setWidth(max(size.width() + 50, max_width))
        size.setHeight(min(400, 40 * len(options) + 70))
        self.setMinimumSize(size)

    def _get_layout_widget(self) -> tuple[QWidget | None, QWidget | None]:
        """Get layout widget."""
        scroll_area, scroll_widget = hp.make_scroll_area(self)
        return scroll_area, scroll_widget


if __name__ == "__main__":  # pragma: no cover
    import sys

    from qtextra.utils.dev import apply_style, qapplication

    app = qapplication(False)
    frame = QtScrollablePickOption(
        None,
        "Select an option",
        {
            "Option 1": "option1",
            "Option 2": "option2",
            "Option 3": "option3",
            "Option 4": "option4",
            "Option 5 (dict)": {"test": "1", "name": "option5"},
            "Option 6": "option6",
            "Option 7": "option7",
            **{f"Option {i}": f"option{i}" for i in range(8, 20)},
        },
        orientation="vertical",
    )
    apply_style(frame)

    if frame.exec_():
        print(frame.option)
    sys.exit()
