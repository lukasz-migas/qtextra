from qtpy.QtCore import Qt
from qtpy.QtGui import QMouseEvent
from qtpy.QtWidgets import QHBoxLayout, QLabel, QWidget

from qtextra.widgets.qt_line import QtHorzLine


class QReadMoreLessLabel(QWidget):
    """Read more/less label."""

    def __init__(self, parent, text: str):
        QWidget.__init__(self, parent)

        self.text = text
        self.readmore = False

        # Explanation text
        self.explanation_layout = QHBoxLayout()
        self.explanation_layout.setAlignment(Qt.AlignTop)
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
        self.explanation_text_left.setTextFormat(Qt.RichText)
        self.explanation_layout.addWidget(self.explanation_text_left, 50)

        # Vertical Line Break
        self.vertical_break = QtHorzLine(self)
        self.explanation_layout.addWidget(self.vertical_break)

        self.explanation_text_right = QLabel(text_right, self)
        self.explanation_text_right.setWordWrap(True)
        self.explanation_text_right.setTextFormat(Qt.RichText)
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
    Now it is time to denoise the previously selected and cropped images.
    <br><br>
    Some info
    <moreless>
    Some more text
    <split>
    Even some more text
    """

    def _main():
        import sys
        from random import choice

        from qtextra.config import THEMES
        from qtextra.helpers import make_btn
        from qtextra.utils.dev import qmain

        def _toggle_theme():
            THEMES.theme = choice(THEMES.available_themes())
            THEMES.set_theme_stylesheet(frame)

        app, frame, ha = qmain(False)
        frame.setMinimumSize(600, 600)

        wdg = make_btn(frame, "Click here to toggle theme")
        wdg.clicked.connect(_toggle_theme)
        ha.addWidget(wdg)

        wdg = QReadMoreLessLabel(parent=frame, text=_make_text())
        ha.addWidget(wdg)

        frame.show()
        sys.exit(app.exec_())

    _main()
