"""Info widget."""

from qtpy.QtCore import Qt
from qtpy.QtWidgets import QFormLayout, QPlainTextEdit, QWidget

import qtextra.helpers as hp
from qtextra.widgets.qt_dialog import QtFramelessPopup


class InfoDialog(QtFramelessPopup):
    """Dialog to display some useful information."""

    def __init__(
        self,
        parent: QWidget,
        text: str,
        title: str = "Help information",
        min_width: int = 300,
        min_height: int = 200,
        persist: bool = False,
        quick: bool = False,
    ):
        self._title = title
        self.persist = persist
        self.quick = quick
        kws = {}
        if persist:
            kws = {"flags": Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool}
        super().__init__(parent, **kws)
        self.setMinimumWidth(min_width)
        self.setMinimumHeight(min_height)
        if self.quick:
            self.label.appendHtml(text)
            self.on_scroll_to_top()
        else:
            self.label.setText(text)

    def on_scroll_to_top(self) -> None:
        """Scroll to end."""
        self.label.verticalScrollBar().setValue(self.label.verticalScrollBar().minimum())

    def on_scroll_to_end(self) -> None:
        """Scroll to end."""
        self.label.verticalScrollBar().setValue(self.label.verticalScrollBar().maximum())

    # noinspection PyAttributeOutsideInit
    def make_panel(self) -> QFormLayout:
        """Make panel."""
        if self.persist:
            _, header_layout = self._make_close_handle(self._title)
        else:
            header_layout = self._make_title_handle(self._title)

        layout = hp.make_form_layout(parent=self, margin=2)
        layout.addRow(header_layout)

        if self.quick:
            self.label = QPlainTextEdit()
            layout.addRow(
                hp.make_h_layout(
                    hp.make_btn(self, "Scroll to top", func=self.on_scroll_to_top),
                    hp.make_btn(self, "Scroll to end", func=self.on_scroll_to_end),
                    stretch_after=True,
                )
            )
        else:
            self.label = hp.make_scrollable_label(
                self, wrap=True, enable_url=True, selectable=True, object_name="title_label"
            )

        layout.addRow(self.label)
        return layout


if __name__ == "__main__":
    import sys

    from qtextra.utils.dev import apply_style, qapplication

    _ = qapplication()  # analysis:ignore

    dlg = InfoDialog(None, "This is a test message.<br>" * 50, persist=True, quick=True)
    apply_style(dlg)
    dlg.show()
    sys.exit(dlg.exec_())
