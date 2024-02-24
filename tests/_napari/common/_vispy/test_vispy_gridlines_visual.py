"""Test gridlines visual"""


def test_vispy_gridlines_visual_image(make_ionglow_image_viewer):
    view = make_ionglow_image_viewer()
    viewer, qt_widget = view.viewer, view.widget
    assert viewer.grid_lines is not None
    # check visible attribute
    assert qt_widget.grid_lines.node.visible == viewer.grid_lines.visible
    viewer.grid_lines.visible = True
    assert qt_widget.grid_lines.node.visible == viewer.grid_lines.visible


def test_vispy_gridlines_visual_line(make_ionglow_line_viewer):
    view = make_ionglow_line_viewer()
    viewer, qt_widget = view.viewer, view.widget
    assert viewer.grid_lines is not None
    # check visible attribute
    assert qt_widget.grid_lines.node.visible == viewer.grid_lines.visible
    viewer.grid_lines.visible = True
    assert qt_widget.grid_lines.node.visible == viewer.grid_lines.visible
