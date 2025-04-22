"""Toast."""

from __future__ import annotations

from contextlib import suppress

from qtpy.QtCore import Qt, QTimer
from qtpy.QtGui import QMouseEvent
from qtpy.QtWidgets import QProgressBar, QWidget

import qtextra.helpers as hp
from qtextra.widgets.qt_dialog import SubWindowBase
from qtextra.widgets.qt_label_icon import QtSeverityLabel


class QtToast(SubWindowBase):
    """Small popup notification that can contain actions."""

    # Animation attributes
    POSITION = "top_right"
    DISMISS_AFTER = 5000
    MAX_OPACITY = 1.0

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)

        self.timer_dismiss = QTimer()
        self.timer_remaining = QTimer()

        self.make_ui()
        if hasattr(parent, "evt_resized"):
            parent.evt_resized.connect(lambda: self.move_to(self.POSITION))

    # noinspection PyAttributeOutsideInit
    def make_ui(self) -> None:
        """Setup UI."""
        title_widget = QWidget()
        title_widget.setObjectName("toast_header")

        self._icon_label = QtSeverityLabel(title_widget)
        self._icon_label.set_xsmall()

        self._title_label = hp.make_label(title_widget, "", bold=True, object_name="transparent")
        hp.set_expanding_sizer_policy(self._title_label, True, False)

        self._date_label = hp.make_label(title_widget, "", object_name="transparent")

        self._close_btn = hp.make_qta_btn(title_widget, "cross", func=self.close)
        self._close_btn.set_xsmall()

        self._message_label = hp.make_label(self, "", wrap=True, enable_url=True)

        title_layout = hp.make_h_layout(parent=title_widget, margin=2, spacing=1)
        title_layout.addWidget(self._icon_label, alignment=Qt.AlignmentFlag.AlignVCenter)
        title_layout.addWidget(self._title_label, stretch=True, alignment=Qt.AlignmentFlag.AlignVCenter)
        title_layout.addWidget(self._date_label, alignment=Qt.AlignmentFlag.AlignVCenter)
        title_layout.addStretch(1)
        title_layout.addWidget(self._close_btn, alignment=Qt.AlignmentFlag.AlignTop)

        self._timer_indicator = QProgressBar(self)
        self._timer_indicator.setObjectName("progress_timer")
        self._timer_indicator.setTextVisible(False)

        # layout
        layout = hp.make_v_layout(parent=self, margin=0, spacing=0)
        layout.addWidget(title_widget)
        layout.addWidget(self._message_label, stretch=True)
        layout.addStretch(1)
        layout.addWidget(self._timer_indicator)

    def show_message(
        self, title: str, message: str, icon: str = "info", position: str = "top_right", duration: int = 5000
    ) -> None:
        """Show message."""
        self.POSITION = position
        self.DISMISS_AFTER = duration
        self._title_label.setText(title)
        self._title_label.adjustSize()
        self._message_label.setText(message)
        self._message_label.adjustSize()
        self._icon_label.severity = str(icon)
        self.adjustSize()
        self.move_to(self.POSITION)
        self.show()

    def show(self) -> None:
        """Show the message with a fade and slight slide in from the bottom."""

        def _update_timer_indicator() -> None:
            with suppress(RuntimeError):
                self._timer_indicator.setValue(int(self.timer_dismiss.remainingTime() / self.DISMISS_AFTER * 100))

        super().show()
        self.slide_in()
        if self.DISMISS_AFTER > 0:
            self.timer_dismiss.setInterval(self.DISMISS_AFTER)
            self.timer_dismiss.setSingleShot(True)
            self.timer_dismiss.timeout.connect(self.close)
            self.timer_dismiss.timeout.connect(self.timer_remaining.stop)
            self.timer_dismiss.start()

            self.timer_remaining.setInterval(50)
            self.timer_remaining.setSingleShot(False)
            self.timer_remaining.timeout.connect(_update_timer_indicator)
            self.timer_remaining.start()

    def mouseMoveEvent(self, event: QMouseEvent | None) -> None:  # type: ignore[override]
        """On hover, stop the self-destruct timer."""
        self.timer_dismiss.stop()
        self.timer_remaining.stop()
        self._timer_indicator.setVisible(False)
        return super().mouseMoveEvent(event)

    def deleteLater(self) -> None:
        """Stop all animations and timers before deleting."""
        self.timer_dismiss.stop()
        self.timer_remaining.stop()
        super().deleteLater()

    def close(self):
        self.timer_dismiss.stop()
        self.timer_remaining.stop()
        SubWindowBase.close(self)


if __name__ == "__main__":  # pragma: no cover

    def _main():  # type: ignore[no-untyped-def]
        import sys
        from random import choice

        from qtextra.config import THEMES
        from qtextra.utils.dev import qframe

        def _popup_notif() -> None:
            pop = QtToast(frame)
            THEMES.set_theme_stylesheet(pop)
            # pop.show_message("Title", "Here is a message..")
            pop.show_message("Title", "Here is a message.\nA couple of lines long.\nAnother line")

        def _popup_notif3() -> None:
            from qtextra.helpers import toast_alt

            toast_alt(
                frame,
                "Title",
                "Here is a message.\nA couple of lines long.\nAnother line",
                icon=choice(["info", "warning", "error", "success"]),
            )

        def _popup_notif2() -> None:
            pop = QtToast(frame)
            THEMES.set_theme_stylesheet(pop)
            pop.show_message(
                "Title",
                (
                    "You can easily move images around by clicking inside the image and moving it left-right and"
                    "up-down.\nRotation is currently disabled and changes to scale and shearing will not be supported."
                ),
                duration=10000,
            )

        app, frame, ha = qframe(False, set_style=True)
        frame.setMinimumSize(600, 600)

        btn2 = hp.make_btn(frame, "Create random notification")
        btn2.clicked.connect(_popup_notif)
        ha.addWidget(btn2)
        btn2 = hp.make_btn(frame, "Create long notification")
        btn2.clicked.connect(_popup_notif2)
        ha.addWidget(btn2)
        btn2 = hp.make_btn(frame, "Create alternate notification")
        btn2.clicked.connect(_popup_notif3)
        ha.addWidget(btn2)
        ha.addWidget(btn2)
        ha.addStretch(1)

        frame.show()
        sys.exit(app.exec_())

    _main()
