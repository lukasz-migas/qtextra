"""Crosshair model controls."""

from napari._qt.widgets.qt_color_swatch import QColorSwatchEdit
from napari.utils.events import disconnect_events
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QFormLayout

import qtextra.helpers as hp
from qtextra._napari.image.components.viewer_model import ViewerModel
from qtextra.widgets.qt_dialog import QtFramelessPopup


class QtCrosshairControls(QtFramelessPopup):
    """Popup to control crosshair values."""

    def __init__(self, viewer: ViewerModel, parent=None):
        self.viewer = viewer

        super().__init__(parent=parent)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setObjectName("crosshair")
        self.setMouseTracking(True)

        self.viewer.cross_hair.events.visible.connect(self._on_visible_change)
        self.viewer.cross_hair.events.width.connect(self._on_width_change)
        self.viewer.cross_hair.events.color.connect(self._on_color_change)
        self.viewer.cross_hair.events.window.connect(self._on_window_change)
        self.viewer.cross_hair.events.position.connect(self._on_position_change)
        self._on_visible_change()

    # noinspection PyAttributeOutsideInit
    def make_panel(self) -> QFormLayout:
        """Make panel."""
        self.visible_checkbox = hp.make_checkbox(
            self, "", "Show/hide crosshair", value=self.viewer.cross_hair.visible, func=self.on_change_visible
        )

        self.autohide_checkbox = hp.make_checkbox(
            self, "", "Auto-hide crosshair", value=self.viewer.cross_hair.auto_hide, func=self.on_change_auto_hide
        )

        self.position_x_spin = hp.make_int_spin_box(
            self, 0, 100_000, value=self.viewer.cross_hair.position[1], func=self.on_change_position
        )

        self.position_y_spin = hp.make_int_spin_box(
            self, 0, 100_000, value=self.viewer.cross_hair.position[0], func=self.on_change_position
        )

        self.width_spinbox = hp.make_slider_with_text(
            self, 1, 10, step_size=1, value=self.viewer.cross_hair.width, func=self.on_change_width
        )

        self.window_spinbox = hp.make_slider_with_text(
            self, 1, 10, step_size=1, value=self.viewer.cross_hair.window, func=self.on_change_window
        )

        self.color_swatch = QColorSwatchEdit(self, initial_color=self.viewer.cross_hair.color)
        self.color_swatch.color_changed.connect(self.on_change_color)

        layout = hp.make_form_layout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.addRow(self._make_move_handle("Crosshair controls"))
        layout.addRow(hp.make_label(self, "Visible"), self.visible_checkbox)
        layout.addRow(hp.make_label(self, "Auto-hide"), self.autohide_checkbox)
        layout.addRow(hp.make_label(self, "Position (x)"), self.position_x_spin)
        layout.addRow(hp.make_label(self, "Position (y)"), self.position_y_spin)
        layout.addRow(hp.make_label(self, "Line width"), self.width_spinbox)
        layout.addRow(hp.make_label(self, "Window size"), self.window_spinbox)
        layout.addRow(hp.make_label(self, "Color"), self.color_swatch)
        layout.setSpacing(2)
        return layout

    def on_change_visible(self):
        """Update visibility checkbox."""
        self.viewer.cross_hair.visible = self.visible_checkbox.isChecked()

    def on_change_auto_hide(self):
        """Update visibility checkbox."""
        self.viewer.cross_hair.auto_hide = self.visible_checkbox.isChecked()

    def _on_visible_change(self, _event=None):
        """Update visibility checkbox."""
        with self.viewer.cross_hair.events.visible.blocker():
            self.visible_checkbox.setChecked(self.viewer.cross_hair.visible)
        hp.enable_with_opacity(
            self,
            [
                self.color_swatch,
                self.autohide_checkbox,
                self.position_x_spin,
                self.position_y_spin,
                self.width_spinbox,
                self.window_spinbox,
            ],
            self.viewer.cross_hair.visible,
        )

    def on_change_position(self):
        """Update visibility checkbox."""
        self.viewer.cross_hair.position = (self.position_y_spin.value(), self.position_x_spin.value())

    def _on_position_change(self, _event=None):
        """Update visibility checkbox."""
        with self.viewer.cross_hair.events.position.blocker():
            self.position_y_spin.setValue(self.viewer.cross_hair.position[0])
            self.position_x_spin.setValue(self.viewer.cross_hair.position[1])

    def on_change_width(self):
        """Update visibility checkbox."""
        self.viewer.cross_hair.width = self.width_spinbox.value()

    def _on_width_change(self, _event=None):
        """Update visibility checkbox."""
        with self.viewer.cross_hair.events.width.blocker():
            self.width_spinbox.setValue(self.viewer.cross_hair.width)

    def on_change_window(self):
        """Update visibility checkbox."""
        self.viewer.cross_hair.window = self.window_spinbox.value()

    def _on_window_change(self, _event=None):
        """Update visibility checkbox."""
        with self.viewer.cross_hair.events.window.blocker():
            self.window_spinbox.setValue(self.viewer.cross_hair.window)

    def on_change_color(self, color: str):
        """Update edge color of layer model from color picker user input."""
        self.viewer.cross_hair.color = color

    def _on_color_change(self, _event=None):
        """Update visibility checkbox."""
        with hp.qt_signals_blocked(self.color_swatch):
            self.color_swatch.setColor(self.viewer.cross_hair.color)

    def close(self):
        """Disconnect events when widget is closing."""
        disconnect_events(self.viewer.cross_hair.events, self)
        super().close()
