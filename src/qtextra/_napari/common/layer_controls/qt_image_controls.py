"""Image controls."""
from napari._qt.layer_controls.qt_image_controls import PlaneNormalButtons
from napari.layers.image._image_constants import ImageRendering, Interpolation, VolumeDepiction
from napari.layers.image._image_key_bindings import (
    orient_plane_normal_along_view_direction,
    orient_plane_normal_along_x,
    orient_plane_normal_along_y,
    orient_plane_normal_along_z,
)
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QHBoxLayout

import qtextra.helpers as hp
from qtextra._napari.common.layer_controls.qt_image_controls_base import QtBaseImageControls


# noinspection PyMissingOrEmptyDocstring
class QtImageControls(QtBaseImageControls):
    """Qt view and controls for the napari Image layer."""

    def __init__(self, layer):
        super().__init__(layer)
        self.layer.events.interpolation2d.connect(self._on_interpolation_change)
        self.layer.events.interpolation3d.connect(self._on_interpolation_change)
        self.layer.events.rendering.connect(self._on_rendering_change)
        self.layer.events.iso_threshold.connect(self._on_iso_threshold_change)
        self.layer.events.attenuation.connect(self._on_attenuation_change)
        self.layer.events.depiction.connect(self._on_depiction_change)
        self.layer.plane.events.thickness.connect(self._on_plane_thickness_change)
        self.layer.events.editable.connect(self._on_editable_or_visible_change)
        self.layer.events.visible.connect(self._on_editable_or_visible_change)

        self.interpolation_combobox = hp.make_combobox(self)
        hp.set_combobox_data(self.interpolation_combobox, Interpolation, self.layer.interpolation2d)
        self.interpolation_combobox.currentTextChanged.connect(self.on_change_interpolation)

        self.render_label = hp.make_label(self, "Rendering")
        self.render_combobox = hp.make_combobox(self)
        hp.set_combobox_data(self.render_combobox, ImageRendering, self.layer.rendering)
        self.render_combobox.currentTextChanged.connect(self.on_change_rendering)

        self.depiction_label = hp.make_label(self, "Depiction")
        self.depiction_combobox = hp.make_combobox(self)
        hp.set_combobox_data(self.depiction_combobox, VolumeDepiction, self.layer.depiction)
        self.depiction_combobox.currentTextChanged.connect(self.on_change_depiction)

        # plane controls
        self.planeNormalButtons = PlaneNormalButtons(self)
        self.planeNormalLabel = hp.make_label(self, "Plane normal", tooltip="Change plane normal.")
        self.planeNormalButtons.xButton.clicked.connect(lambda x: orient_plane_normal_along_x(self.layer))
        self.planeNormalButtons.yButton.clicked.connect(lambda x: orient_plane_normal_along_y(self.layer))
        self.planeNormalButtons.zButton.clicked.connect(lambda x: orient_plane_normal_along_z(self.layer))
        self.planeNormalButtons.obliqueButton.clicked.connect(
            lambda x: orient_plane_normal_along_view_direction(self.layer)
        )

        self.planeThicknessSlider = hp.make_double_slider_with_text(self, 1, 50)
        self.planeThicknessLabel = hp.make_label(self, "Plane thickness", tooltip="Change plane thickness.")
        self.planeThicknessSlider.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.planeThicknessSlider.setValue(self.layer.plane.thickness)
        self.planeThicknessSlider.valueChanged.connect(self.on_change_plane_thickness)

        cmin, cmax = self.layer.contrast_limits_range
        self.iso_threshold_label = hp.make_label(self, "Iso threshold")
        sld = hp.make_double_slider_with_text(self, cmin, cmax, value=self.layer.iso_threshold)
        sld.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        sld.valueChanged.connect(self.on_change_iso_threshold)
        self.iso_threshold_slider = sld

        self.attenuation_label = hp.make_label(self, "Attenuation")
        sld = hp.make_slider_with_text(self, 0, 100, value=int(self.layer.attenuation * 200))
        sld.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        sld.valueChanged.connect(self.on_change_attenuation)
        self.attenuation_slider = sld

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
        self.layout().addRow(self.opacityLabel, self.opacitySlider)
        self.layout().addRow(hp.make_label(self, "Contrast limits"), self.contrast_limits_slider)
        self.layout().addRow(hp.make_label(self, "Auto-contrast"), self.autoScaleBar)
        self.layout().addRow(hp.make_label(self, "Gamma"), self.gamma_slider)
        self.layout().addRow(hp.make_label(self, "Colormap"), colormap_layout)
        self.layout().addRow(hp.make_label(self, "Blending"), self.blendComboBox)
        self.layout().addRow(hp.make_label(self, "Interpolation"), self.interpolation_combobox)
        self.layout().addRow(self.depiction_label, self.depiction_combobox)
        self.layout().addRow(self.render_label, self.render_combobox)
        self.layout().addRow(self.iso_threshold_label, self.iso_threshold_slider)
        self.layout().addRow(self.attenuation_label, self.attenuation_slider)
        self.layout().addRow(self.planeNormalLabel, self.planeNormalButtons)
        self.layout().addRow(self.planeThicknessLabel, self.planeThicknessSlider)
        self.layout().addRow(hp.make_label(self, "Editable"), self.editable_checkbox)
        self._on_ndisplay_changed()
        self._on_editable_or_visible_change()

    def _on_editable_or_visible_change(self, event=None):
        """Receive layer model editable change event & enable/disable buttons."""
        hp.enable_with_opacity(
            self,
            [
                self.opacitySlider,
                self.contrast_limits_slider,
                self.autoScaleBar,
                self.gamma_slider,
                self.blendComboBox,
                self.depiction_combobox,
                self.render_combobox,
                self.iso_threshold_slider,
                self.attenuation_slider,
                self.interpolation_combobox,
                self.planeNormalButtons,
                self.planeThicknessSlider,
                self.colormap_combobox,
                self.colorbar_label,
            ],
            self.layer.editable and self.layer.visible,
        )
        super()._on_editable_or_visible_change(event)

    def on_change_interpolation(self, text):
        """Change interpolation mode for image display."""
        if text:
            if self.ndisplay == 2:
                self.layer.interpolation2d = text
            else:
                self.layer.interpolation3d = text

    def on_change_scaling(self, text: str) -> None:
        """Change image scaling."""
        self.layer._keep_auto_contrast = text == "Continuous"

    def on_change_rendering(self, text: str) -> None:
        """Change rendering mode for image display."""
        self.layer.rendering = text
        self._update_rendering_parameter_visibility()

    def on_change_depiction(self, text: str) -> None:
        self.layer.depiction = text
        self._update_plane_parameter_visibility()

    def on_change_plane_thickness(self, value: float) -> None:
        self.layer.plane.thickness = value

    def on_change_iso_threshold(self, value: float) -> None:
        """Change iso-surface threshold on the layer model."""
        with self.layer.events.blocker(self._on_iso_threshold_change):
            self.layer.iso_threshold = value / 100

    def _on_contrast_limits_change(self):
        with self.layer.events.blocker(self._on_iso_threshold_change):
            cmin, cmax = self.layer.contrast_limits_range
            self.iso_threshold_slider.setMinimum(cmin)
            self.iso_threshold_slider.setMaximum(cmax)
        return super()._on_contrast_limits_change()

    def _on_iso_threshold_change(self, event=None) -> None:
        """Receive layer model iso-surface change event and update the slider."""
        with self.layer.events.iso_threshold.blocker():
            self.iso_threshold_slider.setValue(int(self.layer.iso_threshold * 100))

    def on_change_attenuation(self, value: float) -> None:
        """Change attenuation rate for attenuated maximum intensity projection."""
        with self.layer.events.blocker(self._on_attenuation_change):
            self.layer.attenuation = value / 200

    def _on_attenuation_change(self, event=None) -> None:
        """Receive layer model attenuation change event and update the slider."""
        with self.layer.events.attenuation.blocker():
            self.attenuation_slider.setValue(int(self.layer.attenuation * 200))

    def _on_interpolation_change(self, event):
        """Receive layer interpolation change event and update dropdown menu."""
        with self.layer.events.interpolation2d.blocker(), self.layer.events.interpolation3d.blocker():
            hp.set_combobox_current_index(
                self.interpolation_combobox,
                self.layer.interpolation2d if self.ndisplay == 2 else self.layer.interpolation3d,
            )

    def _on_rendering_change(self, event=None) -> None:
        """Receive layer model rendering change event and update dropdown menu."""
        with self.layer.events.rendering.blocker():
            hp.set_combobox_current_index(self.render_combobox, self.layer.rendering)
            self._update_rendering_parameter_visibility()

    def _update_interpolation_combo(self) -> None:
        interp_names = [i.value for i in Interpolation.view_subset()]
        interp = self.layer.interpolation2d if self.ndisplay == 2 else self.layer.interpolation3d
        with hp.qt_signals_blocked(self.interpolation_combobox):
            self.interpolation_combobox.clear()
            self.interpolation_combobox.addItems(interp_names)
            self.interpolation_combobox.setCurrentText(interp)

    def _on_ndisplay_changed(self, event=None) -> None:
        """Toggle between 2D and 3D visualization modes."""
        self._update_interpolation_combo()
        self._update_plane_parameter_visibility()
        if self.ndisplay == 2:
            self.iso_threshold_slider.hide()
            self.iso_threshold_label.hide()
            self.attenuation_slider.hide()
            self.attenuation_label.hide()
            self.render_combobox.hide()
            self.render_label.hide()
            self.depiction_label.hide()
            self.depiction_combobox.hide()
        else:
            self.render_combobox.show()
            self.render_label.show()
            self.depiction_label.show()
            self.depiction_combobox.show()
            self._update_rendering_parameter_visibility()

    def _on_depiction_change(self) -> None:
        """Receive layer model depiction change event and update combobox."""
        with self.layer.events.depiction.blocker():
            hp.set_combobox_current_index(self.depiction_combobox, self.layer.depiction)
            self._update_plane_parameter_visibility()

    def _on_plane_thickness_change(self) -> None:
        with self.layer.plane.events.blocker():
            self.planeThicknessSlider.setValue(self.layer.plane.thickness)

    def _update_plane_parameter_visibility(self) -> None:
        """Hide plane rendering controls if they aren't needed."""
        depiction = VolumeDepiction(self.layer.depiction)
        visible = depiction == VolumeDepiction.PLANE and self.ndisplay == 3
        self.planeNormalButtons.setVisible(visible)
        self.planeNormalLabel.setVisible(visible)
        self.planeThicknessSlider.setVisible(visible)
        self.planeThicknessLabel.setVisible(visible)

    def _update_rendering_parameter_visibility(self) -> None:
        """Hide iso-surface rendering parameters if they aren't needed."""
        rendering = ImageRendering(self.layer.rendering)
        iso_threshold_visible = rendering == ImageRendering.ISO
        self.iso_threshold_label.setVisible(iso_threshold_visible)
        self.iso_threshold_slider.setVisible(iso_threshold_visible)
        attenuation_visible = rendering == ImageRendering.ATTENUATED_MIP
        self.attenuation_label.setVisible(attenuation_visible)
        self.attenuation_slider.setVisible(attenuation_visible)
