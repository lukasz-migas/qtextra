"""Test label visual"""


def test_vispy_label_visual_image(make_ionglow_image_viewer):
    view = make_ionglow_image_viewer()
    viewer, qt_widget = view.viewer, view.widget
    assert viewer.text_overlay is not None
    # check font size attribute
    assert qt_widget.text_overlay.node.font_size == viewer.text_overlay.font_size
    viewer.text_overlay.font_size = 13
    assert qt_widget.text_overlay.node.font_size == viewer.text_overlay.font_size == 13
    # check text attribute
    assert qt_widget.text_overlay.node.text == viewer.text_overlay.text
    viewer.text_overlay.text = "TEST TEXT"
    assert qt_widget.text_overlay.node.text == viewer.text_overlay.text == "TEST TEXT"
    # check visible attribute
    assert qt_widget.text_overlay.node.visible == viewer.text_overlay.visible
    viewer.text_overlay.visible = True
    assert qt_widget.text_overlay.node.visible == viewer.text_overlay.visible


def test_vispy_label_visual_line(make_ionglow_line_viewer):
    view = make_ionglow_line_viewer()
    viewer, qt_widget = view.viewer, view.widget
    assert viewer.text_overlay is not None
    # check font size attribute
    assert qt_widget.text_overlay.node.font_size == viewer.text_overlay.font_size
    viewer.text_overlay.font_size = 13
    assert qt_widget.text_overlay.node.font_size == viewer.text_overlay.font_size == 13
    # check text attribute
    assert qt_widget.text_overlay.node.text == viewer.text_overlay.text
    viewer.text_overlay.text = "TEST TEXT"
    assert qt_widget.text_overlay.node.text == viewer.text_overlay.text == "TEST TEXT"
    # check visible attribute
    assert qt_widget.text_overlay.node.visible == viewer.text_overlay.visible
    viewer.text_overlay.visible = True
    assert qt_widget.text_overlay.node.visible == viewer.text_overlay.visible
