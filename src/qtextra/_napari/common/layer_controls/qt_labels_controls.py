"""Label controls."""
import typing as ty

import numpy as np
from napari.layers import Labels
from napari.layers.labels._labels_constants import Mode
from napari.utils.events import disconnect_events
from qtpy.QtCore import Qt
from qtpy.QtGui import QColor, QPainter
from qtpy.QtWidgets import QButtonGroup, QHBoxLayout, QSpinBox, QWidget

import qtextra.helpers as hp
from qtextra._napari.common.layer_controls.qt_layer_controls_base import QtLayerControls
from qtextra._napari.common.layers._labels_constants import (
    LABEL_COLOR_MODE_TRANSLATIONS,
    RENDER_MODE_TRANSLATIONS,
)
from qtextra._napari.common.widgets.qt_mode_button import QtModePushButton, QtModeRadioButton


# noinspection PyMissingOrEmptyDocstring
class QtLabelsControls(QtLayerControls):
    """Qt view and controls for the napari Labels layer."""

    layer: Labels

    def __init__(self, layer: Labels):
        super().__init__(layer)
        self.layer.events.mode.connect(self._on_mode_change)
        self.layer.events.rendering.connect(self._on_rendering_change)
        self.layer.events.selected_label.connect(self._on_selected_label_change)
        self.layer.events.brush_size.connect(self._on_brush_size_change)
        self.layer.events.contiguous.connect(self._on_contiguous_change)
        # self.layer.events.n_edit_dimensions.connect(self._on_n_edit_dimensions_change)
        self.layer.events.contour.connect(self._on_contour_change)
        self.layer.events.preserve_labels.connect(self._on_preserve_labels_change)
        self.layer.events.show_selected_label.connect(self._on_show_selected_label_change)
        self.layer.events.color_mode.connect(self._on_color_mode_change)
        self.layer.events.editable.connect(self._on_editable_or_visible_change)
        self.layer.events.visible.connect(self._on_editable_or_visible_change)

        # selection spinbox
        self.selection_spin_box = hp.make_int_spin_box(self, maximum=1024, step_size=1, keyboard_tracking=False)
        self.selection_spin_box.valueChanged.connect(self.on_change_selection)
        self.selection_spin_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._on_selected_label_change()

        sld = hp.make_slider_with_text(self, 1, 40, 1)
        sld.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        sld.valueChanged.connect(self.on_change_brush_size)
        self.brush_size_slider = sld
        self._on_brush_size_change()

        contiguous_checkbox = hp.make_checkbox(self, "", tooltip="Contiguous editing")
        contiguous_checkbox.stateChanged.connect(self.on_change_contiguous)
        self.contiguous_checkbox = contiguous_checkbox
        self._on_contiguous_change()

        contour_sb = QSpinBox()
        contour_sb.setToolTip("Display contours of labels")
        contour_sb.valueChanged.connect(self.on_change_contour)
        self.contour_spin_box = contour_sb
        self.contour_spin_box.setKeyboardTracking(False)
        self.contour_spin_box.setSingleStep(1)
        self.contour_spin_box.setMinimum(0)
        self.contour_spin_box.setMaximum(2147483647)
        self.contour_spin_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._on_contour_change()

        preserve_labels_cb = hp.make_checkbox(self, "", tooltip="Preserve existing labels while painting")
        preserve_labels_cb.stateChanged.connect(self.on_change_preserve_labels)
        self.preserve_labels_checkbox = preserve_labels_cb
        self._on_preserve_labels_change()

        selected_color_checkbox = hp.make_checkbox(self, "", tooltip="Display only select label")
        selected_color_checkbox.stateChanged.connect(self.toggle_selected_mode)
        self.selected_color_checkbox = selected_color_checkbox

        # shuffle colormap button
        self.shuffle_button = QtModePushButton(
            layer,
            "shuffle",
            func=self.on_shuffle_colors,
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

        button_row = QHBoxLayout()
        button_row.addStretch(1)
        button_row.addWidget(self.shuffle_button)
        button_row.addWidget(self.erase_button)
        button_row.addWidget(self.fill_button)
        button_row.addWidget(self.paint_button)
        button_row.addWidget(self.pick_button)
        button_row.addWidget(self.panzoom_button)
        button_row.setContentsMargins(0, 0, 0, 5)
        button_row.setSpacing(4)

        render_combobox = hp.make_combobox(self)
        hp.set_combobox_data(render_combobox, RENDER_MODE_TRANSLATIONS, self.layer.rendering)
        self.renderCombobox = render_combobox
        self.renderLabel = hp.make_label(self, "Rendering")

        color_mode_combo_box = hp.make_combobox(self)
        hp.set_combobox_data(color_mode_combo_box, LABEL_COLOR_MODE_TRANSLATIONS, self.layer.color_mode)
        color_mode_combo_box.currentTextChanged.connect(self.on_change_color_mode)
        self.color_mode_combobox = color_mode_combo_box
        self._on_color_mode_change()

        color_layout = QHBoxLayout()
        self.color_box = QtColorBox(layer)
        color_layout.addWidget(self.color_box)
        color_layout.addWidget(self.selection_spin_box)

        # layout created in QtLayerControls
        self.layout().addRow(button_row)
        self.layout().addRow(self.opacityLabel, self.opacitySlider)
        self.layout().addRow(hp.make_label(self, "Label"), color_layout)
        self.layout().addRow(hp.make_label(self, "Brush size"), self.brush_size_slider)
        self.layout().addRow(hp.make_label(self, "Blending"), self.blendComboBox)
        self.layout().addRow(self.renderLabel, self.renderCombobox)
        self.layout().addRow(hp.make_label(self, "Color mode"), self.color_mode_combobox)
        self.layout().addRow(hp.make_label(self, "Contour"), self.contour_spin_box)
        self.layout().addRow(hp.make_label(self, "Contiguous"), self.contiguous_checkbox)
        self.layout().addRow(hp.make_label(self, "Preserve labels"), self.preserve_labels_checkbox)
        self.layout().addRow(hp.make_label(self, "Show selected"), self.selected_color_checkbox)
        self.layout().addRow(hp.make_label(self, "Editable"), self.editable_checkbox)
        self._on_ndisplay_changed()

    def _on_mode_change(self, event) -> None:
        """Receive layer model mode change event and update checkbox ticks."""
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

    def on_shuffle_colors(self) -> None:
        """Change colormap of the label layer."""
        self.layer.new_colormap()

    def on_change_selection(self, value):
        """Change the currently selected label."""
        self.layer.selected_label = value
        self.selection_spin_box.clearFocus()
        self.setFocus()

    def toggle_selected_mode(self, state):
        self.layer.show_selected_label = Qt.CheckState(state) == Qt.CheckState.Checked

    def on_change_brush_size(self, value):
        """Change paint brush size."""
        self.layer.brush_size = value

    def on_change_rendering(self, text):
        """Change rendering mode for image display."""
        self.layer.rendering = text

    def on_change_contiguous(self, state):
        """Toggle the contiguous state of label layer."""
        self.layer.contiguous = Qt.CheckState(state) == Qt.CheckState.Checked

    def on_change_n_edit_dimensions(self, state):
        """Toggle n-dimensional state of label layer."""
        self.layer.n_edit_dimensions = Qt.CheckState(state) == Qt.CheckState.Checked

    def on_change_contour(self, value):
        """Change contour thickness.

        Parameters
        ----------
        value : int
            Thickness of contour.
        """
        self.layer.contour = value
        self.contour_spin_box.clearFocus()
        self.setFocus()

    def on_change_preserve_labels(self, state: Qt.CheckState) -> None:
        """Toggle preserve_labels state of label layer."""
        self.layer.preserve_labels = Qt.CheckState(state) == Qt.CheckState.Checked

    def on_change_color_mode(self, new_mode: ty.Any) -> None:
        """Change color mode of label layer."""
        self.layer.color_mode = self.color_mode_combobox.currentData()

    def _on_contour_change(self, event=None) -> None:
        """Receive layer model contour value change event and update spinbox."""
        with self.layer.events.contour.blocker():
            value = self.layer.contour
            self.contour_spin_box.setValue(int(value))

    def _on_selected_label_change(self, event=None) -> None:
        """Receive layer model label selection change event and update spinbox."""
        with self.layer.events.selected_label.blocker():
            value = self.layer.selected_label
            self.selection_spin_box.setValue(int(value))

    def _on_brush_size_change(self, event=None) -> None:
        """Receive layer model brush size change event and update the slider."""
        with self.layer.events.brush_size.blocker():
            value = self.layer.brush_size
            value = np.clip(int(value), 1, 40)
            self.brush_size_slider.setValue(value)

    # def _on_n_edit_dimensions_change(self, event=None) -> None:
    #     """Receive layer model n-dim mode change event and update the checkbox."""
    #     with self.layer.events.n_edit_dimensions.blocker():
    #         self.ndimCheckBox.setChecked(self.layer.n_edit_dimensions)

    def _on_contiguous_change(self, event=None) -> None:
        """Receive layer model contiguous change event and update the checkbox."""
        with self.layer.events.contiguous.blocker():
            self.contiguous_checkbox.setChecked(self.layer.contiguous)

    def _on_preserve_labels_change(self, event=None) -> None:
        """Receive layer model preserve_labels event and update the checkbox."""
        with self.layer.events.preserve_labels.blocker():
            self.preserve_labels_checkbox.setChecked(self.layer.preserve_labels)

    def _on_show_selected_label_change(self):
        """Receive layer model show_selected_labels event and update the checkbox."""
        with self.layer.events.show_selected_label.blocker():
            self.selected_color_checkbox.setChecked(self.layer.show_selected_label)

    def _on_color_mode_change(self, event=None) -> None:
        """Receive layer model color."""
        with self.layer.events.color_mode.blocker():
            hp.set_combobox_current_index(self.color_mode_combobox, self.layer.color_mode)

    def _on_rendering_change(self):
        """Receive layer model rendering change event and update dropdown menu."""
        with self.layer.events.rendering.blocker():
            hp.set_combobox_current_index(self.renderCombobox, self.layer.rendering)

    def _on_ndisplay_changed(self) -> None:
        render_visible = self.ndisplay == 3
        self.renderCombobox.setVisible(render_visible)
        self.renderLabel.setVisible(render_visible)
        self._on_editable_or_visible_change()

    def _on_editable_or_visible_change(self, event=None) -> None:
        """Receive layer model editable change event & enable/disable buttons."""
        hp.enable_with_opacity(
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
                self.blendComboBox,
                self.opacitySlider,
                self.selection_spin_box,
                self.shuffle_button,
                self.renderCombobox,
            ],
            self.layer.editable and self.layer.visible,
        )
        super()._on_editable_or_visible_change(event)

    def deleteLater(self):
        disconnect_events(self.layer.events, self.color_box)
        super().deleteLater()


class QtColorBox(QWidget):
    """A widget that shows a square with the current label color."""

    def __init__(self, layer: Labels):
        super().__init__()

        self.layer = layer
        self.layer.events.selected_label.connect(self._on_selected_label_change)
        self.layer.events.opacity.connect(self._on_opacity_change)

        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        self._height = 24
        self.setFixedWidth(self._height)
        self.setFixedHeight(self._height)
        self.setToolTip("Selected label color")

    def _on_selected_label_change(self, event=None) -> None:
        """Receive layer model label selection change event & update colorbox."""
        self.update()

    def _on_opacity_change(self, event=None) -> None:
        """Receive layer model label selection change event & update colorbox."""
        self.update()

    def paintEvent(self, event) -> None:
        """Paint the colorbox.  If no color, display a checkerboard pattern."""
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
