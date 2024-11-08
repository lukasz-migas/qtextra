"""Take screenshot dialog."""

from __future__ import annotations

import typing as ty
from functools import partial

from qtpy.QtWidgets import QLayout

import qtextra.helpers as hp
from qtextra.widgets.qt_dialog import QtFramelessPopup

if ty.TYPE_CHECKING:
    from qtextra._napari.image.wrapper import NapariImageView
    from qtextra._napari.line.wrapper import NapariLineView


class QtScreenshotDialog(QtFramelessPopup):
    """Popup to control screenshot/clipboard."""

    def __init__(self, wrapper: NapariImageView | NapariLineView, parent=None):
        self.wrapper = wrapper
        super().__init__(parent=parent)

    # noinspection PyAttributeOutsideInit
    def make_panel(self) -> QLayout:
        """Make layout."""
        size = self.wrapper.widget.canvas.size
        self.size_x = hp.make_int_spin_box(self, 50, 8000, 50, default=size[0], tooltip="Width of the screenshot.")
        self.size_y = hp.make_int_spin_box(self, 50, 8000, 50, default=size[1], tooltip="Height of the screenshot.")

        self.scale = hp.make_double_spin_box(
            self,
            0.1,
            5,
            0.5,
            n_decimals=2,
            default=1,
            tooltip="Increase the resolution of the screenshot. Value of 1.0 means that the screenshot will have the"
            " same resolution as the canvas, whereas, values >1 will increase the resolution by the specified ratio."
            " The higher this value is, the longer it will take to generate the screenshot.",
        )
        self.canvas_only = hp.make_checkbox(
            self,
            "",
            "Only screenshot the canvas",
            value=True,
        )
        self.clipboard_btn = hp.make_btn(
            self,
            "Copy to clipboard",
            tooltip="Copy screenshot to clipboard",
            func=self.on_copy_to_clipboard,
        )
        self.save_btn = hp.make_btn(
            self,
            "Save to file",
            tooltip="Save screenshot to file",
            func=self.on_save_figure,
        )

        layout = hp.make_form_layout()
        hp.style_form_layout(layout)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.addRow(self._make_move_handle("Screenshot controls"))
        layout.addRow("Width", self.size_x)
        layout.addRow("Height", self.size_y)
        layout.addRow("Up-sample", self.scale)
        layout.addRow("Canvas only", self.canvas_only)
        layout.addRow(self.clipboard_btn)
        layout.addRow(self.save_btn)
        return layout

    def on_save_figure(self):
        """Save figure."""
        from napari._qt.dialogs.screenshot_dialog import HOME_DIRECTORY, ScreenshotDialog

        save_func = partial(
            self.wrapper.widget.screenshot,
            size=(self.size_y.value(), self.size_x.value()),
            scale=self.scale.value(),
            canvas_only=self.canvas_only.isChecked(),
        )

        dialog = ScreenshotDialog(save_func, self.parent() or self, HOME_DIRECTORY, history=[])
        if dialog.exec_():
            pass

    def on_copy_to_clipboard(self):
        """Copy canvas to clipboard."""
        self.wrapper.widget.clipboard(
            size=(self.size_y.value(), self.size_x.value()),
            scale=self.scale.value(),
            canvas_only=self.canvas_only.isChecked(),
        )
