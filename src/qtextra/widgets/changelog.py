"""Changelog dialog."""
import typing as ty

from qtpy.QtWidgets import QFormLayout, QTextEdit, QWidget

import qtextra.helpers as hp
from qtextra.config import THEMES
from qtextra.widgets.qt_code_widget import Codelighter
from qtextra.widgets.qt_dialog import QtFramelessTool


class ChangelogDialog(QtFramelessTool):
    """Changelog."""

    HIDE_WHEN_CLOSE = False

    def __init__(self, parent: ty.Optional[QWidget], text: str, language: str = "markdown") -> None:
        self.text = text
        self.language = language
        super().__init__(parent)
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)

    # noinspection PyAttributeOutsideInit
    def make_panel(self) -> QFormLayout:
        """Make panel."""
        self.text_edit = QTextEdit()
        self._highlight = Codelighter(self.text_edit.document(), THEMES.syntax_style, self.language)
        self.text_edit.setText(self.text)
        self.text_edit.setReadOnly(True)

        layout = hp.make_form_layout(self)
        layout.addRow(self._make_close_handle("Changelog")[1])
        layout.addWidget(self.text_edit)
        return layout
