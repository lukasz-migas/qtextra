from qtpy.QtCore import Qt
from qtpy.QtGui import QMouseEvent
from qtpy.QtWidgets import QHBoxLayout, QLabel, QWidget

from qtextra.widgets.qt_separator import QtHorzLine


class QReadMoreLessLabel(QWidget):
    """Read more/less label."""

    def __init__(self, parent, text: str):
        QWidget.__init__(self, parent)

        self.text = text
        self.readmore = False

        # Explanation text
        self.explanation_layout = QHBoxLayout()
        self.explanation_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.mousePressEvent = self.state_toggle

        if "<moreless>" in text:
            self.readless_text, self.readmore_text = text.split("<moreless>")
            self.readmore_text = text
            self.readmore_left, self.readmore_right = self.readmore_text.split("<split>")
            text_left = self.readless_text + ("" if self.readmore_right.strip() == "" else "<b>Read more...</b>")
            text_right = ""
        else:
            text_left, text_right = text.split("<split>")

        self.explanation_text_left = QLabel(text_left, self)
        self.explanation_text_left.setWordWrap(True)
        self.explanation_text_left.setTextFormat(Qt.TextFormat.RichText)
        self.explanation_layout.addWidget(self.explanation_text_left, 50)

        # Vertical Line Break
        self.vertical_break = QtHorzLine(self)
        self.explanation_layout.addWidget(self.vertical_break)

        self.explanation_text_right = QLabel(text_right, self)
        self.explanation_text_right.setWordWrap(True)
        self.explanation_text_right.setTextFormat(Qt.TextFormat.RichText)
        self.explanation_layout.addWidget(self.explanation_text_right, 50)

        if self.readmore_text is not None and self.readmore_text.strip() == "":
            self.vertical_break.setHidden(True)
            self.explanation_text_right.setHidden(True)

        self.setLayout(self.explanation_layout)

    def state_toggle(self, a0: QMouseEvent) -> None:
        if self.readmore_text is not None and self.readmore_right.strip() != "":
            self.readmore = not self.readmore
            if self.readmore:
                self.explanation_text_left.setText(self.readmore_left)
                self.explanation_text_right.setText(self.readmore_right + "<b>Read less...</b>")
            else:
                self.explanation_text_left.setText(self.readless_text + "<b>Read more...</b>")
                self.explanation_text_right.setText("")


if __name__ == "__main__":  # pragma: no cover

    def _make_text():
        return """
    You can use this widget to create a label that can be expanded or collapsed.
    <br><br>
    Some info which can take a little bit of space
    <moreless>
    Some more text that will be hidden
    <split>
    Even some more text and even more text
    """

    def _main():  # type: ignore[no-untyped-def]
        import sys

        from qtextra.utils.dev import qframe

        app, frame, ha = qframe(False)
        frame.setMinimumSize(600, 600)

        wdg = QReadMoreLessLabel(parent=frame, text=_make_text())
        ha.addWidget(wdg)

        frame.show()
        sys.exit(app.exec_())

    _main()
