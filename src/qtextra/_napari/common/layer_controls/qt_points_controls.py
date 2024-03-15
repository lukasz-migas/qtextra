"""Points controls."""

import numpy as np
from napari._qt.widgets.qt_color_swatch import QColorSwatchEdit
from napari.layers import Points
from napari.layers.points._points_constants import Mode
from napari.utils.events import disconnect_events
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QButtonGroup, QHBoxLayout

import qtextra.helpers as hp
from qtextra._napari.common.layer_controls.qt_layer_controls_base import QtLayerControls
from qtextra._napari.common.layers._points_constants import SYMBOL_TRANSLATION
from qtextra._napari.common.widgets.qt_mode_button import QtModePushButton, QtModeRadioButton


class QtPointsControls(QtLayerControls):
    """Qt view and controls for the napari Points layer."""

    layer: Points

    def __init__(self, layer: Points):
        super().__init__(layer)

        self.layer.events.mode.connect(self._on_mode_change)
        self.layer.events.n_dimensional.connect(self._on_out_of_slice_change)
        self.layer.events.symbol.connect(self._on_symbol_change)
        self.layer.events.size.connect(self._on_size_change)
        self.layer.events.current_edge_color.connect(self._on_current_edge_color_change)
        self.layer._edge.events.current_color.connect(self._on_current_edge_color_change)
        self.layer.events.current_face_color.connect(self._on_current_face_color_change)
        self.layer._face.events.current_color.connect(self._on_current_face_color_change)
        self.layer.events.editable.connect(self._on_editable_or_visible_change)
        self.layer.events.visible.connect(self._on_editable_or_visible_change)
        self.layer.text.events.visible.connect(self._on_text_visibility_change)

        if self.layer.size.size:
            max_value = max(100, int(np.max(self.layer.size)) + 1)
        else:
            max_value = 100
        self.sizeSlider = hp.make_slider_with_text(self, 1, max_value, tooltip="Scatter point size")
        self.sizeSlider.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.sizeSlider.setValue(int(self.layer.current_size))
        self.sizeSlider.valueChanged.connect(self.on_change_size)

        self.faceColorEdit = QColorSwatchEdit(
            initial_color=self.layer.current_face_color, tooltip="Click to set current face color"
        )
        self.faceColorEdit.color_changed.connect(self.on_change_face_color)

        self.edgeColorEdit = QColorSwatchEdit(
            initial_color=self.layer.current_edge_color, tooltip="Click to set current edge color"
        )
        self.edgeColorEdit.color_changed.connect(self.on_change_edge_color)

        self.symbolComboBox = hp.make_combobox(self, tooltip="Next marker symbol")
        hp.set_combobox_data(self.symbolComboBox, SYMBOL_TRANSLATION, self.layer.current_symbol)
        self.symbolComboBox.currentTextChanged.connect(self.on_change_symbol)

        self.outOfSliceCheckBox = hp.make_checkbox(
            self,
            tooltip="N-dimensional points",
            checked=self.layer.out_of_slice_display,
            func=self.on_change_out_of_slice,
        )

        self.select_button = QtModeRadioButton(
            layer,
            "select_points",
            Mode.SELECT,
            tooltip="Select points",
        )
        self.addition_button = QtModeRadioButton(layer, "add_points", Mode.ADD, tooltip="Add points (P)")
        self.panzoom_button = QtModeRadioButton(
            layer,
            "pan_zoom",
            Mode.PAN_ZOOM,
            tooltip="Pan/zoom",
            checked=True,
        )
        self.delete_button = QtModePushButton(
            layer,
            "delete_shape",
            func=self.layer.remove_selected,
            tooltip="Delete selected points",
        )

        self.text_display_checkbox = hp.make_checkbox(self, tooltip="Toggle text visibility")
        self.text_display_checkbox.setChecked(self.layer.text.visible)
        self.text_display_checkbox.stateChanged.connect(self.on_change_text_visibility)

        self.button_group = QButtonGroup(self)
        self.button_group.addButton(self.select_button)
        self.button_group.addButton(self.addition_button)
        self.button_group.addButton(self.panzoom_button)

        button_row = QHBoxLayout()
        button_row.addStretch(1)
        button_row.addWidget(self.addition_button)
        button_row.addWidget(self.select_button)
        button_row.addWidget(self.panzoom_button)
        button_row.addWidget(self.delete_button)
        button_row.setContentsMargins(0, 0, 0, 5)
        button_row.setSpacing(4)

        # grid_layout created in QtLayerControls
        self.layout().addRow(self.opacityLabel, self.opacitySlider)
        self.layout().addRow(hp.make_label(self, "Points size"), self.sizeSlider)
        self.layout().addRow(hp.make_label(self, "Blending"), self.blendComboBox)
        self.layout().addRow(hp.make_label(self, "Symbol"), self.symbolComboBox)
        self.layout().addRow(hp.make_label(self, "Face color"), self.faceColorEdit)
        self.layout().addRow(hp.make_label(self, "Edge color"), self.edgeColorEdit)
        self.layout().addRow(hp.make_label(self, "Display text"), self.text_display_checkbox)
        self.layout().addRow(hp.make_label(self, "Out-of-slice display"), self.outOfSliceCheckBox)
        self.layout().addRow(hp.make_label(self, "Editable"), self.editable_checkbox)
        self.layout().addRow(button_row)
        self._on_editable_or_visible_change()

    def _on_mode_change(self, event):
        """Update ticks in checkbox widgets when points layer mode is changed."""
        mode = event.mode
        if mode == Mode.ADD:
            self.addition_button.setChecked(True)
        elif mode == Mode.SELECT:
            self.select_button.setChecked(True)
        elif mode == Mode.PAN_ZOOM:
            self.panzoom_button.setChecked(True)
        else:
            raise ValueError("Mode not recognized")

    def on_change_symbol(self, text):
        """Change marker symbol of the points on the layer model."""
        self.layer.symbol = self.symbolComboBox.currentData()

    def _on_symbol_change(self, event):
        """Receive marker symbol change event and update the dropdown menu."""
        with self.layer.events.symbol.blocker():
            hp.set_combobox_current_index(self.symbolComboBox, self.layer.current_symbol.value)

    def on_change_size(self, value):
        """Change size of points on the layer model."""
        self.layer.current_size = value

    def _on_size_change(self, event=None):
        """Receive layer model size change event and update point size slider."""
        with self.layer.events.size.blocker():
            self.sizeSlider.setValue(int(self.layer.current_size))

    def on_change_out_of_slice(self, state):
        """Toggle n-dimensional state of label layer."""
        self.layer.out_of_slice_display = state == Qt.CheckState.Checked

    def _on_out_of_slice_change(self, event):
        """Receive layer model n-dimensional change event and update checkbox."""
        with self.layer.events.n_dimensional.blocker():
            self.outOfSliceCheckBox.setChecked(self.layer.n_dimensional)

    def on_change_text_visibility(self, state):
        """Toggle the visibility of the text."""
        self.layer.text.visible = state == Qt.CheckState.Checked

    def _on_text_visibility_change(self, _event=None) -> None:
        """Receive layer model text visibility change change event and update checkbox."""
        with self.layer.text.events.visible.blocker():
            self.text_display_checkbox.setChecked(self.layer.text.visible)

    def on_change_face_color(self, color: np.ndarray) -> None:
        """Update face color of layer model from color picker user input."""
        with self.layer.events.current_face_color.blocker():
            self.layer.current_face_color = color

    def _on_current_face_color_change(self, _event=None) -> None:
        """Receive layer.current_face_color() change event and update view."""
        with hp.qt_signals_blocked(self.faceColorEdit):
            self.faceColorEdit.setColor(self.layer.current_face_color)

    def on_change_edge_color(self, color: np.ndarray) -> None:
        """Update edge color of layer model from color picker user input."""
        with self.layer.events.current_edge_color.blocker():
            self.layer.current_edge_color = color

    def _on_current_edge_color_change(self, _event=None):
        """Receive layer.current_edge_color() change event and update view."""
        with hp.qt_signals_blocked(self.edgeColorEdit):
            self.edgeColorEdit.setColor(self.layer.current_edge_color)

    def _on_editable_or_visible_change(self, event=None) -> None:
        """Receive layer model editable change event & enable/disable buttons."""
        hp.enable_with_opacity(
            self,
            [
                self.select_button,
                self.addition_button,
                self.delete_button,
                self.symbolComboBox,
                self.sizeSlider,
                self.faceColorEdit,
                self.edgeColorEdit,
                self.blendComboBox,
                self.opacitySlider,
                self.outOfSliceCheckBox,
                self.text_display_checkbox,
            ],
            self.layer.editable and self.layer.visible,
        )
        super()._on_editable_or_visible_change(event)

    def close(self):
        """Disconnect events when widget is closing."""
        disconnect_events(self.layer.text.events, self)
        super().close()
