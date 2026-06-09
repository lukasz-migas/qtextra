"""Buttons."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Callable

from qtpy import QtCore
from qtpy import QtWidgets as QtW


class QtComboButton(QtW.QToolButton):
    """QToolButton."""

    currentTextChanged = QtCore.Signal(str)

    def __init__(self, text: str = "", parent: QtW.QWidget | None = None) -> None:
        super().__init__(parent)
        self._choices: Callable[[], Iterable[str]] = list
        self.clicked.connect(self._on_clicked)
        self._title = ""
        self._message = ""
        self._formatter = "{}"
        self._current_text = ""
        self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.setCurrentText(text)

    def _on_clicked(self) -> None:
        from qtextra.widgets.qt_command_palette import choose_from_palette

        resp = choose_from_palette(
            title=self._title,
            message=self._message,
            options=self._choices(),
        )
        if resp is not None:
            self.setCurrentText(str(resp))
            self.currentTextChanged.emit(str(resp))

    def currentText(self) -> str:
        """Return the current text."""
        return self._current_text

    def setCurrentText(self, text: str) -> None:
        """Set the current text."""
        self.setText(self._formatter.format(text))
        self._current_text = text

    def setTitle(self, title: str) -> None:
        """Set the title."""
        self._title = title

    def setMessage(self, message: str) -> None:
        """Set the message."""
        self._message = message

    def setFormatter(self, formatter: str) -> None:
        """Set the formatter."""
        self._formatter = formatter
        self.setCurrentText(self._current_text)

    def setChoices(self, choices: Iterable[str] | Callable[[], Iterable[str]]) -> None:
        """Set the choices."""
        if callable(choices):
            self._choices = choices
        else:
            self._choices = lambda: choices


if __name__ == "__main__":  # pragma: no cover
    import sys

    from qtextra.utils.dev import qframe

    app, frame, va = qframe(False)
    frame.setMinimumSize(500, 200)

    # No actions - plain main button
    btn4 = QtComboButton("No actions", frame)
    btn4.setChoices(
        ["Apple", "Apricot", "Banana", "Blueberry", "Cherry", "Cranberry", "Grape", "Guava", "Lemon", "Lime"]
    )
    va.addWidget(btn4)

    frame.show()
    sys.exit(app.exec_())
