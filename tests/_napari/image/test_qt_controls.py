"""Test controls"""
import numpy as np
import pytest
from napari.layers import Image, Labels
from qtextra._napari.common.layer_controls.qt_image_controls import QtBaseImageControls, QtImageControls
from qtextra._napari.common.layer_controls.qt_labels_controls import QtLabelsControls

# make label data
np.random.seed(0)
_LABELS = np.random.randint(5, size=(10, 15))
_COLOR = {1: "white", 2: "blue", 3: "green", 4: "red", 5: "yellow"}
# make image data
_IMAGE = np.arange(100).astype(np.uint16).reshape((10, 10))


@pytest.mark.parametrize("layer", [Image(_IMAGE)])
def test_base_controls_creation(qtbot, layer):
    """Check basic creation of QtBaseImageControls works"""
    qtctrl = QtBaseImageControls(layer)
    qtbot.addWidget(qtctrl)
    original_clims = tuple(layer.contrast_limits)
    slider_clims = qtctrl.contrast_limits_slider.value()
    assert slider_clims[0] == 0
    assert slider_clims[1] == 99
    assert tuple(slider_clims) == original_clims

    new_clims = (20, 40)
    layer.contrast_limits = new_clims
    assert tuple(qtctrl.contrast_limits_slider.value()) == new_clims


@pytest.mark.parametrize("layer", [Image(_IMAGE)])
def test_image_controls_creation(qtbot, layer):
    """Check basic creation of QtBaseImageControls works"""
    qtctrl = QtImageControls(layer)
    qtbot.addWidget(qtctrl)
    original_clims = tuple(layer.contrast_limits)
    slider_clims = qtctrl.contrast_limits_slider.value()
    assert slider_clims[0] == 0
    assert slider_clims[1] == 99
    assert tuple(slider_clims) == original_clims

    new_clims = (20, 40)
    layer.contrast_limits = new_clims
    assert tuple(qtctrl.contrast_limits_slider.value()) == new_clims


def test_changing_layer_color_mode_updates_combo_box(qtbot):
    """Updating layer color mode changes the combo box selection"""
    layer = Labels(_LABELS, color=_COLOR)
    qtctrl = QtLabelsControls(layer)
    qtbot.addWidget(qtctrl)

    original_color_mode = layer.color_mode
    assert original_color_mode == qtctrl.color_mode_combobox.currentText()

    layer.color_mode = "auto"
    assert layer.color_mode == qtctrl.color_mode_combobox.currentText()
