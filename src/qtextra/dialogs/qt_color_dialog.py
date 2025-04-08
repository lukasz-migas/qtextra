"""Simple color scheme builder."""

from __future__ import annotations

import typing as ty
from copy import deepcopy

from koyo.color import colormap_to_hex
from pydantic.color import Color
from qtpy.QtCore import Slot
from qtpy.QtWidgets import QDialogButtonBox, QHBoxLayout, QLayout, QWidget

import qtextra.helpers as hp
from qtextra.widgets.qt_dialog import QtDialog


def parse_colors(colors: ty.Union[ty.List[str], ty.List[Color]]) -> ty.List[str]:
    """Parse colors."""
    _colors = []
    for color in colors:
        if isinstance(color, Color):
            _colors.append(color.as_hex())
        else:
            _colors.append(color)
    return _colors


class QtColorListDialog(QtDialog):
    """Config import."""

    def __init__(
        self,
        parent: QWidget | None,
        colors: ty.Union[ty.List[str], ty.List[Color]],
        message: str = "Please click on any of the colors and select a new one",
    ):
        self.colors: ty.List[str] = parse_colors(colors)
        self.new_colors: ty.List[str] = deepcopy(self.colors)
        self.message = message
        super().__init__(parent)

    @property
    def n_colors(self) -> int:
        """Return the number of colors."""
        return len(self.colors)

    # noinspection PyAttributeOutsideInit
    def make_panel(self) -> QLayout:
        """Make panel."""
        self.info_label = hp.make_label(self, self.message)

        color_layout, self.swatches = hp.make_swatch_grid(self, self.colors, self.on_update_color, use_flow_layout=True)

        colormap = hp.make_label(self, "Colormap")
        self.colormap = hp.make_combobox(
            self,
            ["custom", "viridis", "inferno", "magma", "plasma", "cividis", "twilight"],
        )
        self.colormap.currentTextChanged.connect(self.on_set_colormap)
        self.randomize_btn = hp.make_qta_btn(self, "shuffle", tooltip="Randomize colors", medium=False)

        self.randomize_btn.clicked.connect(self.on_randomize)
        self.invert = hp.make_checkbox(self, "Invert", tooltip="Reverse colors")
        self.invert.stateChanged.connect(self.on_set_colormap)
        hp.disable_widgets(self.invert, disabled=self.colormap.currentText() == "custom")

        layout = QHBoxLayout()
        layout.addWidget(self.colormap, stretch=1)
        layout.addWidget(self.randomize_btn)
        layout.addWidget(self.invert)

        # buttons
        self.button_box = QDialogButtonBox(self)
        self.button_box.setStandardButtons(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.setCenterButtons(True)

        # bind events
        self.button_box.button(QDialogButtonBox.StandardButton.Ok).clicked.connect(self.accept)
        self.button_box.button(QDialogButtonBox.StandardButton.Cancel).clicked.connect(self.reject)

        # set layout
        vertical_layout = hp.make_form_layout()
        vertical_layout.addRow(self.info_label)
        vertical_layout.addRow(colormap, layout)
        vertical_layout.addRow(color_layout)
        vertical_layout.addRow(self.button_box)

        return vertical_layout

    def on_randomize(self) -> None:
        """Randomize colors."""
        from koyo.color import get_random_hex_color

        self.colors = [get_random_hex_color() for _ in range(self.n_colors)]
        if self.colormap.currentText() == "custom":
            self.on_set_colormap()
        else:
            self.colormap.setCurrentText("custom")

    @Slot()  # type: ignore[misc]
    def on_set_colormap(self) -> None:
        """Set colors based on colormap."""
        import matplotlib.cm

        colormap = self.colormap.currentText()
        hp.disable_widgets(self.invert, disabled=colormap == "custom")
        if colormap == "custom":
            colors = self.colors
        else:
            colormap += "_r" if self.invert.isChecked() else ""
            cmap = matplotlib.colormaps.get_cmap(colormap)
            colors = colormap_to_hex(cmap.resampled(self.n_colors))
        for color_idx, (swatch, color) in enumerate(zip(self.swatches, colors)):
            swatch.set_color(color)
            self.new_colors[color_idx] = color

    def on_update_color(self, color_idx: int, color: str) -> None:
        """Update color."""
        self.new_colors[color_idx] = color

    def accept(self) -> None:
        """Accept changes."""
        self.colors = self.new_colors
        super().accept()


if __name__ == "__main__":  # pragma: no cover

    def _main():  # type: ignore[no-untyped-def]
        import sys

        from qtextra.utils.dev import apply_style, qapplication

        _ = qapplication()  # analysis:ignore
        dlg = QtColorListDialog(
            None,
            [
                "#ff0000",
                "#00ff00",
                "#000075",
                "#a9a9a9",
                "#ff0000",
                "#00ff00",
                "#000075",
                "#a9a9a9",
                "#ff0000",
                "#00ff00",
                "#000075",
                "#a9a9a9",
            ],
        )
        apply_style(dlg)
        dlg.show()
        sys.exit(dlg.exec_())  # type: ignore[attr-defined]

    _main()  # type: ignore[no-untyped-call]
