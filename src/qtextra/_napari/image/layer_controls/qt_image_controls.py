from napari.layers.image._image_constants import ImageRendering, Interpolation
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QHBoxLayout, QSlider

import qtextra.helpers as hp
from qtextra._napari.image.layer_controls.qt_image_controls_base import QtBaseImageControls


class QtImageControls(QtBaseImageControls):
    """Qt view and controls for the napari Image layer.

    Parameters
    ----------
    layer : napari.layers.Image
        An instance of a napari Image layer.

    Attributes
    ----------
    attenuation_slider : qtpy.QtWidgets.QSlider
        Slider controlling attenuation rate for `attenuated_mip` mode.
    attenuation_label : qtpy.QtWidgets.QLabel
        Label for the attenuation slider widget.
    layout : qtpy.QtWidgets.QGridLayout
        Layout of Qt widget controls for the layer.
    interpolation_combobox : qtpy.QtWidgets.QComboBox
        Dropdown menu to select the interpolation mode for image display.
    interpLabel : qtpy.QtWidgets.QLabel
        Label for the interpolation dropdown menu.
    iso_threshold_slider : qtpy.QtWidgets.QSlider
        Slider controlling the isosurface threshold value for rendering.
    iso_threshold_label : qtpy.QtWidgets.QLabel
        Label for the isosurface threshold slider widget.
    layer : napari.layers.Image
        An instance of a napari Image layer.
    render_combobox : qtpy.QtWidgets.QComboBox
        Dropdown menu to select the rendering mode for image display.
    render_label : qtpy.QtWidgets.QLabel
        Label for the rendering mode dropdown menu.
    """

    def __init__(self, layer):
        super().__init__(layer)
        self.layer.events.rendering.connect(self._on_rendering_change)
        self.layer.events.iso_threshold.connect(self._on_iso_threshold_change)
        self.layer.events.attenuation.connect(self._on_attenuation_change)
        self.layer.events._ndisplay.connect(self._on_ndisplay_change)

        self.scaling_combobox = hp.make_combobox(self, ["Individual", "Continuous"])
        self.scaling_combobox.setCurrentText("Individual" if self.layer._keep_auto_contrast is False else "Continuous")
        self.scaling_combobox.currentTextChanged.connect(self.on_change_scaling)

        self.interpolation_combobox = hp.make_combobox(self)
        hp.set_combobox_data(self.interpolation_combobox, Interpolation, self.layer.interpolation2d)
        self.interpolation_combobox.currentTextChanged.connect(self.on_change_interpolation)

        self.render_label = hp.make_label(self, "Rendering")
        self.render_combobox = hp.make_combobox(self)
        hp.set_combobox_data(self.render_combobox, ImageRendering, self.layer.rendering)
        self.render_combobox.currentTextChanged.connect(self.on_change_rendering)

        # self.depiction_label = hp.make_label(self, "Depiction")
        # self.depiction_combobox = hp.make_combobox(self)
        # hp.set_combobox_data(self.depiction_combobox, VolumeDepiction, self.layer.depiction)
        # self.depiction_combobox.currentTextChanged.connect(self.on_change_depiction)

        self.iso_threshold_label = hp.make_label(self, "Iso threshold")
        sld = QSlider(Qt.Horizontal, parent=self)
        sld.setFocusPolicy(Qt.NoFocus)
        sld.setMinimum(0)
        sld.setMaximum(100)
        sld.setSingleStep(1)
        sld.setValue(int(self.layer.iso_threshold * 100))
        sld.valueChanged.connect(self.on_change_iso_threshold)
        self.iso_threshold_slider = sld

        self.attenuation_label = hp.make_label(self, "Attenuation")
        sld = QSlider(Qt.Horizontal, parent=self)
        sld.setFocusPolicy(Qt.NoFocus)
        sld.setMinimum(0)
        sld.setMaximum(100)
        sld.setSingleStep(1)
        sld.setValue(int(self.layer.attenuation * 200))
        sld.valueChanged.connect(self.on_change_attentuation)
        self.attenuation_slider = sld
        self._on_ndisplay_change()

        colormap_layout = QHBoxLayout()
        if hasattr(self.layer, "rgb") and self.layer.rgb:
            colormap_layout.addWidget(hp.make_label(self, "RGB"))
            self.colormap_combobox.setVisible(False)
            self.colorbar_label.setVisible(False)
        else:
            colormap_layout.addWidget(self.colorbar_label)
            colormap_layout.addWidget(self.colormap_combobox)
        colormap_layout.addStretch(1)

        # layout created in QtLayerControls
        self.layout.addRow(hp.make_label(self, "Opacity"), self.opacity_slider)
        self.layout.addRow(hp.make_label(self, "Contrast limits"), self.contrast_limits_slider)
        self.layout.addRow(hp.make_label(self, "Scaling"), self.scaling_combobox)
        self.layout.addRow(hp.make_label(self, "Gamma"), self.gamma_slider)
        self.layout.addRow(hp.make_label(self, "Colormap"), colormap_layout)
        self.layout.addRow(hp.make_label(self, "Blending"), self.blending_combobox)
        self.layout.addRow(hp.make_label(self, "Interpolation"), self.interpolation_combobox)
        self.layout.addRow(self.render_label, self.render_combobox)
        self.layout.addRow(self.iso_threshold_label, self.iso_threshold_slider)
        self.layout.addRow(self.attenuation_label, self.attenuation_slider)
        self.layout.addRow(hp.make_label(self, "Editable"), self.editable_checkbox)
        self._on_editable_change()

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
        if text:
            if self.ndisplay == 2:
                self.layer.interpolation2d = text
            else:
                self.layer.interpolation3d = text

    def on_change_scaling(self, text: str):
        """Change image scaling."""
        self.layer._keep_auto_contrast = text == "Continuous"

    def on_change_rendering(self, text):
        """Change rendering mode for image display.

        Parameters
        ----------
        text : str
            Rendering mode used by vispy.
            Selects a preset rendering mode in vispy that determines how
            volume is displayed:
            * translucent: voxel colors are blended along the view ray until
              the result is opaque.
            * mip: maximum intensity projection. Cast a ray and display the
              maximum value that was encountered.
            * additive: voxel colors are added along the view ray until
              the result is saturated.
            * iso: isosurface. Cast a ray until a certain threshold is
              encountered. At that location, lighning calculations are
              performed to give the visual appearance of a surface.
            * attenuated_mip: attenuated maximum intensity projection. Cast a
              ray and attenuate values based on integral of encountered values,
              display the maximum value that was encountered after attenuation.
              This will make nearer objects appear more prominent.
        """
        if text:
            self.layer.rendering = text
        self._toggle_rendering_parameter_visbility()

    def on_change_iso_threshold(self, value):
        """Change isosurface threshold on the layer model.

        Parameters
        ----------
        value : float
            Threshold for isosurface.
        """
        with self.layer.events.blocker(self._on_iso_threshold_change):
            self.layer.iso_threshold = value / 100

    def _on_iso_threshold_change(self, event):
        """Receive layer model isosurface change event and update the slider.

        Parameters
        ----------
        event : napari.utils.event.Event
            The napari event that triggered this method.
        """
        with self.layer.events.iso_threshold.blocker():
            self.iso_threshold_slider.setValue(int(self.layer.iso_threshold * 100))

    def on_change_attentuation(self, value):
        """Change attenuation rate for attenuated maximum intensity projection.

        Parameters
        ----------
        value : Float
            Attenuation rate for attenuated maximum intensity projection.
        """
        with self.layer.events.blocker(self._on_attenuation_change):
            self.layer.attenuation = value / 200

    def _on_attenuation_change(self, event):
        """Receive layer model attenuation change event and update the slider.

        Parameters
        ----------
        event : napari.utils.event.Event
            The napari event that triggered this method.
        """
        with self.layer.events.attenuation.blocker():
            self.attenuation_slider.setValue(int(self.layer.attenuation * 200))

    def _on_interpolation_change(self, event):
        """Receive layer interpolation change event and update dropdown menu.

        Parameters
        ----------
        event : napari.utils.event.Event
            The napari event that triggered this method.
        """
        with self.layer.events.interpolation2d.blocker(), self.layer.events.interpolation3d.blocker():
            index = self.interpolation_combobox.findText(
                self.layer.interpolation2d if self.ndisplay == 2 else self.layer.interpolation3d, Qt.MatchFixedString
            )
            self.interpolation_combobox.setCurrentIndex(index)

    def _on_rendering_change(self, event):
        """Receive layer model rendering change event and update dropdown menu.

        Parameters
        ----------
        event : napari.utils.event.Event
            The napari event that triggered this method.
        """
        with self.layer.events.rendering.blocker():
            index = self.render_combobox.findText(self.layer.rendering, Qt.MatchFixedString)
            self.render_combobox.setCurrentIndex(index)
            self._toggle_rendering_parameter_visbility()

    def _toggle_rendering_parameter_visbility(self):
        """Hide isosurface rendering parameters if they aren't needed."""
        rendering = ImageRendering(self.layer.rendering)
        if rendering == ImageRendering.ISO:
            self.iso_threshold_slider.show()
            self.iso_threshold_label.show()
        else:
            self.iso_threshold_slider.hide()
            self.iso_threshold_label.hide()
        if rendering == ImageRendering.ATTENUATED_MIP:
            self.attenuation_slider.show()
            self.attenuation_label.show()
        else:
            self.attenuation_slider.hide()
            self.attenuation_label.hide()

    def _update_interpolation_combo(self):
        interp_names = [i.value for i in Interpolation.view_subset()]
        interp = self.layer.interpolation2d if self.ndisplay == 2 else self.layer.interpolation3d
        with hp.qt_signals_blocked(self.interpolation_combobox):
            self.interpolation_combobox.clear()
            self.interpolation_combobox.addItems(interp_names)
            self.interpolation_combobox.setCurrentText(interp)

    def _on_ndisplay_change(self, event=None):
        """Toggle between 2D and 3D visualization modes.

        Parameters
        ----------
        event : napari.utils.event.Event, optional
            The napari event that triggered this method, default is None.
        """
        self._update_interpolation_combo()
        if self.layer._ndisplay == 2:
            self.iso_threshold_slider.hide()
            self.iso_threshold_label.hide()
            self.attenuation_slider.hide()
            self.attenuation_label.hide()
            self.render_combobox.hide()
            self.render_label.hide()
        else:
            self.render_combobox.show()
            self.render_label.show()
            self._toggle_rendering_parameter_visbility()
