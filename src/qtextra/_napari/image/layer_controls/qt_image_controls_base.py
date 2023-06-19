"""Base image controls."""
from contextlib import suppress
from functools import partial

from napari._qt.layer_controls.qt_colormap_combobox import QtColormapComboBox
from qtpy.QtCore import Qt
from qtpy.QtGui import QImage, QPixmap
from superqt.sliders import QRangeSlider

import qtextra.helpers as hp
from qtextra._napari.common.layer_controls.qt_layer_controls_base import QtLayerControls


class QtBaseImageControls(QtLayerControls):
    """Superclass for classes requiring colormaps, contrast & gamma sliders.

    This class is never directly instantiated anywhere.
    It is subclassed by QtImageControls and QtSurfaceControls.

    Attributes
    ----------
    clim_pop :
        Popup widget launching the contrast range slider.
    colorbarLabel : qtpy.QtWidgets.QLabel
        Label text of colorbar widget.
    colormap_combobox : qtpy.QtWidgets.QComboBox
        Dropdown widget for selecting the layer colormap.
    contrast_limits_slider : qtpy.QtWidgets.QHRangeSlider
        Contrast range slider widget.
    gamma_slider : qtpy.QtWidgets.QSlider
        Gamma adjustment slider widget.
    layer : napari.layers.Layer
        An instance of a napari layer.

    """

    def __init__(self, layer):
        super().__init__(layer)
        self._ndisplay: int = 2

        self.layer.events.colormap.connect(self._on_colormap_change)
        self.layer.events.gamma.connect(self._on_gamma_change)
        self.layer.events.contrast_limits.connect(self._on_contrast_limits_change)
        self.layer.events.interpolation2d.connect(self._on_interpolation_change)
        self.layer.events.interpolation3d.connect(self._on_interpolation_change)

        colormap_combobox = QtColormapComboBox(self)
        colormap_combobox.setObjectName("colormapComboBox")
        colormap_combobox.addItems(self.layer.colormaps)
        colormap_combobox._allitems = set(self.layer.colormaps)
        colormap_combobox.currentTextChanged.connect(self.on_change_color)
        self.colormap_combobox = colormap_combobox

        self.colorbar_label = hp.make_label(self, "")
        self.colorbar_label.setObjectName("colorbar")
        self.colorbar_label.setToolTip("Colorbar")

        # Create contrast_limits slider
        self.contrast_limits_slider = QRangeSlider(Qt.Horizontal, self)
        self.contrast_limits_slider.setRange(*self.layer.contrast_limits_range)
        decimals = range_to_decimals(self.layer.contrast_limits_range, self.layer.dtype)
        self.contrast_limits_slider.setSingleStep(10**-decimals)
        self.contrast_limits_slider.setValue(self.layer.contrast_limits)
        self.contrast_limits_slider.mousePressEvent = self._clim_mousepress
        set_clim = partial(setattr, self.layer, "contrast_limits")
        set_clim_range = partial(setattr, self.layer, "contrast_limits_range")
        self.contrast_limits_slider.valueChanged.connect(set_clim)
        self.contrast_limits_slider.rangeChanged.connect(set_clim_range)

        # gamma slider
        sld = hp.make_int_spin_box(self, minimum=2, maximum=200, step_size=2)
        sld.setFocusPolicy(Qt.NoFocus)
        sld.setValue(100)
        sld.valueChanged.connect(self.gamma_slider_changed)
        self.gamma_slider = sld
        self._on_gamma_change()

        self._on_colormap_change()

    def on_change_color(self, text):
        """Change colormap on the layer model.

        Parameters
        ----------
        text : str
            Colormap name.
        """
        self.layer.colormap = text

    def _clim_mousepress(self, event):
        """Update the slider, or, on right-click, pop-up an expanded slider.

        The expanded slider provides finer control, directly editable values,
        and the ability to change the available range of the sliders."""
        return QRangeSlider.mousePressEvent(self.contrast_limits_slider, event)

    def _on_contrast_limits_change(self, event=None):
        """Receive layer model contrast limits change event and update slider."""
        with hp.qt_signals_blocked(self.contrast_limits_slider):
            self.contrast_limits_slider.setRange(*self.layer.contrast_limits_range)
            self.contrast_limits_slider.setValue(self.layer.contrast_limits)

        # clim_popup will throw an AttributeError if not yet created
        # and a RuntimeError if it has already been cleaned up.
        # we only want to update the slider if it's active
        with suppress(AttributeError, RuntimeError):
            self.clim_pop.slider.setRange(self.layer.contrast_limits_range)
            with hp.qt_signals_blocked(self.clim_pop.slider):
                clims = self.layer.contrast_limits
                self.clim_pop.slider.setValue(clims)
                self.clim_pop._on_values_change(clims)

    def _on_colormap_change(self, event=None):
        """Receive layer model colormap change event and update dropdown menu."""
        name = self.layer.colormap.name
        if name not in self.colormap_combobox._allitems:
            self.colormap_combobox._allitems.add(name)
            self.colormap_combobox.addItem(name)
        if name != self.colormap_combobox.currentText():
            self.colormap_combobox.setCurrentText(name)

        # Note that QImage expects the image width followed by height
        cbar = self.layer.colormap.colorbar
        image = QImage(
            cbar,
            cbar.shape[1],
            cbar.shape[0],
            QImage.Format_RGBA8888,
        )
        self.colorbar_label.setPixmap(QPixmap.fromImage(image))

    def gamma_slider_changed(self, value):
        """Change gamma value on the layer model.

        Parameters
        ----------
        value : float
            Gamma adjustment value.
            https://en.wikipedia.org/wiki/Gamma_correction
        """
        self.layer.gamma = value / 100

    def _on_gamma_change(self, event=None):
        """Receive the layer model gamma change event and update the slider."""
        with hp.qt_signals_blocked(self.gamma_slider):
            self.gamma_slider.setValue(int(self.layer.gamma * 100))

    def on_change_interpolation(self, text):
        """Change interpolation mode for image display.

        Parameters
        ----------
        text : str
            Interpolation mode used by vispy. Must be one of our supported
            modes:
            'bessel', 'bicubic', 'bilinear', 'blackman', 'catrom', 'gaussian',
            'hamming', 'hanning', 'hermite', 'kaiser', 'lanczos', 'mitchell',
            'nearest', 'spline16', 'spline36'
        """
        if self.ndisplay == 2:
            self.layer.interpolation2d = text
        else:
            self.layer.interpolation3d = text

    def _on_interpolation_change(self, event):
        """Receive layer interpolation change event and update dropdown menu."""
        interp_string = event.value.value
        with self.layer.events.interpolation2d.blocker(), self.layer.events.interpolation3d.blocker():
            if self.interpComboBox.findText(interp_string) == -1:
                self.interpComboBox.addItem(interp_string)
            self.interpComboBox.setCurrentText(interp_string)

    def closeEvent(self, event):
        """Close event."""
        self.deleteLater()
        event.accept()

    @property
    def ndisplay(self) -> int:
        """The number of dimensions displayed in the canvas."""
        return self._ndisplay

    @ndisplay.setter
    def ndisplay(self, ndisplay: int) -> None:
        self._ndisplay = ndisplay
        self._on_ndisplay_changed()

    def _on_ndisplay_changed(self) -> None:
        """Respond to a change to the number of dimensions displayed in the viewer.

        This is needed because some layer controls may have options that are specific
        to 2D or 3D visualization only.
        """
        pass


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
