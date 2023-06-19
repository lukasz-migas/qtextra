"""Label controls."""
import numpy as np
from napari.layers.labels._labels_constants import Mode
from napari.utils.events import disconnect_events
from qtpy.QtCore import Qt
from qtpy.QtGui import QColor, QPainter
from qtpy.QtWidgets import QButtonGroup, QGridLayout, QHBoxLayout, QSpinBox, QWidget

import qtextra.helpers as hp
from qtextra._napari.common.layer_controls.qt_layer_controls_base import QtLayerControls
from qtextra._napari.image.layers.labels._labels_constants import LABEL_COLOR_MODE_TRANSLATIONS
from qtextra.widgets.qt_mode_radio_button import QtModePushButton, QtModeRadioButton


class QtLabelsControls(QtLayerControls):
    """Qt view and controls for the napari Labels layer.

    Parameters
    ----------
    layer : napari.layers.Labels
        An instance of a napari Labels layer.

    Attributes
    ----------
    button_group : qtpy.QtWidgets.QButtonGroup
        Button group of labels layer modes: PAN_ZOOM, PICKER, PAINT, ERASE, or
        FILL.
    shuffle_button : qtpy.QtWidgets.QPushButton
        Button to update colormap of label layer.
    contiguous_checkbox : qtpy.QtWidgets.QCheckBox
        Checkbox to control if label layer is contiguous.
    fill_button : qtpy.QtWidgets.QtModeRadioButton
        Button to select FILL mode on Labels layer.
    layout : qtpy.QtWidgets.QGridLayout
        Layout of Qt widget controls for the layer.
    layer : napari.layers.Labels
        An instance of a napari Labels layer.
    ndimCheckBox : qtpy.QtWidgets.QCheckBox
        Checkbox to control if label layer is n-dimensional.
    paint_button : qtpy.QtWidgets.QtModeRadioButton
        Button to select PAINT mode on Labels layer.
    panzoom_button : qtpy.QtWidgets.QtModeRadioButton
        Button to select PAN_ZOOM mode on Labels layer.
    pick_button : qtpy.QtWidgets.QtModeRadioButton
        Button to select PICKER mode on Labels layer.
    erase_button : qtpy.QtWidgets.QtModeRadioButton
        Button to select ERASE mode on Labels layer.
    selection_spin_box : qtpy.QtWidgets.QSpinBox
        Widget to select a specific label by its index.

    Raises
    ------
    ValueError
        Raise error if label mode is not PAN_ZOOM, PICKER, PAINT, ERASE, or
        FILL.
    """

    def __init__(self, layer):
        super().__init__(layer)
        self.layer.events.mode.connect(self._on_mode_change)
        self.layer.events.selected_label.connect(self._on_selected_label_change)
        self.layer.events.brush_size.connect(self._on_brush_size_change)
        self.layer.events.contiguous.connect(self._on_contiguous_change)
        self.layer.events.n_edit_dimensions.connect(self._on_n_dimensional_change)
        self.layer.events.contour.connect(self._on_contour_change)
        self.layer.events.editable.connect(self._on_editable_change)
        self.layer.events.preserve_labels.connect(self._on_preserve_labels_change)
        self.layer.events.color_mode.connect(self._on_color_mode_change)

        # selection spinbox
        self.selection_spin_box = hp.make_int_spin_box(self, maximum=1024)
        self.selection_spin_box.setKeyboardTracking(False)
        self.selection_spin_box.setSingleStep(1)
        self.selection_spin_box.valueChanged.connect(self.change_selection)
        self.selection_spin_box.setAlignment(Qt.AlignCenter)
        self._on_selected_label_change()

        sld = hp.make_int_spin_box(self, minimum=1, maximum=40)
        sld.setFocusPolicy(Qt.NoFocus)
        sld.valueChanged.connect(self.changeSize)
        self.brush_size_slider = sld
        self._on_brush_size_change()

        contiguous_checkbox = hp.make_checkbox(self, "", tooltip="Contiguous editing")
        contiguous_checkbox.stateChanged.connect(self.change_contig)
        self.contiguous_checkbox = contiguous_checkbox
        self._on_contiguous_change()

        contour_sb = QSpinBox()
        contour_sb.setToolTip("Display contours of labels")
        contour_sb.valueChanged.connect(self.change_contour)
        self.contour_spin_box = contour_sb
        self.contour_spin_box.setKeyboardTracking(False)
        self.contour_spin_box.setSingleStep(1)
        self.contour_spin_box.setMinimum(0)
        self.contour_spin_box.setMaximum(2147483647)
        self.contour_spin_box.setAlignment(Qt.AlignCenter)
        self._on_contour_change()

        preserve_labels_cb = hp.make_checkbox(self, "", tooltip="Preserve existing labels while painting")
        preserve_labels_cb.stateChanged.connect(self.change_preserve_labels)
        self.preserve_labels_checkbox = preserve_labels_cb
        self._on_preserve_labels_change()

        selected_color_checkbox = hp.make_checkbox(self, "", tooltip="Display only select label")
        selected_color_checkbox.stateChanged.connect(self.toggle_selected_mode)
        self.selected_color_checkbox = selected_color_checkbox

        # shuffle colormap button
        self.shuffle_button = QtModePushButton(
            layer,
            "shuffle",
            slot=self.on_change_colors,
            tooltip="shuffle colors",
        )

        self.panzoom_button = QtModeRadioButton(
            layer,
            "zoom",
            Mode.PAN_ZOOM,
            tooltip="Pan/zoom mode (Space)",
            checked=True,
        )
        self.pick_button = QtModeRadioButton(layer, "picker", Mode.PICK, tooltip="Pick mode (L)")
        self.paint_button = QtModeRadioButton(layer, "paint", Mode.PAINT, tooltip="Paint mode (P)")
        self.fill_button = QtModeRadioButton(
            layer,
            "fill",
            Mode.FILL,
            tooltip="Fill mode (F) \nToggle with CTRL",
        )
        self.erase_button = QtModeRadioButton(
            layer,
            "erase",
            Mode.ERASE,
            tooltip="Erase mode (E) \nToggle with ALT",
        )

        self.button_group = QButtonGroup(self)
        self.button_group.addButton(self.panzoom_button)
        self.button_group.addButton(self.paint_button)
        self.button_group.addButton(self.pick_button)
        self.button_group.addButton(self.fill_button)
        self.button_group.addButton(self.erase_button)

        button_grid = QGridLayout()
        button_grid.addWidget(self.shuffle_button, 0, 0)
        button_grid.addWidget(self.erase_button, 0, 1)
        button_grid.addWidget(self.fill_button, 0, 2)
        button_grid.addWidget(self.paint_button, 0, 3)
        button_grid.addWidget(self.pick_button, 0, 4)
        button_grid.addWidget(self.panzoom_button, 0, 5)
        button_grid.setContentsMargins(5, 0, 10, 5)
        button_grid.setSpacing(4)

        color_mode_comboBox = hp.make_combobox(self)
        hp.set_combobox_data(color_mode_comboBox, LABEL_COLOR_MODE_TRANSLATIONS, self.layer.color_mode)

        color_mode_comboBox.currentTextChanged.connect(self.change_color_mode)
        self.color_mode_combobox = color_mode_comboBox
        self._on_color_mode_change()

        color_layout = QHBoxLayout()
        self.color_box = QtColorBox(layer)
        color_layout.addWidget(self.color_box)
        color_layout.addWidget(self.selection_spin_box)

        # layout created in QtLayerControls
        self.layout.addRow(hp.make_label(self, "Opacity"), self.opacity_slider)
        self.layout.addRow(hp.make_label(self, "Label"), color_layout)
        self.layout.addRow(hp.make_label(self, "Brush size"), self.brush_size_slider)
        self.layout.addRow(hp.make_label(self, "Blending"), self.blending_combobox)
        self.layout.addRow(hp.make_label(self, "Color mode"), self.color_mode_combobox)
        self.layout.addRow(hp.make_label(self, "Contour"), self.contour_spin_box)
        self.layout.addRow(hp.make_label(self, "Contiguous"), self.contiguous_checkbox)
        self.layout.addRow(hp.make_label(self, "Preserve labels"), self.preserve_labels_checkbox)
        self.layout.addRow(hp.make_label(self, "Show selected"), self.selected_color_checkbox)
        self.layout.addRow(hp.make_label(self, "Editable"), self.editable_checkbox)
        self.layout.addRow(button_grid)
        self._on_editable_change()

    def _on_mode_change(self, event):
        """Receive layer model mode change event and update checkbox ticks.

        Parameters
        ----------
        event : napari.utils.event.Event
            The napari event that triggered this method.

        Raises
        ------
        ValueError
            Raise error if event.mode is not PAN_ZOOM, PICK, PAINT, ERASE, or
            FILL
        """
        mode = event.mode
        if mode == Mode.PAN_ZOOM:
            self.panzoom_button.setChecked(True)
        elif mode == Mode.PICK:
            self.pick_button.setChecked(True)
        elif mode == Mode.PAINT:
            self.paint_button.setChecked(True)
        elif mode == Mode.FILL:
            self.fill_button.setChecked(True)
        elif mode == Mode.ERASE:
            self.erase_button.setChecked(True)
        else:
            raise ValueError("Mode not recognized")

    def on_change_colors(self):
        """Change colormap of the label layer."""
        self.layer.new_colormap()

    def change_selection(self, value):
        """Change currently selected label.

        Parameters
        ----------
        value : int
            Index of label to select.
        """
        self.layer.selected_label = value
        self.selection_spin_box.clearFocus()
        self.setFocus()

    def toggle_selected_mode(self, state):
        if state == Qt.Checked:
            self.layer.show_selected_label = True
        else:
            self.layer.show_selected_label = False

    def changeSize(self, value):
        """Change paint brush size.

        Parameters
        ----------
        value : float
            Size of the paint brush.
        """
        self.layer.brush_size = value

    def change_contig(self, state):
        """Toggle contiguous state of label layer.

        Parameters
        ----------
        state : QCheckBox
            Checkbox indicating if labels are contiguous.
        """
        if state == Qt.Checked:
            self.layer.contiguous = True
        else:
            self.layer.contiguous = False

    def change_ndim(self, state):
        """Toggle n-dimensional state of label layer.

        Parameters
        ----------
        state : QCheckBox
            Checkbox indicating if label layer is n-dimensional.
        """
        if state == Qt.Checked:
            self.layer.n_edit_dimensions = True
        else:
            self.layer.n_edit_dimensions = False

    def change_contour(self, value):
        """Change contour thickness.

        Parameters
        ----------
        value : int
            Thickness of contour.
        """
        self.layer.contour = value
        self.contour_spin_box.clearFocus()
        self.setFocus()

    def change_preserve_labels(self, state):
        """Toggle preserve_labels state of label layer.

        Parameters
        ----------
        state : QCheckBox
            Checkbox indicating if overwriting label is enabled.
        """
        if state == Qt.Checked:
            self.layer.preserve_labels = True
        else:
            self.layer.preserve_labels = False

    def change_color_mode(self, new_mode):
        """Change color mode of label layer.

        Parameters
        ----------
        new_mode : str
            AUTO (default) allows color to be set via a hash function with a seed.
            DIRECT allows color of each label to be set directly by a color dictionary.
        """
        self.layer.color_mode = self.color_mode_combobox.currentData()

    def _on_contour_change(self, event=None):
        """Receive layer model contour value change event and update spinbox.

        Parameters
        ----------
        event : napari.utils.event.Event, optional
            The napari event that triggered this method.
        """
        with self.layer.events.contour.blocker():
            value = self.layer.contour
            self.contour_spin_box.setValue(int(value))

    def _on_selected_label_change(self, event=None):
        """Receive layer model label selection change event and update spinbox.

        Parameters
        ----------
        event : napari.utils.event.Event, optional
            The napari event that triggered this method.
        """
        with self.layer.events.selected_label.blocker():
            value = self.layer.selected_label
            self.selection_spin_box.setValue(int(value))

    def _on_brush_size_change(self, event=None):
        """Receive layer model brush size change event and update the slider.

        Parameters
        ----------
        event : napari.utils.event.Event, optional
            The napari event that triggered this method.
        """
        with self.layer.events.brush_size.blocker():
            value = self.layer.brush_size
            value = np.clip(int(value), 1, 40)
            self.brush_size_slider.setValue(value)

    def _on_n_dimensional_change(self, event=None):
        """Receive layer model n-dim mode change event and update the checkbox.

        Parameters
        ----------
        event : napari.utils.event.Event, optional
            The napari event that triggered this method.
        """
        with self.layer.events.n_edit_dimensions.blocker():
            self.ndimCheckBox.setChecked(self.layer.n_edit_dimensions)

    def _on_contiguous_change(self, event=None):
        """Receive layer model contiguous change event and update the checkbox.

        Parameters
        ----------
        event : napari.utils.event.Event, optional
            The napari event that triggered this method.
        """
        with self.layer.events.contiguous.blocker():
            self.contiguous_checkbox.setChecked(self.layer.contiguous)

    def _on_preserve_labels_change(self, event=None):
        """Receive layer model preserve_labels event and update the checkbox.

        Parameters
        ----------
        event : napari.utils.event.Event, optional
            The napari event that triggered this method.
        """
        with self.layer.events.preserve_labels.blocker():
            self.preserve_labels_checkbox.setChecked(self.layer.preserve_labels)

    def _on_color_mode_change(self, event=None):
        """Receive layer model color.

        Parameters
        ----------
        event : napari.utils.event.Event, optional
            The napari event that triggered this method.
        """
        with self.layer.events.color_mode.blocker():
            hp.set_combobox_current_index(self.color_mode_combobox, self.layer.color_mode)

    def _on_editable_change(self, event=None):
        """Receive layer model editable change event & enable/disable buttons.

        Parameters
        ----------
        event : napari.utils.event.Event, optional
            The napari event that triggered this method.
        """
        hp.disable_with_opacity(
            self,
            [
                self.pick_button,
                self.paint_button,
                self.fill_button,
                self.erase_button,
                self.brush_size_slider,
                self.color_mode_combobox,
                self.contour_spin_box,
                self.contiguous_checkbox,
                self.preserve_labels_checkbox,
                self.selected_color_checkbox,
                self.color_box,
                self.blending_combobox,
                self.opacity_slider,
                self.selection_spin_box,
                self.shuffle_button,
            ],
            not self.layer.editable,
        )
        super()._on_editable_change(event)


class QtColorBox(QWidget):
    """A widget that shows a square with the current label color.

    Parameters
    ----------
    layer : napari.layers.Layer
        An instance of a napari layer.
    """

    def __init__(self, layer):
        super().__init__()

        self.layer = layer
        self.layer.events.selected_label.connect(self._on_selected_label_change)
        self.layer.events.opacity.connect(self._on_opacity_change)

        self.setAttribute(Qt.WA_DeleteOnClose)

        self._height = 24
        self.setFixedWidth(self._height)
        self.setFixedHeight(self._height)
        self.setToolTip("Selected label color")

    def _on_selected_label_change(self, event):
        """Receive layer model label selection change event & update colorbox.

        Parameters
        ----------
        event : napari.utils.event.Event
            The napari event that triggered this method.
        """
        self.update()

    def _on_opacity_change(self, event):
        """Receive layer model label selection change event & update colorbox.

        Parameters
        ----------
        event : napari.utils.event.Event
            The napari event that triggered this method.
        """
        self.update()

    def paintEvent(self, event):
        """Paint the colorbox.  If no color, display a checkerboard pattern.

        Parameters
        ----------
        event : qtpy.QtCore.QEvent
            Event from the Qt context.
        """
        painter = QPainter(self)
        if self.layer._selected_color is None:
            for i in range(self._height // 4):
                for j in range(self._height // 4):
                    if (i % 2 == 0 and j % 2 == 0) or (i % 2 == 1 and j % 2 == 1):
                        painter.setPen(QColor(230, 230, 230))
                        painter.setBrush(QColor(230, 230, 230))
                    else:
                        painter.setPen(QColor(25, 25, 25))
                        painter.setBrush(QColor(25, 25, 25))
                    painter.drawRect(i * 4, j * 4, 5, 5)
        else:
            color = np.multiply(self.layer._selected_color, self.layer.opacity)
            color = np.round(255 * color).astype(int)
            painter.setPen(QColor(*list(color)))
            painter.setBrush(QColor(*list(color)))
            painter.drawRect(0, 0, self._height, self._height)

    def close(self):
        """Disconnect events when widget is closing."""
        disconnect_events(self.layer.events, self)
        super().close()
