"""Eliding label."""
from qtpy.QtCore import Qt
from superqt import QElidingLabel


class QtElidingLabel(QElidingLabel):
    """A single-line eliding QLabel."""

    def __init__(
        self,
        text="",
        bold: bool = False,
        parent=None,
        elide: Qt.TextElideMode = Qt.ElideMiddle,
        multiline: bool = False,
    ):
        super().__init__(text, parent=parent)
        self.setElideMode(elide)
        self.setWordWrap(multiline)
        font = self.font()
        font.setBold(bold)
        self.setFont(font)

    def full_text(self) -> str:
        """Get full text."""
        return self._text


if __name__ == "__main__":  # pragma: no cover

    def _main():  # pragma: no cover
        import sys

        from qtextra._dev_tools import qframe

        app, frame, ha = qframe()
        widget = QtElidingLabel(
            parent=frame,
            text="This is a lot of text that should be cut because its way too long for such a short label",
            multiline=True,
        )

        ha.addWidget(widget)
        frame.show()
        sys.exit(app.exec_())

    _main()
