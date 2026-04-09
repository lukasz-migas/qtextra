from __future__ import annotations

from qtpy.QtCore import QSize

from qtextra.widgets.qt_toolbar_mini import QtMiniToolbar


def test_qt_mini_toolbar_named_icon_size_uses_preset(qtbot):
    toolbar = QtMiniToolbar(None, add_spacer=False, icon_size="average")
    qtbot.addWidget(toolbar)

    button = toolbar.add_qta_tool("help")

    assert button.minimumSize() == QSize(24, 24)
    assert button.maximumSize() == QSize(24, 24)
    assert button.iconSize() == QSize(24, 24)


def test_qt_mini_toolbar_default_qta_tool_size_is_fixed_26(qtbot):
    toolbar = QtMiniToolbar(None, add_spacer=False)
    qtbot.addWidget(toolbar)

    button = toolbar.add_qta_tool("help")

    assert button.minimumSize() == QSize(26, 26)
    assert button.maximumSize() == QSize(26, 26)
    assert button.iconSize() == QSize(26, 26)
