"""Shape controls."""

import typing as ty
from collections.abc import Iterable

import numpy as np
from napari._qt.widgets.qt_color_swatch import QColorSwatchEdit
from napari.layers.shapes._shapes_constants import Mode
from napari.utils.events import disconnect_events
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QButtonGroup, QCheckBox, QGridLayout

import qtextra.helpers as hp
from qtextra._napari.common.layer_controls.qt_layer_controls_base import QtLayerControls
from qtextra._napari.common.widgets.qt_mode_button import QtModePushButton, QtModeRadioButton

if ty.TYPE_CHECKING:
    from napari.layers import Shapes


class QtShapesControls(QtLayerControls):
    """Qt view and controls for the qtextra Shapes layer."""

    layer: "Shapes"

    def __init__(self, layer: "Shapes"):
        super().__init__(layer)
        self.layer.events.mode.connect(self._on_mode_change)
        self.layer.events.edge_width.connect(self._on_edge_width_change)
        self.layer.events.current_edge_color.connect(self._on_current_edge_color_change)
        self.layer.events.current_face_color.connect(self._on_current_face_color_change)
        self.layer.events.editable.connect(self._on_editable_or_visible_change)
        self.layer.text.events.visible.connect(self._on_text_visibility_change)

        sld = hp.make_slider_with_text(self, 0, 40, step_size=1, tooltip="Edge width of currently selected shapes.")
        sld.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        value = self.layer.current_edge_width
        if isinstance(value, Iterable):
            if isinstance(value, list):
                value = np.asarray(value)
            value = value.mean()
        sld.setValue(int(value))
        sld.valueChanged.connect(self.on_change_current_edge_width)
        self.current_width_slider = sld

        self.select_button = QtModeRadioButton(layer, "select", Mode.SELECT, tooltip="Select shapes (S)")
        self.direct_button = QtModeRadioButton(
            layer,
            "vertex_select",
            Mode.DIRECT,
            tooltip="Select vertices (D)",
        )
        self.panzoom_button = QtModeRadioButton(
            layer,
            "pan_zoom",
            Mode.PAN_ZOOM,
            tooltip="Pan/zoom (Space)",
            checked=True,
        )
        self.line_button = QtModeRadioButton(
            layer,
            "line",
            Mode.ADD_LINE,
            tooltip="Add line (L)",
        )
        self.path_button = QtModeRadioButton(
            layer,
            "path",
            Mode.ADD_PATH,
            tooltip="Add path (A)",
        )
        self.rectangle_button = QtModeRadioButton(
            layer,
            "rectangle",
            Mode.ADD_RECTANGLE,
            tooltip="Add rectangles (R)",
        )
        self.ellipse_button = QtModeRadioButton(
            layer,
            "ellipse",
            Mode.ADD_ELLIPSE,
            tooltip="Add ellipses (E)",
        )
        self.polygon_button = QtModeRadioButton(
            layer,
            "polygon",
            Mode.ADD_POLYGON,
            tooltip="Add polygons (P)",
        )
        self.lasso_button = QtModeRadioButton(
            layer,
            "lasso",
            Mode.ADD_POLYGON_LASSO,
            tooltip="Add polygons (P)",
        )
        self.vertex_insert_button = QtModeRadioButton(
            layer,
            "vertex_insert",
            Mode.VERTEX_INSERT,
            tooltip="Insert vertex (I)",
        )
        self.vertex_remove_button = QtModeRadioButton(
            layer,
            "vertex_remove",
            Mode.VERTEX_REMOVE,
            tooltip="Remove vertex (X)",
        )
        self.move_front_button = QtModePushButton(
            layer,
            "move_front",
            func=self.layer.move_to_front,
            tooltip="Move to front",
        )
        self.move_back_button = QtModePushButton(
            layer,
            "move_back",
            func=self.layer.move_to_back,
            tooltip="Move to back",
        )
        self.delete_button = QtModePushButton(
            layer,
            "delete_shape",
            func=self.layer.remove_selected,
            tooltip="Delete selected shapes (Backspace})",
        )
        self.delete_button.clicked.connect(self.layer.remove_selected)

        self.button_group = QButtonGroup(self)
        self.button_group.addButton(self.select_button)
        self.button_group.addButton(self.direct_button)
        self.button_group.addButton(self.panzoom_button)
        self.button_group.addButton(self.line_button)
        self.button_group.addButton(self.path_button)
        self.button_group.addButton(self.rectangle_button)
        self.button_group.addButton(self.ellipse_button)
        self.button_group.addButton(self.polygon_button)
        self.button_group.addButton(self.lasso_button)
        self.button_group.addButton(self.vertex_insert_button)
        self.button_group.addButton(self.vertex_remove_button)

        button_grid = QGridLayout()
        # row 0
        button_grid.addWidget(self.move_back_button, 0, 0)
        button_grid.addWidget(self.vertex_remove_button, 0, 1)
        button_grid.addWidget(self.vertex_insert_button, 0, 2)
        button_grid.addWidget(self.direct_button, 0, 3)
        button_grid.addWidget(self.select_button, 0, 4)
        button_grid.addWidget(self.panzoom_button, 0, 5)
        button_grid.addWidget(self.delete_button, 0, 6)
        # row 1
        button_grid.addWidget(self.move_front_button, 1, 0)
        button_grid.addWidget(self.line_button, 1, 1)
        button_grid.addWidget(self.path_button, 1, 2)
        button_grid.addWidget(self.ellipse_button, 1, 3)
        button_grid.addWidget(self.rectangle_button, 1, 4)
        button_grid.addWidget(self.polygon_button, 1, 5)
        button_grid.addWidget(self.lasso_button, 1, 6)
        button_grid.setContentsMargins(5, 0, 0, 5)
        button_grid.setColumnStretch(0, 1)
        button_grid.setSpacing(4)

        self.face_color_swatch = QColorSwatchEdit(
            initial_color=self.layer.current_face_color,
            tooltip="click to set current face color",
        )
        self._on_current_face_color_change()
        self.face_color_swatch.color_changed.connect(self.on_change_face_color)

        self.edge_color_swatch = QColorSwatchEdit(
            initial_color=self.layer.current_edge_color,
            tooltip="click to set current edge color",
        )
        self._on_current_edge_color_change()
        self.edge_color_swatch.color_changed.connect(self.on_change_edge_color)

        text_disp_cb = QCheckBox()
        text_disp_cb.setToolTip("Toggle text visibility")
        text_disp_cb.setChecked(self.layer.text.visible)
        text_disp_cb.stateChanged.connect(self.change_text_visibility)
        self.text_display_checkbox = text_disp_cb

        # layout created in QtLayerControls
        self.layout().addRow(button_grid)
        self.layout().addRow(self.opacityLabel, self.opacitySlider)
        self.layout().addRow(hp.make_label(self, "Edge width"), self.current_width_slider)
        self.layout().addRow(hp.make_label(self, "Blending"), self.blendComboBox)
        self.layout().addRow(hp.make_label(self, "Face color"), self.face_color_swatch)
        self.layout().addRow(hp.make_label(self, "Edge color"), self.edge_color_swatch)
        self.layout().addRow(hp.make_label(self, "Display text"), self.text_display_checkbox)
        self.layout().addRow(hp.make_label(self, "Editable"), self.editable_checkbox)
        self._on_editable_or_visible_change()

    def set_layer(self, layer: "Shapes") -> None:
        """Set new layer for this container."""
        if layer == self.layer:
            return
        disconnect_events(self.layer.events, self)

        self.layer = layer
        # update values
        self._on_opacity_change()
        # self._on_mode_change()
        self._on_current_edge_color_change()
        self._on_current_face_color_change()
        self._on_edge_width_change()
        self._on_text_visibility_change()
        self._on_editable_or_visible_change()
        for button in self.button_group.buttons():
            button.set_layer(layer)
        for button in [self.move_front_button, self.move_back_button, self.move_front_button, self.delete_button]:
            button.set_layer(layer)

        # connect new events
        self.layer.events.blending.connect(self._on_blending_change)
        self.layer.events.opacity.connect(self._on_opacity_change)
        self.layer.events.mode.connect(self._on_mode_change)
        self.layer.events.edge_width.connect(self._on_edge_width_change)
        self.layer.events.current_edge_color.connect(self._on_current_edge_color_change)
        self.layer.events.current_face_color.connect(self._on_current_face_color_change)
        self.layer.events.editable.connect(self._on_editable_or_visible_change)
        self.layer.text.events.visible.connect(self._on_text_visibility_change)

    def _on_mode_change(self, event):
        """Update ticks in checkbox widgets when shapes layer mode changed."""
        mode_buttons = {
            Mode.SELECT: self.select_button,
            Mode.DIRECT: self.direct_button,
            Mode.PAN_ZOOM: self.panzoom_button,
            Mode.ADD_RECTANGLE: self.rectangle_button,
            Mode.ADD_LINE: self.line_button,
            Mode.ADD_PATH: self.path_button,
            Mode.ADD_ELLIPSE: self.ellipse_button,
            Mode.ADD_POLYGON: self.polygon_button,
            Mode.ADD_POLYGON_LASSO: self.lasso_button,
            Mode.VERTEX_INSERT: self.vertex_insert_button,
            Mode.VERTEX_REMOVE: self.vertex_remove_button,
        }

        if event.mode in mode_buttons:
            mode_buttons[event.mode].setChecked(True)
        else:
            raise ValueError(f"Mode '{event.mode}'not recognized")

    def on_change_face_color(self, color: np.ndarray) -> None:
        """Change face color of shapes."""
        with self.layer.events.current_face_color.blocker():
            self.layer.current_face_color = color

    def on_change_edge_color(self, color: np.ndarray) -> None:
        """Change edge color of shapes."""
        with self.layer.events.current_edge_color.blocker():
            self.layer.current_edge_color = color

    def on_change_current_edge_width(self, value: float) -> None:
        """Change edge line width of shapes on the layer model."""
        self.layer.current_edge_width = float(value)

    def change_text_visibility(self, state):
        """Toggle the visibility of the text."""
        self.layer.text.visible = Qt.CheckState(state) == Qt.CheckState.Checked

    def _on_text_visibility_change(self, event=None):
        """Receive layer model text visibility change event and update checkbox."""
        with self.layer.text.events.visible.blocker():
            self.text_display_checkbox.setChecked(self.layer.text.visible)

    def _on_edge_width_change(self, _event=None):
        """Receive layer model edge line width change event and update slider."""
        with self.layer.events.edge_width.blocker():
            value = self.layer.current_edge_width
            value = np.clip(int(value), 0, 40)
            self.current_width_slider.setValue(value)

    def _on_current_edge_color_change(self, _event=None) -> None:
        """Receive layer model edge color change event and update color swatch."""
        with hp.qt_signals_blocked(self.edge_color_swatch):
            self.edge_color_swatch.setColor(self.layer.current_edge_color)

    def _on_current_face_color_change(self, _event=None) -> None:
        """Receive layer model face color change event and update color swatch."""
        with hp.qt_signals_blocked(self.face_color_swatch):
            self.face_color_swatch.setColor(self.layer.current_face_color)

    def _on_ndisplay_changed(self):
        self.layer.editable = self.ndisplay == 2

    def _on_editable_or_visible_change(self, event=None):
        """Receive layer model editable change event & enable/disable buttons."""
        hp.enable_with_opacity(
            self,
            [
                self.select_button,
                self.direct_button,
                self.line_button,
                self.path_button,
                self.rectangle_button,
                self.ellipse_button,
                self.polygon_button,
                self.lasso_button,
                self.vertex_remove_button,
                self.vertex_insert_button,
                self.delete_button,
                self.move_back_button,
                self.move_front_button,
                self.opacitySlider,
                self.blendComboBox,
                self.face_color_swatch,
                self.edge_color_swatch,
                self.text_display_checkbox,
                self.current_width_slider,
            ],
            self.layer.editable and self.layer.visible,
        )
        super()._on_editable_or_visible_change(event)

    def close(self):
        """Disconnect events when widget is closing."""
        disconnect_events(self.layer.text.events, self)
        super().close()
