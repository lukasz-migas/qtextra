"""ColorBar model controls."""

from napari._qt.widgets.qt_color_swatch import QColorSwatchEdit
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QFormLayout

import qtextra.helpers as hp
from qtextra._napari.common.components._viewer_constants import POSITION_TRANSLATIONS
from qtextra._napari.image.components.viewer_model import ViewerModel
from qtextra.widgets.qt_dialog import QtFramelessPopup


class QtColorBarControls(QtFramelessPopup):
    """Popup to control scalebar values."""

    def __init__(self, viewer: ViewerModel, parent=None):
        self.viewer = viewer

        super().__init__(parent=parent)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setObjectName("colorbar")
        self.setMouseTracking(True)

        self.viewer.color_bar.events.visible.connect(self._on_visible_change)
        self.viewer.color_bar.events.border_width.connect(self._on_border_width_change)
        self.viewer.color_bar.events.border_color.connect(self._on_border_color_change)
        self.viewer.color_bar.events.position.connect(self._on_position_change)
        self.viewer.color_bar.events.label_size.connect(self._on_tick_font_size_change)
        self.viewer.color_bar.events.label_color.connect(self._on_tick_color_change)
        self._on_visible_change()

    # noinspection PyAttributeOutsideInit
    def make_panel(self) -> QFormLayout:
        """Make panel."""
        self.visible_checkbox = hp.make_checkbox(
            self, "", "Show/hide colorbar", value=self.viewer.color_bar.visible, func=self.on_change_visible
        )

        self.position_combobox = hp.make_combobox(self)
        hp.set_combobox_data(self.position_combobox, POSITION_TRANSLATIONS, self.viewer.color_bar.position)
        self.position_combobox.currentTextChanged.connect(self.on_change_position)

        self.border_color_swatch = QColorSwatchEdit(self, initial_color=self.viewer.color_bar.border_color)
        self.border_color_swatch.color_changed.connect(self.on_change_border_color)

        self.border_width_spinbox = hp.make_slider_with_text(
            self, 0, 10, step_size=1, value=self.viewer.color_bar.border_width, func=self.on_change_border_width
        )

        self.label_color_swatch = QColorSwatchEdit(self, initial_color=self.viewer.color_bar.label_color)
        self.label_color_swatch.color_changed.connect(self.on_change_tick_color)

        self.label_size_spinbox = hp.make_slider_with_text(
            self, 4, 24, step_size=1, value=self.viewer.color_bar.label_size, func=self.on_change_tick_font_size
        )

        layout = hp.make_form_layout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.addRow(self._make_move_handle("Colorbar controls"))
        layout.addRow(hp.make_label(self, "Visible"), self.visible_checkbox)
        layout.addRow(hp.make_label(self, "Colorbar position"), self.position_combobox)
        layout.addRow(hp.make_label(self, "Border color"), self.border_color_swatch)
        layout.addRow(hp.make_label(self, "Border width"), self.border_width_spinbox)
        layout.addRow(hp.make_label(self, "Label color"), self.label_color_swatch)
        layout.addRow(hp.make_label(self, "Label size"), self.label_size_spinbox)
        layout.setSpacing(2)
        return layout

    def on_change_visible(self):
        """Update visibility checkbox."""
        self.viewer.color_bar.visible = self.visible_checkbox.isChecked()

    def _on_visible_change(self, _event=None):
        """Update visibility checkbox."""
        with self.viewer.color_bar.events.visible.blocker():
            self.visible_checkbox.setChecked(self.viewer.color_bar.visible)
        hp.enable_with_opacity(
            self,
            [
                self.position_combobox,
                self.border_color_swatch,
                self.border_width_spinbox,
                self.label_color_swatch,
                self.label_size_spinbox,
            ],
            self.viewer.color_bar.visible,
        )

    def on_change_position(self):
        """Update visibility checkbox."""
        self.viewer.color_bar.position = self.position_combobox.currentData()

    def _on_position_change(self, _event=None):
        """Update visibility checkbox."""
        with self.viewer.color_bar.events.position.blocker():
            hp.set_combobox_current_index(self.position_combobox, self.viewer.color_bar.position)

    def on_change_border_width(self):
        """Update visibility checkbox."""
        self.viewer.color_bar.border_width = self.border_width_spinbox.value()

    def _on_border_width_change(self, _event=None):
        """Update visibility checkbox."""
        with self.viewer.color_bar.events.border_width.blocker():
            self.border_width_spinbox.setValue(self.viewer.color_bar.border_width)

    def on_change_border_color(self, color: str):
        """Update edge color of layer model from color picker user input."""
        with self.viewer.color_bar.events.border_color.blocker():
            self.viewer.color_bar.border_color = color

    def _on_border_color_change(self, _event=None):
        """Update visibility checkbox."""
        with hp.qt_signals_blocked(self.border_color_swatch):
            self.border_color_swatch.setColor(self.viewer.color_bar.border_color)

    def on_change_tick_font_size(self):
        """Update visibility checkbox."""
        self.viewer.color_bar.label_size = self.label_size_spinbox.value()

    def _on_tick_font_size_change(self, _event=None):
        """Update visibility checkbox."""
        with self.viewer.color_bar.events.label_size.blocker():
            self.label_size_spinbox.setValue(self.viewer.color_bar.label_size)

    def on_change_tick_color(self, color: str):
        """Update edge color of layer model from color picker user input."""
        with self.viewer.color_bar.events.label_color.blocker():
            self.viewer.color_bar.label_color = color

    def _on_tick_color_change(self, _event=None):
        """Update visibility checkbox."""
        with hp.qt_signals_blocked(self.label_color_swatch):
            self.label_color_swatch.setColor(self.viewer.color_bar.label_color)
