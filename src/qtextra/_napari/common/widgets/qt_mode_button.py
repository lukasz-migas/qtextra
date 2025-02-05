"""Mode buttons."""
import typing as ty
import weakref
from enum import Enum

from napari.layers import Layer

from qtextra.widgets.qt_button_icon import QtImagePushButton


class QtModeRadioButton(QtImagePushButton):
    """Enum-based button."""

    def __init__(
        self, layer: Layer, icon_name: str, mode: Enum, tooltip: str = "", checked: bool = False, *args, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.layer_ref = weakref.ref(layer)
        self.set_qta(icon_name)
        self.setToolTip(tooltip or icon_name)
        self.setCheckable(True)
        self.setChecked(checked)
        self.setProperty("mode", icon_name)
        self.set_medium()
        self.mode = mode
        if mode is not None:
            self.toggled.connect(self._set_mode)

    def set_layer(self, layer: Layer):
        """Set layer."""
        self.layer_ref = weakref.ref(layer)

    def _set_mode(self, mode_selected):
        """Toggle the mode associated with the layer.

        Parameters
        ----------
        mode_selected : bool
            Whether this mode is currently selected or not.
        """
        layer = self.layer_ref()
        if layer is None:
            return

        with layer.events.mode.blocker(self._set_mode):
            if mode_selected:
                layer.mode = self.mode


class QtModePushButton(QtImagePushButton):
    """Enum-based button."""

    def __init__(
        self, layer: Layer, icon_name: str, tooltip: str = "", func: ty.Optional[ty.Callable] = None, *args, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.layer_ref = weakref.ref(layer)
        self.set_qta(icon_name)
        self.setToolTip(tooltip or icon_name)
        self.set_medium()
        if func is not None:
            self.clicked.connect(func)

    def set_layer(self, layer: Layer):
        """Set layer."""
        self.layer_ref = weakref.ref(layer)

    def _set_mode(self, mode_selected):
        """Toggle the mode associated with the layer.

        Parameters
        ----------
        mode_selected : bool
            Whether this mode is currently selected or not.
        """
        layer = self.layer_ref()
        if layer is None:
            return

        with layer.events.mode.blocker(self._set_mode):
            if mode_selected:
                layer.mode = self.mode
