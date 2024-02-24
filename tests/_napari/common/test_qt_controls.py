"""Test controls"""
import numpy as np
import pytest
from napari.layers.points._points_constants import Mode as PointsMode
from napari.layers.shapes._shapes_constants import Mode as ShapesMode
from napari.utils.colormaps.standardize_color import transform_color

from qtextra._napari.common.layer_controls.qt_points_controls import QtPointsControls
from qtextra._napari.common.layer_controls.qt_shapes_controls import QtShapesControls\
from napari.layers import Points, Shapes

_SHAPES = np.random.random((10, 4, 2))
_POINTS = np.random.random((10, 10))


@pytest.mark.parametrize("layer", [Shapes(_SHAPES)])
def test_shape_controls_creation(qtbot, layer):
    """Check basic creation of QtShapesControls works"""
    qtctrl = QtShapesControls(layer)
    qtbot.addWidget(qtctrl)

    # test face color
    target_color = transform_color(layer.current_face_color)[0]
    np.testing.assert_almost_equal(transform_color(qtctrl.face_color_swatch.color)[0], target_color)

    # Update current face color
    layer.current_face_color = "red"
    target_color = transform_color(layer.current_face_color)[0]
    np.testing.assert_almost_equal(transform_color(qtctrl.face_color_swatch.color)[0], target_color)

    # test edge color
    target_color = transform_color(layer.current_edge_color)[0]
    np.testing.assert_almost_equal(transform_color(qtctrl.edge_color_swatch.color)[0], target_color)

    # Update current edge color
    layer.current_edge_color = "red"
    target_color = transform_color(layer.current_edge_color)[0]
    np.testing.assert_almost_equal(transform_color(qtctrl.edge_color_swatch.color)[0], target_color)

    # check change of mode
    layer.mode = ShapesMode.ADD_LINE
    assert layer.mode == str(ShapesMode.ADD_LINE)
    assert layer._mode == ShapesMode.ADD_LINE
    assert qtctrl.line_button.isChecked()

    layer.mode = "pan_zoom"
    assert layer._mode == ShapesMode.PAN_ZOOM
    assert qtctrl.panzoom_button.isChecked()


@pytest.mark.parametrize("layer", [Points(_POINTS)])
def test_points_controls_creation(qtbot, layer):
    """Check basic creation of QtPointsControls works"""
    qtctrl = QtPointsControls(layer)
    qtbot.addWidget(qtctrl)

    # test face color
    target_color = transform_color(layer.current_face_color)[0]
    np.testing.assert_almost_equal(transform_color(qtctrl.face_color_swatch.color)[0], target_color)

    # Update current face color
    layer.current_face_color = "red"
    target_color = transform_color(layer.current_face_color)[0]
    np.testing.assert_almost_equal(transform_color(qtctrl.face_color_swatch.color)[0], target_color)

    # test edge color
    target_color = transform_color(layer.current_edge_color)[0]
    np.testing.assert_almost_equal(transform_color(qtctrl.edge_color_swatch.color)[0], target_color)

    # Update current edge color
    layer.current_edge_color = "red"
    target_color = transform_color(layer.current_edge_color)[0]
    np.testing.assert_almost_equal(transform_color(qtctrl.edge_color_swatch.color)[0], target_color)

    # check change of mode
    layer.mode = PointsMode.SELECT
    assert layer._mode == PointsMode.SELECT
    assert qtctrl.select_button.isChecked()

    layer.mode = "add"
    assert layer._mode == PointsMode.ADD
    assert qtctrl.addition_button.isChecked()
