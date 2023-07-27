"""Toast."""
from contextlib import suppress

from qtpy.QtCore import QTimer, Qt
from qtpy.QtWidgets import QHBoxLayout, QProgressBar, QVBoxLayout, QWidget

import qtextra.helpers as hp
from qtextra.widgets.qt_dialog import SubWindowBase
from qtextra.widgets.qt_icon_label import QtSeverityLabel


class QtToast(SubWindowBase):
    """Small popup notification that can contain actions."""

    # Animation attributes
    POSITION = "top_right"
    DISMISS_AFTER = 5000
    MAX_OPACITY = 1.0

    def __init__(self, parent=None):
        super().__init__(parent)

        self.timer_dismiss = QTimer()
        self.timer_remaining = QTimer()

        self.make_ui()
        if hasattr(parent, "evt_resized"):
            parent.evt_resized.connect(lambda: self.move_to(self.POSITION))

    # noinspection PyAttributeOutsideInit
    def make_ui(self):
        """Setup UI."""
        title_widget = QWidget()
        # title_widget.setMaximumHeight(30)
        title_widget.setObjectName("toast_header")
        self._icon_label = QtSeverityLabel(title_widget)
        self._icon_label.setMaximumWidth(20)
        self._icon_label.setMinimumHeight(20)
        self._title_label = hp.make_label(title_widget, "", bold=True)
        self._date_label = hp.make_label(title_widget, "")
        self._close_btn = hp.make_qta_btn(title_widget, "cross", small=True, medium=False, func=self.close)

        self._message_label = hp.make_label(self, "", wrap=True, enable_url=True)

        self._timer_indicator = QProgressBar(self)
        self._timer_indicator.setObjectName("progress_timer")
        self._timer_indicator.setTextVisible(False)

        title_layout = QHBoxLayout(title_widget)
        hp.set_layout_margin(title_layout, 2)
        title_layout.addWidget(self._icon_label, alignment=Qt.AlignVCenter)
        title_layout.addWidget(self._title_label, stretch=True, alignment=Qt.AlignVCenter)
        title_layout.addWidget(self._date_label, alignment=Qt.AlignVCenter)
        title_layout.addStretch(1)
        title_layout.addWidget(self._close_btn, alignment=Qt.AlignVCenter)

        # layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(title_widget)
        layout.addWidget(self._message_label, stretch=True)
        layout.addStretch(1)
        layout.addWidget(self._timer_indicator)

    def show_message(self, title: str, message: str, icon: str = "info", position: str = "top_right"):
        """Show message."""
        self.POSITION = position
        self._title_label.setText(title)
        self._message_label.setText(message)
        self._icon_label.severity = str(icon)
        self.adjustSize()
        self.move_to(self.POSITION)
        self.show()

    def show_long_message(
        self, title: str, message: str, duration: int = 5000, position: str = "top_right", icon: str = "info"
    ):
        """Show message that appears for longer but is also longer in time."""
        self.DISMISS_AFTER = duration
        self.POSITION = position
        self.show_message(title, message, icon=icon)

    def show(self):
        """Show the message with a fade and slight slide in from the bottom."""

        def _update_timer_indicator():
            with suppress(RuntimeError):
                self._timer_indicator.setValue(self.timer_dismiss.remainingTime() / self.DISMISS_AFTER * 100)

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

    def mouseMoveEvent(self, event):
        """On hover, stop the self-destruct timer."""
        self.timer_dismiss.stop()
        self.timer_remaining.stop()
        self._timer_indicator.setVisible(False)
        return super().mouseMoveEvent(event)


if __name__ == "__main__":  # pragma: no cover

    def _main():
        import sys
        from random import choice

        from qtextra.config import THEMES
        from qtextra.utils.dev import qframe

        def _popup_notif():
            pop = QtToast(frame)
            THEMES.set_theme_stylesheet(pop)
            # pop.show_message("Title", "Here is a message..")
            pop.show_message("Title", "Here is a message.\nA couple of lines long.\nAnother line")

        def _popup_notif2():
            pop = QtToast(frame)
            THEMES.set_theme_stylesheet(pop)
            pop.show_long_message(
                "Title",
                (
                    "You can easily move images around by clicking inside the image and moving it left-right and"
                    "up-down.\nRotation is currently disabled and changes to scale and shearing will not be supported."
                ),
            )

        def _toggle_theme():
            THEMES.theme = choice(THEMES.available_themes())
            THEMES.set_theme_stylesheet(frame)

        def _reload_theme():
            from qtextra.assets import get_stylesheet

            get_stylesheet.cache_clear()
            THEMES.set_theme_stylesheet(frame)

        #
        app, frame, ha = qframe(False)
        frame.setMinimumSize(600, 600)

        btn2 = hp.make_btn(frame, "Create random notification")
        btn2.clicked.connect(_popup_notif)
        ha.addWidget(btn2)
        btn2 = hp.make_btn(frame, "Create long notification")
        btn2.clicked.connect(_popup_notif2)
        ha.addWidget(btn2)
        btn2 = hp.make_btn(frame, "Click me to toggle theme")
        btn2.clicked.connect(_toggle_theme)
        ha.addWidget(btn2)
        btn2 = hp.make_btn(frame, "Click me to reload theme")
        btn2.clicked.connect(_reload_theme)
        ha.addWidget(btn2)
        ha.addStretch(1)

        frame.show()
        sys.exit(app.exec_())

    _main()
