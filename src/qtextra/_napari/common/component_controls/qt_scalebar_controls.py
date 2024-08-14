"""ScaleBar model controls."""

import numpy as np
from napari._qt.widgets.qt_color_swatch import QColorSwatchEdit
from napari.utils.events import disconnect_events
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QFormLayout

import qtextra.helpers as hp
from qtextra._napari.common.components._scalebar_constants import UNITS_TRANSLATIONS
from qtextra._napari.common.components._viewer_constants import POSITION_TRANSLATIONS
from qtextra._napari.image.components.viewer_model import ViewerModel
from qtextra.widgets.qt_dialog import QtFramelessPopup


class QtScaleBarControls(QtFramelessPopup):
    """Popup to control scalebar values."""

    def __init__(self, viewer: ViewerModel, parent=None):
        self.viewer = viewer

        super().__init__(parent=parent)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setObjectName("scalebar")
        self.setMouseTracking(True)

        self.viewer.scale_bar.events.visible.connect(self._on_visible_change)
        self.viewer.scale_bar.events.colored.connect(self._on_colored_changed)
        self.viewer.scale_bar.events.color.connect(self._on_color_changed)
        self.viewer.scale_bar.events.box.connect(self._on_box_changed)
        self.viewer.scale_bar.events.box_color.connect(self._on_box_color_changed)
        self.viewer.scale_bar.events.ticks.connect(self._on_ticks_change)
        self.viewer.scale_bar.events.position.connect(self._on_position_change)
        self.viewer.scale_bar.events.unit.connect(self._on_unit_change)
        self.viewer.scale_bar.events.font_size.connect(self._on_font_size_change)
        self._on_visible_change()

    # noinspection PyAttributeOutsideInit
    def make_panel(self) -> QFormLayout:
        """Make panel."""
        self.visible_checkbox = hp.make_checkbox(
            self, "", "Show/hide scalebar", value=self.viewer.scale_bar.visible, func=self.on_change_visible
        )

        self.colored_checkbox = hp.make_checkbox(
            self, "", "Invert color", value=self.viewer.scale_bar.colored, func=self.on_change_colored
        )

        self.color_swatch = QColorSwatchEdit(
            initial_color=self.viewer.scale_bar.color, tooltip="Click to set color of the scalebar and text."
        )
        self.color_swatch.color_changed.connect(self.on_change_color)

        self.box_checkbox = hp.make_checkbox(
            self, "", "Show/hide scalebar", value=self.viewer.scale_bar.visible, func=self.on_change_box
        )

        self.box_color_swatch = QColorSwatchEdit(
            initial_color=self.viewer.scale_bar.box_color, tooltip="Click to set background color."
        )
        self.box_color_swatch.color_changed.connect(self.on_change_box_color)

        self.position_combobox = hp.make_combobox(self)
        hp.set_combobox_data(self.position_combobox, POSITION_TRANSLATIONS, self.viewer.scale_bar.position)
        self.position_combobox.currentTextChanged.connect(self.on_change_position)

        self.font_size_spinbox = hp.make_double_slider_with_text(self, 4, 20, step_size=1)
        self.font_size_spinbox.setValue(self.viewer.scale_bar.font_size)
        self.font_size_spinbox.valueChanged.connect(self.on_change_font_size)

        self.ticks_checkbox = hp.make_checkbox(self, "", "Display end ticks")
        self.ticks_checkbox.setChecked(self.viewer.scale_bar.ticks)
        self.ticks_checkbox.stateChanged.connect(self.on_change_ticks)

        pixel_size, unit = get_value_for_unit(self.viewer.scale_bar.unit)
        self.units_combobox = hp.make_combobox(self)
        hp.set_combobox_data(self.units_combobox, UNITS_TRANSLATIONS, unit)
        self.units_combobox.currentTextChanged.connect(self.on_change_unit)

        self.pixel_size = hp.make_double_spin_box(
            self,
            minimum=0.01,
            maximum=10_000,
            step_size=5,
            n_decimals=3,
            value=pixel_size,
            tooltip="Size of a single pixel in the selected units.",
        )
        self.pixel_size.valueChanged.connect(self.on_change_unit)

        layout = hp.make_form_layout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.addRow(self._make_move_handle("Scalebar controls"))
        layout.addRow(hp.make_label(self, "Visible"), self.visible_checkbox)
        layout.addRow(hp.make_label(self, "Colored"), self.colored_checkbox)
        layout.addRow(hp.make_label(self, "Color"), self.color_swatch)
        layout.addRow(hp.make_label(self, "Show box"), self.box_checkbox)
        layout.addRow(hp.make_label(self, "Box color"), self.box_color_swatch)
        layout.addRow(hp.make_label(self, "Scalebar position"), self.position_combobox)
        layout.addRow(hp.make_label(self, "Font size"), self.font_size_spinbox)
        layout.addRow(hp.make_label(self, "Show ticks"), self.ticks_checkbox)
        layout.addRow(hp.make_label(self, "Units"), self.units_combobox)
        layout.addRow(hp.make_label(self, "Pixel size"), self.pixel_size)
        layout.setSpacing(2)
        return layout

    def on_change_color(self, color: np.ndarray) -> None:
        """Update color."""
        with self.viewer.scale_bar.events.color.blocker(self._on_color_changed):
            self.viewer.scale_bar.color = color

    def _on_color_changed(self, _event=None):
        """Receive layer.current_edge_color() change event and update view."""
        with hp.qt_signals_blocked(self.color_swatch):
            self.color_swatch.setColor(self.viewer.scale_bar.color)

    def on_change_box(self) -> None:
        """Update visibility checkbox."""
        self.viewer.scale_bar.box = self.box_checkbox.isChecked()

    def _on_box_changed(self, _event=None) -> None:
        """Update visibility checkbox."""
        with self.viewer.scale_bar.events.box.blocker():
            self.box_checkbox.setChecked(self.viewer.scale_bar.box)

    def on_change_box_color(self, color: np.ndarray) -> None:
        """Update color."""
        with self.viewer.scale_bar.events.box_color.blocker(self._on_box_color_changed):
            self.viewer.scale_bar.box_color = color

    def _on_box_color_changed(self, _event=None):
        """Receive layer.current_edge_color() change event and update view."""
        with hp.qt_signals_blocked(self.box_color_swatch):
            self.box_color_swatch.setColor(self.viewer.scale_bar.box_color)

    def on_change_visible(self) -> None:
        """Update visibility checkbox."""
        self.viewer.scale_bar.visible = self.visible_checkbox.isChecked()

    def _on_visible_change(self, _event=None) -> None:
        """Update visibility checkbox."""
        with self.viewer.scale_bar.events.visible.blocker():
            self.visible_checkbox.setChecked(self.viewer.scale_bar.visible)
        hp.enable_with_opacity(
            self,
            [
                self.font_size_spinbox,
                self.units_combobox,
                self.pixel_size,
                self.color_swatch,
                self.box_color_swatch,
                self.position_combobox,
                self.ticks_checkbox,
                self.colored_checkbox,
                self.box_checkbox,
            ],
            self.viewer.scale_bar.visible,
        )

    def on_change_colored(self) -> None:
        """Update colored checkbox."""
        self.viewer.scale_bar.colored = self.colored_checkbox.isChecked()

    def _on_colored_changed(self, _event=None) -> None:
        """Update colored checkbox."""
        with self.viewer.scale_bar.events.colored.blocker():
            self.colored_checkbox.setChecked(self.viewer.scale_bar.colored)

    def on_change_ticks(self) -> None:
        """Update visibility checkbox."""
        self.viewer.scale_bar.ticks = self.ticks_checkbox.isChecked()

    def _on_ticks_change(self, _event=None) -> None:
        """Update visibility checkbox."""
        with self.viewer.scale_bar.events.ticks.blocker():
            self.ticks_checkbox.setChecked(self.viewer.scale_bar.ticks)

    def on_change_position(self) -> None:
        """Update visibility checkbox."""
        self.viewer.scale_bar.position = self.position_combobox.currentData()

    def _on_position_change(self, _event=None) -> None:
        """Update visibility checkbox."""
        with self.viewer.scale_bar.events.position.blocker():
            hp.set_combobox_current_index(self.position_combobox, self.viewer.scale_bar.position)

    def on_change_unit(self, _event=None) -> None:
        """Update dimension."""
        unit = self.units_combobox.currentData()
        unit = f"{self.pixel_size.value()}{unit}" if unit == "um" else unit
        self.viewer.scale_bar.unit = unit

    def _on_unit_change(self, _event=None) -> None:
        """Update visibility checkbox."""
        with self.viewer.scale_bar.events.unit.blocker():
            unit = self.viewer.scale_bar.unit
            hp.set_combobox_current_index(self.units_combobox, unit)

    def on_change_font_size(self) -> None:
        """Update visibility checkbox."""
        self.viewer.scale_bar.font_size = self.font_size_spinbox.value()

    def _on_font_size_change(self, _event=None) -> None:
        """Update visibility checkbox."""
        with self.viewer.scale_bar.events.font_size.blocker():
            self.font_size_spinbox.setValue(self.viewer.scale_bar.font_size)

    def close(self) -> None:
        """Disconnect events when widget is closing."""
        disconnect_events(self.viewer.scale_bar.events, self)
        super().close()


def get_value_for_unit(value: str) -> tuple[float, str]:
    """Extract unit from value."""
    if value == "" or value is None:
        return 1, UNITS_TRANSLATIONS[""]
    elif value == "px":
        return 1, UNITS_TRANSLATIONS[value]
    elif "um" in value:
        if value[:-2] == "":
            return 1, UNITS_TRANSLATIONS["um"]
        return float(value[:-2]), UNITS_TRANSLATIONS["um"]
    return 1, UNITS_TRANSLATIONS[""]
