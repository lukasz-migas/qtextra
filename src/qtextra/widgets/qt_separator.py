"""Horizontal and Vertical lines."""

import typing as ty

from qtpy.QtWidgets import QFrame, QWidget

import qtextra.helpers as hp

# TODO: the vertical line with text is currently not looking great since the label is not properly rotated


class QtHorzLine(QFrame):
    """Horizontal line."""

    def __init__(self, parent: QWidget):
        super().__init__(parent=parent)
        self.setFrameShape(QFrame.Shape.HLine)
        self.setFrameShadow(QFrame.Shadow.Plain)


class QtHorzLineWithText(QWidget):
    """Horizontal line with text."""

    def __init__(self, parent: QWidget, label: str, bold: bool = False, position: str = "center", **kwargs: ty.Any):
        super().__init__(parent=parent)

        self.label = hp.make_label(parent, label, bold=bold, **kwargs)
        if position == "center":
            widgets = (QtHorzLine(parent), self.label, QtHorzLine(parent))
            stretch_ids = (0, 2)
        elif position == "left":
            widgets = (self.label, QtHorzLine(parent))
            stretch_ids = (1,)
        else:
            widgets = (QtHorzLine(parent), self.label)
            stretch_ids = (0,)
        hp.make_h_layout(*widgets, stretch_id=stretch_ids, spacing=2, margin=1, parent=self)

    def setText(self, text: str) -> None:
        """Set text of the label."""
        self.label.setText(text)


class QtVertLine(QFrame):
    """Vertical line."""

    def __init__(self, parent: QWidget):
        super().__init__(parent=parent)
        self.setFrameShape(QFrame.Shape.VLine)
        self.setFrameShadow(QFrame.Shadow.Plain)


class QtVertLineWithText(QWidget):
    """Vertical line with text."""

    def __init__(self, parent: QWidget, label: str, bold: bool = False, position: str = "center", **kwargs: ty.Any):
        super().__init__(parent=parent)

        self.label = hp.make_label(parent, label, bold=bold, vertical=True, **kwargs)
        if position == "center":
            widgets = (QtVertLine(parent), self.label, QtVertLine(parent))
            stretch_ids = (0, 2)
        elif position == "left":
            widgets = (self.label, QtVertLine(parent))
            stretch_ids = (1,)
        else:
            widgets = (QtVertLine(parent), self.label)
            stretch_ids = (0,)
        hp.make_v_layout(
            *widgets,
            stretch_id=stretch_ids,
            spacing=2,
            margin=1,
            parent=self,
        )


if __name__ == "__main__":  # pragma: no cover
    import sys

    from qtextra.utils.dev import qframe

    app, frame, ha = qframe(False, dev=True)
    frame.setMinimumSize(600, 600)

    ha.addWidget(QtHorzLineWithText(frame, "Test 1"))
    ha.addWidget(QtVertLineWithText(frame, "Test 1"))

    frame.show()
    sys.exit(app.exec_())
