"""ScaleBar model controls."""

import numpy as np
from napari._qt.widgets.qt_color_swatch import QColorSwatchEdit
from napari.utils.events import disconnect_events
from qtpy.QtCore import Qt, Slot  # type: ignore[attr-defined]
from qtpy.QtWidgets import QFormLayout

import qtextra.helpers as hp
from qtextra._napari.common.components._viewer_constants import TEXT_POSITION_TRANSLATIONS
from qtextra._napari.image.components.viewer_model import ViewerModel
from qtextra.widgets.qt_dialog import QtFramelessPopup


class QtTextOverlayControls(QtFramelessPopup):
    """Popup to control scalebar values."""

    def __init__(self, viewer: ViewerModel, parent=None):
        self.viewer = viewer

        super().__init__(parent=parent)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setObjectName("text_overlay")
        self.setMouseTracking(True)

        self.viewer.text_overlay.events.visible.connect(self._on_visible_change)
        self.viewer.text_overlay.events.color.connect(self._on_color_change)
        self.viewer.text_overlay.events.position.connect(self._on_position_change)
        self.viewer.text_overlay.events.font_size.connect(self._on_font_size_change)
        self.viewer.text_overlay.events.text.connect(self._on_text_change)
        self._on_visible_change()

    # noinspection PyAttributeOutsideInit
    def make_panel(self) -> QFormLayout:
        """Make panel."""
        self.visible_checkbox = hp.make_checkbox(
            self, "", "Show/hide text", value=self.viewer.text_overlay.visible, func=self.on_change_visible
        )

        self.text_edit = hp.make_line_edit(self, self.viewer.text_overlay.text, placeholder="Text...")
        self.text_edit.textChanged.connect(self.on_change_text)

        self.position_combobox = hp.make_combobox(self)
        hp.set_combobox_data(self.position_combobox, TEXT_POSITION_TRANSLATIONS, self.viewer.text_overlay.position)
        self.position_combobox.currentTextChanged.connect(self.on_change_position)

        self.color_swatch = QColorSwatchEdit(self, initial_color=self.viewer.text_overlay.color)
        self.color_swatch.color_changed.connect(self.on_change_color)

        self.font_size_spinbox = hp.make_double_slider_with_text(
            self, 4, 32, step_size=1, value=self.viewer.text_overlay.font_size, func=self.on_change_font_size
        )

        layout = hp.make_form_layout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.addRow(self._make_move_handle("Text overlay controls"))
        layout.addRow(hp.make_label(self, "Visible"), self.visible_checkbox)
        layout.addRow(hp.make_label(self, "Text"), self.text_edit)
        layout.addRow(hp.make_label(self, "Text position"), self.position_combobox)
        layout.addRow(hp.make_label(self, "Color"), self.color_swatch)
        layout.addRow(hp.make_label(self, "Font size"), self.font_size_spinbox)
        layout.setSpacing(2)
        return layout

    def on_change_visible(self):
        """Update visibility checkbox."""
        self.viewer.text_overlay.visible = self.visible_checkbox.isChecked()

    def _on_visible_change(self, _event=None):
        """Update visibility checkbox."""
        with self.viewer.text_overlay.events.visible.blocker():
            self.visible_checkbox.setChecked(self.viewer.text_overlay.visible)
        hp.enable_with_opacity(
            self,
            [
                self.color_swatch,
                self.text_edit,
                self.position_combobox,
                self.font_size_spinbox,
            ],
            self.viewer.text_overlay.visible,
        )

    def on_change_text(self):
        """Update visibility checkbox."""
        self.viewer.text_overlay.text = self.text_edit.text()

    def _on_text_change(self, _event=None):
        """Update visibility checkbox."""
        with self.viewer.text_overlay.events.text.blocker():
            self.text_edit.setText(self.viewer.text_overlay.text)

    def on_change_position(self):
        """Update visibility checkbox."""
        self.viewer.text_overlay.position = self.position_combobox.currentData()

    def _on_position_change(self, _event=None):
        """Update visibility checkbox."""
        with self.viewer.text_overlay.events.position.blocker():
            hp.set_combobox_current_index(self.position_combobox, self.viewer.text_overlay.position)

    def on_change_font_size(self):
        """Update visibility checkbox."""
        self.viewer.text_overlay.font_size = self.font_size_spinbox.value()

    def _on_font_size_change(self, _event=None):
        """Update visibility checkbox."""
        with self.viewer.text_overlay.events.font_size.blocker():
            self.font_size_spinbox.setValue(self.viewer.text_overlay.font_size)

    @Slot(np.ndarray)  # type: ignore
    def on_change_color(self, color: np.ndarray):
        """Update edge color of layer model from color picker user input."""
        self.viewer.text_overlay.color = color

    def _on_color_change(self, _event=None):
        """Update visibility checkbox."""
        with hp.qt_signals_blocked(self.color_swatch):
            self.color_swatch.setColor(self.viewer.text_overlay.color)

    def close(self):
        """Disconnect events when widget is closing."""
        disconnect_events(self.viewer.text_overlay.events, self)
        super().close()
