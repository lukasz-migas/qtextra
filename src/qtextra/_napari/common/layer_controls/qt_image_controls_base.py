"""Base image controls."""

from napari._qt.layer_controls.qt_colormap_combobox import QtColormapComboBox
from napari._qt.layer_controls.qt_image_controls_base import AutoScaleButtons, QContrastLimitsPopup
from napari.layers import Image
from napari.utils.colormaps import AVAILABLE_COLORMAPS
from napari.utils.events.event_utils import connect_setattr
from qtpy.QtCore import Qt
from qtpy.QtGui import QIcon, QImage, QPixmap
from superqt.sliders import QDoubleRangeSlider

import qtextra.helpers as hp
from qtextra._napari.common.layer_controls.qt_layer_controls_base import QtLayerControls


class _QDoubleRangeSlider(QDoubleRangeSlider):
    def mousePressEvent(self, event):
        """Update the slider, or, on right-click, pop-up an expanded slider.

        The expanded slider provides finer control, directly editable values,
        and the ability to change the available range of the sliders.

        Parameters
        ----------
        event : napari.utils.event.Event
            The napari event that triggered this method.
        """
        if event.button() == Qt.MouseButton.RightButton:
            self.parent().show_clim_popupup()
        else:
            super().mousePressEvent(event)


class QtBaseImageControls(QtLayerControls):
    """Superclass for classes requiring colormaps, contrast & gamma sliders."""

    layer: Image

    def __init__(self, layer: Image):
        super().__init__(layer)
        self._ndisplay: int = 2

        self.layer.events.colormap.connect(self._on_colormap_change)
        self.layer.events.gamma.connect(self._on_gamma_change)
        self.layer.events.contrast_limits.connect(self._on_contrast_limits_change)
        self.layer.events.contrast_limits_range.connect(self._on_contrast_limits_range_change)

        colormap_combobox = QtColormapComboBox(self)
        colormap_combobox.setObjectName("colormap_combobox")
        colormap_combobox._allitems = set(self.layer.colormaps)
        for name, cm in AVAILABLE_COLORMAPS.items():
            if name in self.layer.colormaps:
                colormap_combobox.addItem(cm._display_name, name)
            colormap_combobox.currentTextChanged.connect(self.on_change_color)
        self.colormap_combobox = colormap_combobox

        self.colorbar_label = hp.make_btn(
            self, "", tooltip="Colorbar", object_name="colorbar", func=self.on_make_colormap
        )

        # Create contrast_limits slider
        self.contrast_limits_slider = _QDoubleRangeSlider(Qt.Orientation.Horizontal, self)
        self.contrast_limits_slider.setRange(*self.layer.contrast_limits_range)
        decimals = range_to_decimals(self.layer.contrast_limits_range, self.layer.dtype)
        self.contrast_limits_slider.setSingleStep(10**-decimals)
        self.contrast_limits_slider.setValue(self.layer.contrast_limits)
        self.contrast_limits_slider.setToolTip("Right click for detailed slider popup.")
        self.clim_popup = None
        connect_setattr(self.contrast_limits_slider.valueChanged, self.layer, "contrast_limits")
        connect_setattr(self.contrast_limits_slider.rangeChanged, self.layer, "contrast_limits_range")

        self.autoScaleBar = AutoScaleButtons(layer, self)

        # gamma slider
        sld = hp.make_double_slider_with_text(self, 0.1, 2, step_size=0.02, n_decimals=2)
        sld.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        sld.setValue(layer.gamma)
        connect_setattr(sld.valueChanged, self.layer, "gamma")
        self.gamma_slider = sld

        self._on_gamma_change()
        self._on_colormap_change()

    def on_make_colormap(self):
        """Make new colormap."""
        from qtextra.utils.colormap import napari_colormap

        color = hp.get_color(self, as_hex=True)
        if color:
            colormap = napari_colormap(color, name=color)
            self.layer.colormap = colormap

    def on_change_color(self, text):
        """Change colormap on the layer model."""
        self.layer.colormap = self.colormap_combobox.currentData()

    def _on_contrast_limits_change(self):
        """Receive layer model contrast limits change event and update slider."""
        with hp.qt_signals_blocked(self.contrast_limits_slider):
            self.contrast_limits_slider.setValue(self.layer.contrast_limits)

        if self.clim_popup:
            with hp.qt_signals_blocked(self.clim_popup.slider):
                self.clim_popup.slider.setValue(self.layer.contrast_limits)

    def _on_contrast_limits_range_change(self):
        """Receive layer model contrast limits change event and update slider."""
        with hp.qt_signals_blocked(self.contrast_limits_slider):
            decimals = range_to_decimals(self.layer.contrast_limits_range, self.layer.dtype)
            self.contrast_limits_slider.setRange(*self.layer.contrast_limits_range)
            self.contrast_limits_slider.setSingleStep(10**-decimals)

        if self.clim_popup:
            with hp.qt_signals_blocked(self.clim_popup.slider):
                self.clim_popup.slider.setRange(*self.layer.contrast_limits_range)

    def _on_colormap_change(self):
        """Receive layer model colormap change event and update dropdown menu."""
        name = self.layer.colormap.name
        if name not in self.colormap_combobox._allitems and (cm := AVAILABLE_COLORMAPS.get(name)):
            self.colormap_combobox._allitems.add(name)
            self.colormap_combobox.addItem(cm._display_name, name)

        if name != self.colormap_combobox.currentData():
            index = self.colormap_combobox.findData(name)
            self.colormap_combobox.setCurrentIndex(index)

        # Note that QImage expects the image width followed by height
        cbar = self.layer.colormap.colorbar
        image = QImage(
            cbar,
            cbar.shape[1],
            cbar.shape[0],
            QImage.Format_RGBA8888,
        )
        self.colorbar_label.setIcon(QIcon(QPixmap.fromImage(image)))

    def _on_gamma_change(self):
        """Receive the layer model gamma change event and update the slider."""
        with hp.qt_signals_blocked(self.gamma_slider):
            self.gamma_slider.setValue(self.layer.gamma)

    def closeEvent(self, event):
        self.deleteLater()
        self.layer.events.disconnect(self)
        super().closeEvent(event)

    def show_clim_popupup(self):
        self.clim_popup = QContrastLimitsPopup(self.layer, self)
        self.clim_popup.setParent(self)
        self.clim_popup.move_to("top", min_length=650)
        self.clim_popup.show()


def range_to_decimals(range_, dtype):
    """Convert a range to decimals of precision.

    Parameters
    ----------
    range_ : tuple
        Slider range, min and then max values.
    dtype : np.dtype
        Data type of the layer. Integers layers are given integer.
        step sizes.

    Returns
    -------
    int
        Decimals of precision.
    """
    import numpy as np

    if hasattr(dtype, "numpy_dtype"):
        # retrieve the corresponding numpy.dtype from a tensorstore.dtype
        dtype = dtype.numpy_dtype

    if np.issubdtype(dtype, np.integer):
        return 0
    else:
        # scale precision with the log of the data range order of magnitude
        # eg.   0 - 1   (0 order of mag)  -> 3 decimal places
        #       0 - 10  (1 order of mag)  -> 2 decimals
        #       0 - 100 (2 orders of mag) -> 1 decimal
        #       ≥ 3 orders of mag -> no decimals
        # no more than 64 decimals
        d_range = np.subtract(*range_[::-1])
        return min(64, max(int(3 - np.log10(d_range)), 0))
