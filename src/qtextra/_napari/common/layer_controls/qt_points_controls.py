"""Points controls."""
import numpy as np
from napari.layers.points._points_constants import Mode
from napari.utils.events import disconnect_events
from qtpy.QtCore import Qt, Slot
from qtpy.QtWidgets import QButtonGroup, QHBoxLayout

import qtextra.helpers as hp
from qtextra._napari.common.layer_controls.qt_layer_controls_base import QtLayerControls
from qtextra._napari.common.layers.points._points_constants import SYMBOL_TRANSLATION
from qtextra.widgets.qt_color_button import QtColorSwatch
from qtextra.widgets.qt_mode_radio_button import QtModePushButton, QtModeRadioButton


class QtPointsControls(QtLayerControls):
    """Qt view and controls for the napari Points layer.

    Parameters
    ----------
    layer : napari.layers.Points
        An instance of a napari Points layer.

    Attributes
    ----------
    addition_button : qtpy.QtWidgets.QtModeRadioButton
        Button to add points to layer.
    button_group : qtpy.QtWidgets.QButtonGroup
        Button group of points layer modes (ADD, PAN_ZOOM, SELECT).
    delete_button : qtpy.QtWidgets.QtModePushButton
        Button to delete points from layer.
    edge_color_swatch : qtpy.QtWidgets.QFrame
        Color swatch showing shapes edge display color.
    face_color_swatch : qtpy.QtWidgets.QFrame
        Color swatch showing shapes face display color.
    layout : qtpy.QtWidgets.QFormLayout
        Layout of Qt widget controls for the layer.
    layer : napari.layers.Points
        An instance of a napari Points layer.
    n_dim_checkbox : qtpy.QtWidgets.QCheckBox
        Checkbox to indicate whether layer is n-dimensional.
    panzoom_button : qtpy.QtWidgets.QtModeRadioButton
        Button for pan/zoom mode.
    select_button : qtpy.QtWidgets.QtModeRadioButton
        Button to select points from layer.
    size_slider : qtpy.QtWidgets.QSlider
        Slider controlling size of points.
    symbol_combobox : qtpy.QtWidgets.QComboBox
        Drop down list of symbol options for points markers.

    Raises
    ------
    ValueError
        Raise error if points mode is not recognized.
        Points mode must be one of: ADD, PAN_ZOOM, or SELECT.
    """

    def __init__(self, layer):
        super().__init__(layer)

        self.layer.events.mode.connect(self._on_mode_change)
        self.layer.events.n_dimensional.connect(self._on_n_dimensional_change)
        self.layer.events.symbol.connect(self._on_symbol_change)
        self.layer.events.size.connect(self._on_size_change)
        self.layer.events.current_edge_color.connect(self._on_current_edge_color_change)
        self.layer._edge.events.current_color.connect(self._on_current_edge_color_change)
        self.layer.events.current_face_color.connect(self._on_current_face_color_change)
        self.layer._face.events.current_color.connect(self._on_current_face_color_change)
        self.layer.events.editable.connect(self._on_editable_change)
        self.layer.text.events.visible.connect(self._on_text_visibility_change)

        self.size_slider = hp.make_int_spin_box(self, 1, tooltip="Scatter point size")
        # self.size_slider.setFocusPolicy(Qt.NoFocus)
        self.size_slider.setValue(int(self.layer.current_size))
        self.size_slider.valueChanged.connect(self.on_change_size)

        self.face_color_swatch = QtColorSwatch(
            initial_color=self.layer.current_face_color,
            tooltip="Click to set current face color",
        )
        self.edge_color_swatch = QtColorSwatch(
            initial_color=self.layer.current_edge_color,
            tooltip="Click to set current edge color",
        )
        self.face_color_swatch.evt_color_changed.connect(self.on_change_face_color)
        self.edge_color_swatch.evt_color_changed.connect(self.on_change_edge_color)

        self.symbol_combobox = hp.make_combobox(self, tooltip="Next marker symbol")
        hp.set_combobox_data(self.symbol_combobox, SYMBOL_TRANSLATION, self.layer.symbol)
        self.symbol_combobox.currentTextChanged.connect(self.on_change_symbol)

        self.n_dim_checkbox = hp.make_checkbox(self, tooltip="N-dimensional points")
        self.n_dim_checkbox.setChecked(self.layer.n_dimensional)
        self.n_dim_checkbox.stateChanged.connect(self.on_change_ndim)

        self.select_button = QtModeRadioButton(
            layer,
            "select_points",
            Mode.SELECT,
            tooltip="Select points (S)",
        )
        self.addition_button = QtModeRadioButton(layer, "add_points", Mode.ADD, tooltip="Add points (P)")
        self.panzoom_button = QtModeRadioButton(
            layer,
            "pan_zoom",
            Mode.PAN_ZOOM,
            tooltip="Pan/zoom (Z)",
            checked=True,
        )
        self.delete_button = QtModePushButton(
            layer,
            "delete_shape",
            slot=self.layer.remove_selected,
            tooltip="Delete selected points (backspace)",
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
        self.layout.addRow(hp.make_label(self, "Opacity"), self.opacity_slider)
        self.layout.addRow(hp.make_label(self, "Points size"), self.size_slider)
        self.layout.addRow(hp.make_label(self, "Blending"), self.blending_combobox)
        self.layout.addRow(hp.make_label(self, "Symbol"), self.symbol_combobox)
        self.layout.addRow(hp.make_label(self, "Face color"), self.face_color_swatch)
        self.layout.addRow(hp.make_label(self, "Edge color"), self.edge_color_swatch)
        self.layout.addRow(hp.make_label(self, "Display text"), self.text_display_checkbox)
        self.layout.addRow(hp.make_label(self, "N-dim"), self.n_dim_checkbox)
        self.layout.addRow(hp.make_label(self, "Editable"), self.editable_checkbox)
        self.layout.addRow(button_row)
        self._on_editable_change()

    def _on_mode_change(self, event):
        """Update ticks in checkbox widgets when points layer mode is changed.

        Available modes for points layer are:
        * ADD
        * SELECT
        * PAN_ZOOM

        Parameters
        ----------
        event : napari.utils.event.Event
            The napari event that triggered this method.

        Raises
        ------
        ValueError
            Raise error if event.mode is not ADD, PAN_ZOOM, or SELECT.
        """
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
        """Change marker symbol of the points on the layer model.

        Parameters
        ----------
        text : int
            Index of current marker symbol of points, eg: '+', '.', etc.
        """
        self.layer.symbol = self.symbol_combobox.currentData()

    def _on_symbol_change(self, event):
        """Receive marker symbol change event and update the dropdown menu.

        Parameters
        ----------
        event : napari.utils.event.Event
            The napari event that triggered this method.
        """
        with self.layer.events.symbol.blocker():
            hp.set_combobox_current_index(self.symbol_combobox, self.layer.symbol)

    def on_change_size(self, value):
        """Change size of points on the layer model.

        Parameters
        ----------
        value : float
            Size of points.
        """
        self.layer.current_size = value

    def _on_size_change(self, event=None):
        """Receive layer model size change event and update point size slider.

        Parameters
        ----------
        event : napari.utils.event.Event, optional
            The napari event that triggered this method.
        """
        with self.layer.events.size.blocker():
            self.size_slider.setValue(int(self.layer.current_size))

    def on_change_ndim(self, state):
        """Toggle n-dimensional state of label layer.

        Parameters
        ----------
        state : QCheckBox
            Checkbox indicating if label layer is n-dimensional.
        """
        self.layer.n_dimensional = state == Qt.Checked

    def _on_n_dimensional_change(self, event):
        """Receive layer model n-dimensional change event and update checkbox.

        Parameters
        ----------
        event : napari.utils.event.Event
            The napari event that triggered this method.
        """
        with self.layer.events.n_dimensional.blocker():
            self.n_dim_checkbox.setChecked(self.layer.n_dimensional)

    def on_change_text_visibility(self, state):
        """Toggle the visibiltiy of the text.

        Parameters
        ----------
        state : QCheckBox
            Checkbox indicating if text is visible.
        """
        self.layer.text.visible = state == Qt.Checked

    def _on_text_visibility_change(self, event):
        """Receive layer model text visibility change change event and update checkbox.

        Parameters
        ----------
        event : qtpy.QtCore.QEvent
            Event from the Qt context.
        """
        with self.layer.text.events.visible.blocker():
            self.text_display_checkbox.setChecked(self.layer.text.visible)

    @Slot(np.ndarray)
    def on_change_face_color(self, color: np.ndarray):
        """Update face color of layer model from color picker user input."""
        with self.layer.events.current_face_color.blocker():
            self.layer.current_face_color = color

    def _on_current_face_color_change(self, event=None):
        """Receive layer.current_face_color() change event and update view."""
        with hp.qt_signals_blocked(self.face_color_swatch):
            self.face_color_swatch.set_color(self.layer.current_face_color)

    @Slot(np.ndarray)
    def on_change_edge_color(self, color: np.ndarray):
        """Update edge color of layer model from color picker user input."""
        with self.layer.events.current_edge_color.blocker():
            self.layer.current_edge_color = color

    def _on_current_edge_color_change(self, event=None):
        """Receive layer.current_edge_color() change event and update view."""
        with hp.qt_signals_blocked(self.edge_color_swatch):
            self.edge_color_swatch.set_color(self.layer.current_edge_color)

    def _on_editable_change(self, event=None):
        """Receive layer model editable change event & enable/disable buttons.

        Parameters
        ----------
        event : napari.utils.event.Event, optional
            The napari event that triggered this method, by default None.
        """
        hp.disable_with_opacity(
            self,
            [self.select_button, self.addition_button, self.delete_button],
            not self.layer.editable,
        )
        super()._on_editable_change(event)

    def close(self):
        """Disconnect events when widget is closing."""
        disconnect_events(self.layer.text.events, self)
        super().close()
