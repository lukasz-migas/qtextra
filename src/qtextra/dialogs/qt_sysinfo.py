"""System info dialog."""

from __future__ import annotations

from koyo.path import open_directory_alt
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QDialog, QHBoxLayout, QLabel, QTextBrowser, QTextEdit, QVBoxLayout, QWidget

from qtextra.widgets.qt_button_clipboard import QtCopyToClipboardButton


class QtSystemInfo(QDialog):
    """Qt dialog window for displaying 'About {APP}}' information.

    Parameters
    ----------
    parent : QWidget, optional
        Parent of the dialog, to correctly inherit and apply theme.
        Default is None.

    Attributes
    ----------
    citationCopyButton : napari._qt.qt_about.QtCopyToClipboardButton
        Button to copy citation information to the clipboard.
    citationTextBox : qtpy.QtWidgets.QTextEdit
        Text box containing napari citation information.
    citation_layout : qtpy.QtWidgets.QHBoxLayout
        Layout widget for napari citation information.
    infoCopyButton : napari._qt.qt_about.QtCopyToClipboardButton
        Button to copy napari version information to the clipboard.
    info_layout : qtpy.QtWidgets.QHBoxLayout
        Layout widget for napari version information.
    infoTextBox : qtpy.QtWidgets.QTextEdit
        Text box containing napari version information.
    layout : qtpy.QtWidgets.QVBoxLayout
        Layout widget for the entire 'About napari' dialog.
    """

    def __init__(self, system_info: str, citation_info: str, title: str = "", parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)

        self._layout = QVBoxLayout(self)
        self._layout.setSpacing(2)
        self._layout.setContentsMargins(5, 5, 5, 5)

        # Description
        title_label = QLabel(title)
        title_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self._layout.addWidget(title_label)

        # Add information
        self.infoTextBox = QTextBrowser(self)
        self.infoTextBox.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.infoTextBox.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.infoTextBox.setOpenLinks(True)
        self.infoTextBox.setOpenExternalLinks(True)
        self.infoTextBox.anchorClicked.connect(open_directory_alt)

        # Add text copy button
        self.infoCopyButton = QtCopyToClipboardButton(self.infoTextBox)
        self.infoCopyButton.set_medium()
        self.info_layout = QHBoxLayout()
        self.info_layout.addWidget(self.infoTextBox, 1)
        self.info_layout.addWidget(self.infoCopyButton, 0, Qt.AlignmentFlag.AlignTop)
        self.info_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._layout.addWidget(QLabel("<b>System information:</b>"))
        self._layout.addLayout(self.info_layout)

        self.infoTextBox.setText(system_info)
        self.infoTextBox.setMinimumSize(
            int(self.infoTextBox.document().size().width() + 19),
            int(min(self.infoTextBox.document().size().height() + 10, 500)),
        )

        self._layout.addWidget(QLabel("<b>Citation information:</b>"))
        self.citationTextBox = QTextEdit(citation_info)
        self.citationTextBox.setFixedHeight(64)
        self.citationCopyButton = QtCopyToClipboardButton(self.citationTextBox)
        self.citationCopyButton.set_medium()
        self.citation_layout = QHBoxLayout()
        self.citation_layout.addWidget(self.citationTextBox, 1)
        self.citation_layout.addWidget(self.citationCopyButton, 0, Qt.AlignmentFlag.AlignTop)
        self._layout.addLayout(self.citation_layout)

        self.resize(600, 400)

    @staticmethod
    def show_sys_info(
        system_info: str, citation_info: str, title: str = "System Information", parent: QWidget | None = None
    ) -> None:
        """Display the 'About napari' dialog box.

        Parameters
        ----------
        system_info : str
            Text containing system information.
        citation_info : str
            Text containing citation information.
        title : str
            Title of the dialog.
        parent : QWidget, optional
            Parent of the dialog, to correctly inherit and apply theme.
            Default is None.
        """
        d = QtSystemInfo(system_info, citation_info, title=title, parent=parent)
        d.setObjectName("DialogSystemInfo")
        d.setWindowTitle(title)
        d.setWindowModality(Qt.WindowModality.ApplicationModal)
        d.exec_()


if __name__ == "__main__":  # pragma: no cover

    def _main():  # type: ignore[no-untyped-def]
        import sys

        from qtextra.config import THEMES
        from qtextra.utils.dev import qapplication

        _ = qapplication()  # analysis:ignore
        dlg = QtSystemInfo("TEST", "TEST", None)
        THEMES.set_theme_stylesheet(dlg)
        dlg.show()
        sys.exit(dlg.exec_())

    _main()  # type: ignore[no-untyped-call]
