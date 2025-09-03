import sys

from qtpy.QtCore import Qt
from qtpy.QtGui import QFontMetrics
from qtpy.QtWidgets import QApplication, QComboBox, QStyle, QStyleOptionComboBox, QStylePainter


class QtElideComboBox(QComboBox):
    """A QComboBox that elides (truncates) long text with '...'."""

    def paintEvent(self, event):
        painter = QStylePainter(self)
        option = QStyleOptionComboBox()
        self.initStyleOption(option)

        # Calculate the available width for text (subtract some space for the arrow).
        text_width = self.width() - 20
        if text_width < 0:
            text_width = 0

        # Use self.font() (instead of option.font) to create the QFontMetrics.
        font_metrics = QFontMetrics(self.font())

        # Elide/truncate the combo box's current text if it's too long.
        elided_text = font_metrics.elidedText(option.currentText, Qt.TextElideMode.ElideRight, text_width)
        option.currentText = elided_text

        # Draw the combo box (frame and arrow).
        painter.drawComplexControl(QStyle.ComplexControl.CC_ComboBox, option)
        # Draw the truncated text.
        painter.drawControl(QStyle.ControlElement.CE_ComboBoxLabel, option)


if __name__ == "__main__":  # pragma: no cover
    app = QApplication(sys.argv)
    combo = QtElideComboBox()
    combo.addItems(
        [
            "Short text",
            "This is a very long text that likely needs truncation",
            "Another extremely long text example to demonstrate ellipses…",
        ]
    )
    combo.setEditable(False)
    combo.show()
    sys.exit(app.exec_())
