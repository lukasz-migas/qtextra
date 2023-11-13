"""Base layer controls."""
from napari._qt.layer_controls.qt_layer_controls_base import QtLayerControls as _QtLayerControls
from napari.layers import Layer
from napari.utils.events import Event

import qtextra.helpers as hp


class QtLayerControls(_QtLayerControls):
    """Override QtLayerControls.."""

    def __init__(self, layer: Layer):
        super().__init__(layer)
        editable_checkbox = hp.make_checkbox(self, "")
        editable_checkbox.stateChanged.connect(self.on_change_editable)
        self.editable_checkbox = editable_checkbox
        self.opacityLabel.setText("Opacity")

    def on_change_editable(self, state):
        """Change editability value on the layer model."""
        with self.layer.events.blocker(self._on_editable_or_visible_change):
            self.layer.editable = state

    def _on_editable_or_visible_change(self, _event: Event = None) -> None:
        """Receive layer model opacity change event and update opacity slider."""
        with self.layer.events.editable.blocker():
            self.editable_checkbox.setChecked(self.layer.editable)


# class QtLayerControls(QFrame):
#     """Superclass for all the other LayerControl classes.
#
#     This class is never directly instantiated anywhere.
#
#     Parameters
#     ----------
#     layer : qtextra.layers.Layer
#         An instance of a qtextra layer.
#
#     Attributes
#     ----------
#     layer : qtextra.layers.Layer
#         An instance of a qtextra layer.
#     layout : qtpy.QtWidgets.QGridLayout
#         Layout of Qt widget controls for the layer.
#     blending_combobox : qtpy.QtWidgets.QComboBox
#         Dropdown widget to select blending mode of layer.
#     opacity_slider : qtpy.QtWidgets.QSlider
#         Slider controlling opacity of the layer.
#     """
#
#     def __init__(self, layer):
#         super().__init__()
#         self.setAttribute(Qt.WA_DeleteOnClose)
#         self.setObjectName("layer")
#         self.setMouseTracking(True)
#
#         self.layer = layer
#         self.layer.events.blending.connect(self._on_blending_change)
#         self.layer.events.opacity.connect(self._on_opacity_change)
#         self.layer.events.editable.connect(self._on_editable_change)
#
#         opacity_slider = hp.make_int_spin_box(self, tooltip="Opacity", step_size=5)
#         # opacity_slider.setFocusPolicy(Qt.NoFocus)
#         opacity_slider.valueChanged.connect(self.on_change_opacity)
#         self.opacity_slider = opacity_slider
#         self._on_opacity_change()
#
#         blending_combobox = hp.make_combobox(self)
#         hp.set_combobox_data(blending_combobox, BLENDING_TRANSLATIONS, self.layer.blending)
#         blending_combobox.currentTextChanged.connect(self.on_change_blending)
#         self.blending_combobox = blending_combobox
#
#         editable_checkbox = hp.make_checkbox(self, "")
#         editable_checkbox.stateChanged.connect(self.on_change_editable)
#         self.editable_checkbox = editable_checkbox
#
#         self.setLayout(hp.make_form_layout(self))
#         self.layout.setSpacing(2)
#         self.setLayout(self.layout)
#
#     def on_change_editable(self, state):
#         """Change editability value on the layer model."""
#         with self.layer.events.blocker(self._on_editable_change):
#             self.layer.editable = state
#
#     def _on_editable_change(self, _event=None):
#         """Receive layer model opacity change event and update opacity slider."""
#         with self.layer.events.editable.blocker():
#             self.editable_checkbox.setChecked(self.layer.editable)
#
#     def on_change_opacity(self, value):
#         """Change opacity value on the layer model.
#
#         Parameters
#         ----------
#         value : float
#             Opacity value for shapes.
#             Input range 0 - 100 (transparent to fully opaque).
#         """
#         with self.layer.events.blocker(self._on_opacity_change):
#             self.layer.opacity = value / 100
#
#     def _on_opacity_change(self, _event=None):
#         """Receive layer model opacity change event and update opacity slider."""
#         with self.layer.events.opacity.blocker():
#             self.opacity_slider.setValue(int(self.layer.opacity * 100))
#
#     def on_change_blending(self, _text):
#         """Change blending mode on the layer model.
#
#         Parameters
#         ----------
#         _text : str
#             Name of blending mode, eg: 'translucent', 'additive', 'opaque'.
#         """
#         self.layer.blending = self.blending_combobox.currentData()
#
#     def _on_blending_change(self, _event=None):
#         """Receive layer model blending mode change event and update slider."""
#         with self.layer.events.blending.blocker():
#             hp.set_combobox_current_index(self.blending_combobox, self.layer.blending)
#
#     def close(self):
#         """Disconnect events when widget is closing."""
#         disconnect_events(self.layer.events, self)
#         for child in self.children():
#             close_method = getattr(child, "close", None)
#             if close_method is not None:
#                 close_method()
#         super().close()
