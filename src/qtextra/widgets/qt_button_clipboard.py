"""Button that copies contents of QTextEdit to the clipboard."""

from qtpy.QtGui import QGuiApplication, QImage

from qtextra.config.theme import THEMES
from qtextra.widgets.qt_button_icon import QtImagePushButton


def copy_text_to_clipboard(text: str):
    """Helper function to easily copy text to clipboard while notifying the user."""
    cb = QGuiApplication.clipboard()
    cb.setText(text)


def copy_image_to_clipboard(image: QImage):
    """Helper function to easily copy image to clipboard while notifying the user."""
    cb = QGuiApplication.clipboard()
    cb.setImage(image)


class QtCopyToClipboardButton(QtImagePushButton):
    """Button to copy text box information to the clipboard.

    Parameters
    ----------
    text_edit : qtpy.QtWidgets.QTextEdit
        The text box contents linked to copy to clipboard button.

    Attributes
    ----------
    text_edit : qtpy.QtWidgets.QTextEdit
        The text box contents linked to copy to clipboard button.
    """

    def __init__(self, text_edit):
        super().__init__()
        self.setObjectName("QtCopyToClipboardButton")
        self.text_edit = text_edit
        self.setToolTip("Copy to clipboard")
        self.set_qta("copy_to_clipboard")
        self.clicked.connect(self.copy_to_clipboard)

    def copy_to_clipboard(self):
        """Copy text to the clipboard."""
        from qtextra.helpers import add_flash_animation

        copy_text_to_clipboard(str(self.text_edit.toPlainText()))
        add_flash_animation(self.text_edit, color=THEMES.get_hex_color("foreground"), duration=500)
