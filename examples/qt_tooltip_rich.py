"""QtRichToolTip example."""

from qtpy.QtWidgets import QApplication, QVBoxLayout, QWidget

import qtextra.helpers as hp
from qtextra.config import THEMES
from qtextra.widgets.qt_tooltip_rich import QtRichToolTip, RichToolTipAction, RichToolTipData

app = QApplication([])

widget = QWidget()
widget.setMinimumSize(420, 340)
THEMES.apply(widget)

layout = QVBoxLayout(widget)


def _show_simple() -> None:
    QtRichToolTip.show_tooltip(
        title="Quick Documentation",
        content=(
            "<b>dict.get</b>(key, default=None)<br><br>"
            "Return the value for <i>key</i> if <i>key</i> is in the dictionary, "
            "else <i>default</i>.<br><br>"
            "<code>d = {'a': 1}; d.get('b', 42)  # returns 42</code>"
        ),
        icon="fa5s.book",
        shortcut="Ctrl+Q",
        target=btn_simple,
        parent=widget,
    )


btn_simple = hp.make_btn(widget, "Simple Docs Tooltip", func=_show_simple)
layout.addWidget(btn_simple)


def _show_rich() -> None:
    QtRichToolTip.show_tooltip(
        title="QtRichToolTip Widget",
        content=(
            "A <b>PyCharm-inspired</b> tooltip that supports:<br>"
            "<ul>"
            "<li>Rich <b>HTML</b> formatting</li>"
            "<li>Images and animated GIFs</li>"
            '<li>Clickable <a href="https://doc.qt.io">hyperlinks</a></li>'
            "<li>Action buttons in a footer</li>"
            "</ul>"
            "Use it anywhere you need a polished documentation popup."
        ),
        icon="fa5s.info-circle",
        actions=[
            RichToolTipAction(label="Learn More", callback=lambda: print("Learn more")),
            RichToolTipAction(label="View Source", object_name="success_btn"),
        ],
        target=btn_rich,
        parent=widget,
    )


btn_rich = hp.make_btn(widget, "Rich Tooltip + Actions", func=_show_rich)
layout.addWidget(btn_rich)


def _show_timed() -> None:
    QtRichToolTip.show_tooltip(
        title="Auto-dismiss",
        content="This tooltip will disappear in <b>3 seconds</b>.",
        icon="fa5s.clock",
        duration=3000,
        target=btn_timed,
        parent=widget,
    )


btn_timed = hp.make_btn(widget, "Timed Tooltip (3s)", func=_show_timed)
layout.addWidget(btn_timed)


def _show_from_model() -> None:
    data = RichToolTipData(
        title="From Model",
        content="Created via <code>RichToolTipData</code> Pydantic model.",
        icon="fa5s.database",
        actions=[RichToolTipAction(label="OK")],
    )
    QtRichToolTip.show_from_data(data, target=btn_model, parent=widget)


btn_model = hp.make_btn(widget, "From Pydantic Model", func=_show_from_model)
layout.addWidget(btn_model)


def _show_cursor() -> None:
    QtRichToolTip.show_tooltip(
        title="Cursor Tooltip",
        content="This tooltip appears at the <b>cursor position</b> rather than anchored to a widget.",
        icon="fa5s.mouse-pointer",
        duration=4000,
    )


btn_cursor = hp.make_btn(widget, "Cursor Tooltip", func=_show_cursor)
layout.addWidget(btn_cursor)


def _show_signature() -> None:
    QtRichToolTip.show_tooltip(
        title="add_widget",
        content=(
            "<code>"
            "def <b>add_widget</b>(<br>"
            "&nbsp;&nbsp;&nbsp;&nbsp;self,<br>"
            "&nbsp;&nbsp;&nbsp;&nbsp;name: <i>str</i>,<br>"
            "&nbsp;&nbsp;&nbsp;&nbsp;tooltip: <i>str</i> = <span style='color:#6a9955;'>\"\"</span>,<br>"
            "&nbsp;&nbsp;&nbsp;&nbsp;widget: <i>QWidget | None</i> = None,<br>"
            "&nbsp;&nbsp;&nbsp;&nbsp;location: <i>str</i> = <span style='color:#6a9955;'>\"top\"</span>,<br>"
            ") -> <i>QtToolbarPushButton</i>"
            "</code><br><br>"
            "Add a toolbar button and optionally bind it to a panel widget.<br><br>"
            "<b>Parameters:</b><br>"
            "&nbsp;&nbsp;<code>name</code> \u2013 name of the object used to select the icon<br>"
            "&nbsp;&nbsp;<code>tooltip</code> \u2013 text for the tooltip information<br>"
            "&nbsp;&nbsp;<code>widget</code> \u2013 widget inserted into the stack<br>"
            "&nbsp;&nbsp;<code>location</code> \u2013 <code>top</code> or <code>bottom</code>"
        ),
        icon="fa5s.code",
        shortcut="Ctrl+P",
        actions=[
            RichToolTipAction(label="View Source", callback=lambda: print("Navigate to source")),
        ],
        target=btn_sig,
        parent=widget,
    )


btn_sig = hp.make_btn(widget, "Signature Tooltip", func=_show_signature)
layout.addWidget(btn_sig)

layout.addStretch()
widget.show()

app.exec_()
