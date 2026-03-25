"""Tests for the read-more label widget."""

from qtextra.widgets.qt_label_read_more import QReadMoreLessLabel


def test_qreadmorelesslabel_supports_split_only_content(qtbot):
    widget = QReadMoreLessLabel(None, "Left content<split>Right content")
    qtbot.addWidget(widget)

    assert widget.readmore is False
    assert widget.explanation_text_left.text() == "Left content"
    assert widget.explanation_text_right.text() == "Right content"
    assert widget.vertical_break.isHidden() is False


def test_qreadmorelesslabel_toggles_read_more_text(qtbot):
    text = "Summary<moreless>Full left<split>Full right"
    widget = QReadMoreLessLabel(None, text)
    qtbot.addWidget(widget)

    assert widget.explanation_text_left.text() == "Summary<b>Read more...</b>"
    assert widget.explanation_text_right.text() == ""

    widget.state_toggle(None)
    assert widget.readmore is True
    assert widget.explanation_text_left.text() == "Full left"
    assert widget.explanation_text_right.text() == "Full right<b>Read less...</b>"

    widget.state_toggle(None)
    assert widget.readmore is False
    assert widget.explanation_text_left.text() == "Summary<b>Read more...</b>"
    assert widget.explanation_text_right.text() == ""


def test_qreadmorelesslabel_hides_right_side_for_empty_read_more_content(qtbot):
    text = "Summary<moreless>Expanded<split>   "
    widget = QReadMoreLessLabel(None, text)
    qtbot.addWidget(widget)

    assert widget.vertical_break.isHidden() is True
    assert widget.explanation_text_right.isHidden() is True
