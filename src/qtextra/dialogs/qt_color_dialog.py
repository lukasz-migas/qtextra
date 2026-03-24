"""Simple color scheme builder."""

from __future__ import annotations

import typing as ty
from copy import deepcopy

from koyo.color import colormap_to_hex
from pydantic.color import Color
from qtpy.QtCore import Slot
from qtpy.QtWidgets import QLayout, QWidget

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
    """Dialog for editing a list of colors, with optional colormap presets."""

    def __init__(
        self,
        parent: QWidget | None,
        colors: ty.Union[ty.List[str], ty.List[Color]],
        message: str = "Click any swatch to change its color.",
    ):
        self.colors: ty.List[str] = parse_colors(colors)
        self.new_colors: ty.List[str] = deepcopy(self.colors)
        self.message = message
        super().__init__(parent, title="Edit colors")

    @property
    def n_colors(self) -> int:
        """Return the number of colors."""
        return len(self.colors)

    # noinspection PyAttributeOutsideInit
    def make_panel(self) -> QLayout:
        """Make panel."""
        info_label = hp.make_label(self, self.message, wrap=True)

        color_layout, self.swatches = hp.make_swatch_grid(
            self,
            self.colors,
            self.on_update_color,
            use_flow_layout=True,
        )

        self.colormap_combo = hp.make_combobox(
            self,
            ["custom", "viridis", "inferno", "magma", "plasma", "cividis", "twilight"],
            func=self.on_set_colormap,
            tooltip="Apply a built-in colormap to all swatches",
        )
        self.randomize_btn = hp.make_qta_btn(
            self,
            "shuffle",
            tooltip="Randomize colors",
            medium=False,
            func=self.on_randomize,
        )
        self.invert_chk = hp.make_checkbox(
            self,
            "Invert",
            tooltip="Reverse the colormap order",
            func=self.on_set_colormap,
        )
        hp.disable_widgets(self.invert_chk, disabled=self.colormap_combo.currentText() == "custom")

        colormap_row = hp.make_h_layout(
            self.colormap_combo,
            self.randomize_btn,
            self.invert_chk,
            spacing=6,
        )

        ok_btn = hp.make_btn(self, "OK", func=self.accept, object_name="success_btn")
        cancel_btn = hp.make_btn(self, "Cancel", func=self.reject, object_name="cancel_btn")
        footer = hp.make_h_layout(stretch_before=True, spacing=8)
        footer.addWidget(cancel_btn)
        footer.addWidget(ok_btn)

        layout = hp.make_v_layout(spacing=12, margin=(16, 12, 16, 12))
        layout.addWidget(info_label)
        layout.addWidget(hp.make_h_line(self))
        layout.addWidget(hp.make_label(self, "Colormap", bold=True))
        layout.addLayout(colormap_row)
        layout.addWidget(hp.make_h_line(self))
        layout.addWidget(hp.make_label(self, "Colors", bold=True))
        layout.addLayout(color_layout)
        layout.addStretch()
        layout.addWidget(hp.make_h_line(self))
        layout.addLayout(footer)
        return layout

    def on_randomize(self) -> None:
        """Randomize colors."""
        from koyo.color import get_random_hex_color

        self.colors = [get_random_hex_color() for _ in range(self.n_colors)]
        if self.colormap_combo.currentText() == "custom":
            self.on_set_colormap()
        else:
            self.colormap_combo.setCurrentText("custom")

    @Slot()  # type: ignore[misc]
    def on_set_colormap(self) -> None:
        """Set colors based on colormap."""
        import matplotlib.cm

        colormap = self.colormap_combo.currentText()
        hp.disable_widgets(self.invert_chk, disabled=colormap == "custom")
        if colormap == "custom":
            colors = self.colors
        else:
            colormap += "_r" if self.invert_chk.isChecked() else ""
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
        sys.exit(dlg.exec())

    _main()  # type: ignore[no-untyped-call]
