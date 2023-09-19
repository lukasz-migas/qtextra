"""ScaleBar model controls."""
from napari.utils.events import disconnect_events
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QFormLayout

import qtextra.helpers as hp
from qtextra._napari.common.components._viewer_constants import POSITION_TRANSLATIONS
from qtextra._napari.image.components.viewer_model import ViewerModel
from qtextra._napari.image.utils.dimension import UNITS_TRANSLATIONS
from qtextra.widgets.qt_dialog import QtFramelessPopup


class QtScaleBarControls(QtFramelessPopup):
    """Popup to control scalebar values."""

    def __init__(self, viewer: ViewerModel, parent=None):
        self.viewer = viewer

        super().__init__(parent=parent)
        self.setAttribute(Qt.WA_DeleteOnClose)  # type: ignore

        self.viewer.scale_bar.events.visible.connect(self._on_visible_change)
        self.viewer.scale_bar.events.colored.connect(self._on_colored_changed)
        self.viewer.scale_bar.events.ticks.connect(self._on_ticks_change)
        self.viewer.scale_bar.events.position.connect(self._on_position_change)
        self.viewer.scale_bar.events.unit.connect(self._on_unit_change)
        self.viewer.scale_bar.events.font_size.connect(self._on_font_size_change)

        self.setObjectName("scalebar")
        self.setMouseTracking(True)

    # noinspection PyAttributeOutsideInit
    def make_panel(self) -> QFormLayout:
        """Make panel."""
        self.visible_checkbox = hp.make_checkbox(self, "", "Show/hide scalebar")
        self.visible_checkbox.setChecked(self.viewer.scale_bar.visible)
        self.visible_checkbox.stateChanged.connect(self.on_change_visible)  # type: ignore

        self.colored_checkbox = hp.make_checkbox(self, "", "Invert color")
        self.colored_checkbox.setChecked(self.viewer.scale_bar.colored)
        self.colored_checkbox.stateChanged.connect(self.on_change_colored)  # type: ignore

        self.position_combobox = hp.make_combobox(self)
        hp.set_combobox_data(self.position_combobox, POSITION_TRANSLATIONS, self.viewer.scale_bar.position)
        self.position_combobox.currentTextChanged.connect(self.on_change_position)  # type: ignore

        self.font_size_spinbox = hp.make_double_spin_box(self, minimum=4, maximum=20, step_size=1)
        self.font_size_spinbox.setValue(self.viewer.scale_bar.font_size)
        self.font_size_spinbox.valueChanged.connect(self.on_change_font_size)  # type: ignore

        self.ticks_checkbox = hp.make_checkbox(self, "", "Display end ticks")
        self.ticks_checkbox.setChecked(self.viewer.scale_bar.ticks)
        self.ticks_checkbox.stateChanged.connect(self.on_change_ticks)  # type: ignore

        self.units_combobox = hp.make_combobox(self)
        hp.set_combobox_data(self.units_combobox, UNITS_TRANSLATIONS)  # , self.viewer.scale_bar.unit)
        self.units_combobox.currentTextChanged.connect(self.on_change_unit)  # type: ignore

        self.pixel_size = hp.make_double_spin_box(self, minimum=0.01, maximum=10_000, step_size=5, n_decimals=3)
        self.pixel_size.valueChanged.connect(self.on_change_unit)  # type: ignore

        layout = hp.make_form_layout(self)
        layout.addRow(self._make_move_handle())
        layout.addRow(hp.make_label(self, "Visible"), self.visible_checkbox)
        layout.addRow(hp.make_label(self, "Colored"), self.colored_checkbox)
        layout.addRow(hp.make_label(self, "Scalebar position"), self.position_combobox)
        layout.addRow(hp.make_label(self, "Font size"), self.font_size_spinbox)
        layout.addRow(hp.make_label(self, "Show ticks"), self.ticks_checkbox)
        layout.addRow(hp.make_label(self, "Units"), self.units_combobox)
        layout.addRow(hp.make_label(self, "Pixel size"), self.pixel_size)
        layout.setSpacing(2)
        return layout

    def on_change_visible(self) -> None:
        """Update visibility checkbox."""
        self.viewer.scale_bar.visible = self.visible_checkbox.isChecked()

    def _on_visible_change(self, _event=None) -> None:
        """Update visibility checkbox."""
        with self.viewer.scale_bar.events.visible.blocker():
            self.visible_checkbox.setChecked(self.viewer.scale_bar.visible)

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
