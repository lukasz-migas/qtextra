"""Button that copies contents of QTextEdit to the clipboard."""

from qtpy.QtGui import QGuiApplication, QImage
from qtpy.QtWidgets import QTextEdit

from qtextra.config import EVENTS, THEMES
from qtextra.widgets.qt_button_icon import QtImagePushButton


def copy_text_to_clipboard(text: str):
    """Helper function to easily copy text to clipboard while notifying the user."""
    cb = QGuiApplication.clipboard()
    cb.setText(text)
    EVENTS.evt_msg_success.emit("Copied text to clipboard!")


def copy_image_to_clipboard(image: QImage):
    """Helper function to easily copy image to clipboard while notifying the user."""
    cb = QGuiApplication.clipboard()
    cb.setImage(image)
    EVENTS.evt_msg_success.emit("Copied image to clipboard!")


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

    def __init__(self, text_edit: QTextEdit):
        super().__init__()
        self.setObjectName("QtCopyToClipboardButton")
        self.text_edit = text_edit
        self.setToolTip("Copy to clipboard")
        self.set_qta("copy_to_clipboard")
        self.clicked.connect(self.copy_to_clipboard)

    def copy_to_clipboard(self) -> None:
        """Copy text to the clipboard."""
        from qtextra.helpers import add_flash_animation

        copy_text_to_clipboard(str(self.text_edit.toPlainText()))
        add_flash_animation(self.text_edit, color=THEMES.get_hex_color("foreground"), duration=500)

    # Alias methods to offer Qt-like interface
    copyToClipboard = copy_to_clipboard
