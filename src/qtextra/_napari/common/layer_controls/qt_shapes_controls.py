"""Shape controls."""
import typing as ty
from collections.abc import Iterable

import numpy as np
from napari.layers.shapes._shapes_constants import Mode
from napari.utils.events import disconnect_events
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QButtonGroup, QCheckBox, QGridLayout

import qtextra.helpers as hp
from qtextra._napari.common.layer_controls.qt_layer_controls_base import QtLayerControls
from qtextra.widgets.qt_color_button import QtColorSwatch
from qtextra.widgets.qt_mode_radio_button import QtModePushButton, QtModeRadioButton

if ty.TYPE_CHECKING:
    from napari.layers import Shapes


class QtShapesControls(QtLayerControls):
    """Qt view and controls for the qtextra Shapes layer.

    Attributes
    ----------
    button_group : qtpy.QtWidgets.QButtonGroup
        Button group for shapes layer modes
        (SELECT, DIRECT, PAN_ZOOM, ADD_RECTANGLE, ADD_ELLIPSE, ADD_LINE,
        ADD_PATH, ADD_POLYGON, VERTEX_INSERT, VERTEX_REMOVE).
    delete_button : qtpy.QtWidgets.QtModePushButton
        Button to delete selected shapes
    direct_button : qtpy.QtWidgets.QtModeRadioButton
        Button to select individual vertices in shapes.
    edgeColorSwatch : qtpy.QtWidgets.QFrame
        Thumbnail display of points edge color.
    edgeComboBox : qtpy.QtWidgets.QComboBox
        Drop down list allowing user to set edge color of points.
    ellipse_button : qtpy.QtWidgets.QtModeRadioButton
        Button to add ellipses to shapes layer.
    faceColorSwatch : qtpy.QtWidgets.QFrame
        Thumbnail display of points face color.
    faceComboBox : qtpy.QtWidgets.QComboBox
        Drop down list allowing user to set face color of points.
    grid_layout : qtpy.QtWidgets.QGridLayout
        Layout of Qt widget controls for the layer.
    layer : napari.layers.Shapes
        An instance of a napari Shapes layer.
    line_button : qtpy.QtWidgets.QtModeRadioButton
        Button to add lines to shapes layer.
    move_back_button : qtpy.QtWidgets.QtModePushButton
        Button to move selected shape(s) to the back.
    move_front_button : qtpy.QtWidgets.QtModePushButton
        Button to move shape(s) to the front.
    panzoom_button : qtpy.QtWidgets.QtModeRadioButton
        Button to pan/zoom shapes layer.
    path_button : qtpy.QtWidgets.QtModeRadioButton
        Button to add paths to shapes layer.
    polygon_button : qtpy.QtWidgets.QtModeRadioButton
        Button to add polygons to shapes layer.
    rectangle_button : qtpy.QtWidgets.QtModeRadioButton
        Button to add rectangles to shapes layer.
    select_button : qtpy.QtWidgets.QtModeRadioButton
        Button to select shapes.
    vertex_insert_button : qtpy.QtWidgets.QtModeRadioButton
        Button to insert vertex into shape.
    vertex_remove_button : qtpy.QtWidgets.QtModeRadioButton
        Button to remove vertex from shapes.
    current_width_slider : qtpy.QtWidgets.QSlider
        Slider controlling line edge width of shapes.

    Raises
    ------
    ValueError
        Raise error if shapes mode is not recognized.
    """

    def __init__(self, layer: "Shapes"):
        super().__init__(layer)
        self.layer.events.mode.connect(self._on_mode_change)
        self.layer.events.edge_width.connect(self._on_edge_width_change)
        self.layer.events.current_edge_color.connect(self._on_current_edge_color_change)
        self.layer.events.current_face_color.connect(self._on_current_face_color_change)
        self.layer.events.editable.connect(self._on_editable_change)
        self.layer.text.events.visible.connect(self._on_text_visibility_change)

        sld = hp.make_int_spin_box(self, maximum=40, tooltip="Edge width of currently selected shapes.")
        # sld.setFocusPolicy(Qt.NoFocus)
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
            "direct",
            Mode.DIRECT,
            tooltip="Select vertices (D)",
        )
        self.panzoom_button = QtModeRadioButton(
            layer,
            "zoom",
            Mode.PAN_ZOOM,
            tooltip="Pan/zoom (Space)",
            checked=True,
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
        self.line_button = QtModeRadioButton(layer, "line", Mode.ADD_LINE, tooltip="Add lines (L)")
        self.path_button = QtModeRadioButton(layer, "path", Mode.ADD_PATH, tooltip="Add paths (T)")
        self.polygon_button = QtModeRadioButton(
            layer,
            "polygon",
            Mode.ADD_POLYGON,
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
            slot=self.layer.move_to_front,
            tooltip="Move to front",
        )
        self.move_back_button = QtModePushButton(
            layer,
            "move_back",
            slot=self.layer.move_to_back,
            tooltip="Move to back",
        )
        self.delete_button = QtModePushButton(
            layer,
            "delete_shape",
            slot=self.layer.remove_selected,
            tooltip="Delete selected shapes (Backspace})",
        )
        self.delete_button.clicked.connect(self.layer.remove_selected)

        self.button_group = QButtonGroup(self)
        self.button_group.addButton(self.select_button)
        self.button_group.addButton(self.direct_button)
        self.button_group.addButton(self.panzoom_button)
        self.button_group.addButton(self.rectangle_button)
        self.button_group.addButton(self.ellipse_button)
        self.button_group.addButton(self.line_button)
        self.button_group.addButton(self.path_button)
        self.button_group.addButton(self.polygon_button)
        self.button_group.addButton(self.vertex_insert_button)
        self.button_group.addButton(self.vertex_remove_button)

        button_grid = QGridLayout()
        button_grid.addWidget(self.vertex_remove_button, 0, 1)
        button_grid.addWidget(self.vertex_insert_button, 0, 2)
        button_grid.addWidget(self.direct_button, 0, 3)
        button_grid.addWidget(self.select_button, 0, 4)
        button_grid.addWidget(self.panzoom_button, 0, 5)
        button_grid.addWidget(self.delete_button, 0, 6)
        button_grid.addWidget(self.move_back_button, 1, 0)
        button_grid.addWidget(self.move_front_button, 1, 1)
        button_grid.addWidget(self.line_button, 1, 2)
        button_grid.addWidget(self.path_button, 1, 3)
        button_grid.addWidget(self.ellipse_button, 1, 4)
        button_grid.addWidget(self.rectangle_button, 1, 5)
        button_grid.addWidget(self.polygon_button, 1, 6)
        button_grid.setContentsMargins(5, 0, 0, 5)
        button_grid.setColumnStretch(0, 1)
        button_grid.setSpacing(4)

        self.face_color_swatch = QtColorSwatch(
            initial_color=self.layer.current_face_color,
            tooltip="click to set current face color",
        )
        self._on_current_face_color_change()
        self.edge_color_swatch = QtColorSwatch(
            initial_color=self.layer.current_edge_color,
            tooltip="click to set current edge color",
        )
        self._on_current_edge_color_change()
        self.face_color_swatch.evt_color_changed.connect(self.on_change_face_color)
        self.edge_color_swatch.evt_color_changed.connect(self.on_change_edge_color)

        text_disp_cb = QCheckBox()
        text_disp_cb.setToolTip("toggle text visibility")
        text_disp_cb.setChecked(self.layer.text.visible)
        text_disp_cb.stateChanged.connect(self.change_text_visibility)
        self.text_display_checkbox = text_disp_cb

        # layout created in QtLayerControls
        self.layout.addRow(hp.make_label(self, "Opacity"), self.opacity_slider)
        self.layout.addRow(hp.make_label(self, "Edge width"), self.current_width_slider)
        self.layout.addRow(hp.make_label(self, "Blending"), self.blending_combobox)
        self.layout.addRow(hp.make_label(self, "Face color"), self.face_color_swatch)
        self.layout.addRow(hp.make_label(self, "Edge color"), self.edge_color_swatch)
        self.layout.addRow(hp.make_label(self, "Display text"), self.text_display_checkbox)
        self.layout.addRow(hp.make_label(self, "Editable"), self.editable_checkbox)
        self.layout.addRow(button_grid)
        self._on_editable_change()

    def _on_mode_change(self, event):
        """Update ticks in checkbox widgets when shapes layer mode changed.

        Available modes for shapes layer are:
        * SELECT
        * DIRECT
        * PAN_ZOOM
        * ADD_RECTANGLE
        * ADD_ELLIPSE
        * ADD_POLYGON
        * VERTEX_INSERT
        * VERTEX_REMOVE

        Raises
        ------
        ValueError
            Raise error if event.mode is not ADD, PAN_ZOOM, or SELECT.
        """
        mode_buttons = {
            Mode.SELECT: self.select_button,
            Mode.DIRECT: self.direct_button,
            Mode.PAN_ZOOM: self.panzoom_button,
            Mode.ADD_LINE: self.line_button,
            Mode.ADD_PATH: self.path_button,
            Mode.ADD_RECTANGLE: self.rectangle_button,
            Mode.ADD_ELLIPSE: self.ellipse_button,
            Mode.ADD_POLYGON: self.polygon_button,
            Mode.VERTEX_INSERT: self.vertex_insert_button,
            Mode.VERTEX_REMOVE: self.vertex_remove_button,
        }

        if event.mode in mode_buttons:
            mode_buttons[event.mode].setChecked(True)
        else:
            raise ValueError(f"Mode '{event.mode}'not recognized")

    def on_change_face_color(self, color: np.ndarray):
        """Change face color of shapes.

        Parameters
        ----------
        color : np.ndarray
            Face color for shapes, color name or hex string.
            Eg: 'white', 'red', 'blue', '#00ff00', etc.
        """
        with self.layer.events.current_face_color.blocker():
            self.layer.current_face_color = color

    def on_change_edge_color(self, color: np.ndarray):
        """Change edge color of shapes.

        Parameters
        ----------
        color : np.ndarray
            Edge color for shapes, color name or hex string.
            Eg: 'white', 'red', 'blue', '#00ff00', etc.
        """
        with self.layer.events.current_edge_color.blocker():
            self.layer.current_edge_color = color

    def on_change_current_edge_width(self, value):
        """Change edge line width of shapes on the layer model.

        Parameters
        ----------
        value : float
            Line width of shapes.
        """
        self.layer.current_edge_width = float(value)

    def change_text_visibility(self, state):
        """Toggle the visibility of the text.

        Parameters
        ----------
        state : QCheckBox
            Checkbox indicating if text is visible.
        """
        if state == Qt.Checked:
            self.layer.text.visible = True
        else:
            self.layer.text.visible = False

    def _on_text_visibility_change(self, event):
        """Receive layer model text visibiltiy change change event and update checkbox.

        Parameters
        ----------
        event : qtpy.QtCore.QEvent
            Event from the Qt context.
        """
        with self.layer.text.events.visible.blocker():
            self.text_display_checkbox.setChecked(self.layer.text.visible)

    def _on_edge_width_change(self, event=None):
        """Receive layer model edge line width change event and update slider."""
        with self.layer.events.edge_width.blocker():
            value = self.layer.current_edge_width
            value = np.clip(int(2 * value), 0, 40)
            self.current_width_slider.setValue(value)

    def _on_current_edge_color_change(self, event=None):
        """Receive layer model edge color change event and update color swatch."""
        with hp.qt_signals_blocked(self.edge_color_swatch):
            self.edge_color_swatch.set_color(self.layer.current_edge_color)

    def _on_current_face_color_change(self, event=None):
        """Receive layer model face color change event and update color swatch."""
        with hp.qt_signals_blocked(self.face_color_swatch):
            self.face_color_swatch.set_color(self.layer.current_face_color)

    def _on_editable_change(self, event=None):
        """Receive layer model editable change event & enable/disable buttons."""
        hp.disable_with_opacity(
            self,
            [
                self.select_button,
                self.direct_button,
                self.rectangle_button,
                self.ellipse_button,
                self.polygon_button,
                self.path_button,
                self.line_button,
                self.vertex_remove_button,
                self.vertex_insert_button,
                self.delete_button,
                self.move_back_button,
                self.move_front_button,
            ],
            not self.layer.editable,
        )
        super()._on_editable_change(event)

    def close(self):
        """Disconnect events when widget is closing."""
        disconnect_events(self.layer.text.events, self)
        super().close()
