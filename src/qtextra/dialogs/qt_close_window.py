"""Close dialog with option to not ask again."""

from __future__ import annotations

import typing as ty

from koyo.system import IS_PYINSTALLER, IS_WIN
from qtpy.QtGui import QKeySequence
from qtpy.QtWidgets import QDialog, QHBoxLayout, QVBoxLayout, QWidget

import qtextra.helpers as hp


class QtConfirmCloseDialog(QDialog):
    """Confirm close dialog with an option to not ask again."""

    def __init__(
        self,
        parent: QWidget,
        attr: str | None = None,
        save_func: ty.Callable | None = None,
        config: ty.Optional[object] = None,
        no_icon: bool = False,
    ) -> None:
        super().__init__(parent)
        self.attr = attr
        self.config = config
        self.save_func = save_func

        if (IS_PYINSTALLER and IS_WIN) or no_icon:
            cancel_btn = hp.make_btn(self, "Cancel", tooltip="Cancel and return to the app.")
            save_btn = hp.make_btn(self, "Save", tooltip="Save and close the app.")
            close_btn = hp.make_btn(self, "Close", tooltip="Close the app.", properties={"type": "error"})
        else:
            cancel_btn = hp.make_qta_btn(
                self, "cancel", label="Cancel", standout=True, tooltip="Cancel and return to the app."
            )
            save_btn = hp.make_qta_btn(self, "save", label="Save", standout=True, tooltip="Save and close the app.")
            close_btn = hp.make_qta_btn(
                self, "warning", color="orange", label="Close", standout=True, tooltip="Close the app."
            )

        icon_label = hp.make_qta_label(self, "warning", color="orange")
        icon_label.set_xxxlarge()

        self.do_not_ask = hp.make_checkbox(self, "Do not ask in future")

        self.setWindowTitle("Close Application?")
        shortcut = QKeySequence("Ctrl+Q").toString(QKeySequence.SequenceFormat.NativeText)
        text = (
            f"Do you want to close the application? There might be some <b>unsaved</b> changes."
            f"<br><br>(<b>{shortcut}</b> to confirm)."
        )
        close_btn.setShortcut(QKeySequence("Ctrl+Q"))

        if callable(save_func):
            save_btn.clicked.connect(self.save_and_accept)
        else:
            save_btn.hide()
        cancel_btn.clicked.connect(self.reject)
        close_btn.clicked.connect(self.accept)

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(close_btn)
        btn_layout.addStretch(1)
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)

        body_layout = QVBoxLayout()
        body_layout.addWidget(hp.make_label(self, text, enable_url=True, wrap=True))
        body_layout.addWidget(self.do_not_ask)
        body_layout.addLayout(btn_layout)

        icon_layout = QHBoxLayout(self)
        icon_layout.addWidget(icon_label)
        icon_layout.addLayout(body_layout)

        # for test purposes because of the problem with shortcut testing:
        # https://github.com/pytest-dev/pytest-qt/issues/254
        self.close_btn = close_btn
        self.cancel_btn = cancel_btn

    def save_and_accept(self):
        """Save and accept."""
        if callable(self.save_func):
            self.save_func()
        return self.accept()

    def accept(self):
        """Accept."""
        if self.do_not_ask.isChecked():
            if self.config and self.attr is not None:
                setattr(self.config, self.attr, False)
        return super().accept()


if __name__ == "__main__":  # pragma: no cover
    from qtextra.utils.dev import apply_style, qapplication

    app = qapplication()
    dlg = QtConfirmCloseDialog(None, no_icon=True)
    apply_style(dlg)
    dlg.exec_()
