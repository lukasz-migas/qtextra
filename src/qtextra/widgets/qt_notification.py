"""Alternative notification."""

from __future__ import annotations

import typing as ty
from contextlib import suppress
from functools import partial

from qtpy.QtCore import QEasingCurve, QRect, QSize, Qt, QThread, QTimer
from qtpy.QtWidgets import (
    QApplication,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QProgressBar,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
from superqt import ensure_main_thread
from superqt.utils import qthrottled

import qtextra.helpers as hp
from qtextra.config import EVENTS, THEMES, get_settings
from qtextra.utils.notifications import NOTIFICATION_LEVELS, ErrorNotification, Notification, NotificationSeverity
from qtextra.widgets.qt_button_icon import QtExpandButton
from qtextra.widgets.qt_dialog import QtFramelessPopup, SubWindowBase
from qtextra.widgets.qt_label_icon import QtSeverityLabel

ActionSequence = ty.Sequence[ty.Tuple[str, ty.Callable[[], None]]]


# TODO: This is currently broken since the settings.nottifications settings module is not present


class QtNotification(SubWindowBase):
    """Small popup notification that can contain actions."""

    MAX_OPACITY = 0.9
    FADE_IN_RATE = 220
    FADE_OUT_RATE = 120
    DISMISS_AFTER = 5000
    MIN_WIDTH = 400
    MIN_HEIGHT = 40
    BOTTOM_Y_OFFSET = 0
    MIN_EXPANSION = 18

    def __init__(
        self,
        message: str,
        severity: str | NotificationSeverity = NotificationSeverity.WARNING,
        source: str | None = None,
        actions: ActionSequence = (),
        is_bottom: bool = True,
        expanded: bool = True,
        auto_close: bool = True,
    ):
        super().__init__()
        # disable window decorations
        self.setMinimumWidth(self.MIN_WIDTH)
        self.setMaximumWidth(self.MIN_WIDTH)
        self.setMinimumHeight(self.MIN_HEIGHT)

        self.is_bottom = is_bottom
        # if the notification is not meant to automatically close, set the DISMISS_AFTER value to 0
        if not auto_close:
            self.DISMISS_AFTER = 0

        parent = None
        if parent is not None:
            self.setParent(parent)
        if hasattr(parent, "evt_window_resize"):
            self.parent().evt_window_resize.connect(
                self.move_to_bottom_right if self.is_bottom else self.move_to_top_right
            )
            self.BOTTOM_Y_OFFSET = parent.statusbar.height()

        self.timer = QTimer()
        self.timer_bar = QTimer()

        self.make_ui()
        self.set_notification(message, severity, actions, source)
        if expanded:
            self.setProperty("expanded", str(expanded))
            self.expand_btn.expanded = True if self.is_bottom else False

        EVENTS.evt_notification_dismiss.connect(self.close)

        # setup
        self.adjustSize()
        self.move_to_bottom_right() if self.is_bottom else self.move_to_top_right()

    # noinspection PyAttributeOutsideInit
    def make_ui(self):
        """Make ui.

        Row 1: Icon, text, expand, close
        Row 2: Source, Push buttons
        """
        self.row1_widget = QWidget(self)
        self.severity_icon = QtSeverityLabel(parent=self.row1_widget)
        self.severity_icon.setMaximumWidth(20)
        self.severity_icon.setMinimumHeight(20)

        self.message = hp.make_label(self.row1_widget, wrap=True)
        # self.message = QElidingLabel(self.row1_widget)
        self.message.setWordWrap(True)
        self.message.setMinimumWidth(self.MIN_WIDTH - 200)
        self.message.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.message.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)

        self.expand_btn = QtExpandButton(parent=self.row1_widget)
        self.expand_btn.expanded = True
        self.expand_btn.setToolTip("Click here to expand/contract text")
        self.expand_btn.setCursor(Qt.PointingHandCursor)
        self.expand_btn.setMaximumWidth(20)
        self.expand_btn.setMinimumHeight(20)
        self.expand_btn.clicked.connect(self.toggle_expansion)

        self.settings_btn = hp.make_qta_btn(self.row1_widget, "gear", tooltip="Show notification settings.", small=True)
        self.settings_btn.setCursor(Qt.PointingHandCursor)
        self.settings_btn.setMaximumWidth(20)
        self.settings_btn.setMinimumHeight(20)
        self.settings_btn.clicked.connect(self.settings)

        self.dismiss_btn = hp.make_qta_btn(self.row1_widget, "cross", tooltip="Dismiss this notification.", small=True)
        self.dismiss_btn.setCursor(Qt.PointingHandCursor)
        self.dismiss_btn.setMaximumWidth(20)
        self.dismiss_btn.setMinimumHeight(20)
        self.dismiss_btn.clicked.connect(self.close)

        self._timer_indicator = QProgressBar(self)
        self._timer_indicator.setObjectName("progress_timer")
        self._timer_indicator.setTextVisible(False)

        row_1 = QHBoxLayout(self.row1_widget)
        row_1.addWidget(self.severity_icon, alignment=Qt.AlignmentFlag.AlignTop)
        row_1.addWidget(self.message, stretch=1, alignment=Qt.AlignmentFlag.AlignTop)
        row_1.addWidget(self.expand_btn, alignment=Qt.AlignmentFlag.AlignTop)
        row_1.addWidget(self.settings_btn, alignment=Qt.AlignmentFlag.AlignTop)
        row_1.addWidget(self.dismiss_btn, alignment=Qt.AlignmentFlag.AlignTop)
        row_1.setSpacing(5)

        self.row2_widget = QWidget(self)
        self.row2_widget.setObjectName("actionButtons")
        self.row2_widget.hide()
        self.row2_widget.setMaximumHeight(34)

        self.row2 = QHBoxLayout(self.row2_widget)
        self.row2.addStretch(1)
        self.row2.setContentsMargins(12, 2, 16, 12)

        self.vertical_layout = QVBoxLayout(self)
        self.vertical_layout.setContentsMargins(2, 2, 2, 2)
        self.vertical_layout.setSpacing(2)
        self.vertical_layout.addWidget(self.row1_widget)
        self.vertical_layout.addWidget(self.row2_widget)
        self.vertical_layout.addStretch(1)
        self.vertical_layout.addWidget(self._timer_indicator)
        self.resize(self.MIN_WIDTH, self.MIN_HEIGHT)

    def set_notification(
        self,
        message: str,
        severity: NotificationSeverity = NotificationSeverity.INFO,
        actions: ActionSequence = None,
        source: str | None = None,
    ):
        """Set message."""
        self.message.setText(message)
        self.message.setToolTip(message)
        self.setup_buttons(actions)
        self.severity_icon.severity = str(severity)
        self.expand_btn.setVisible(self.sizeHint().height() > self.height())

    def slide_in(self):
        """Run animation that fades in the dialog with a slight slide up."""
        super().slide_in()
        if get_settings().notification.auto_expand:
            self.opacity_anim.finished.connect(self.auto_expand)

    def auto_expand(self):
        """Toggle expansion."""
        self.expand()

    def toggle_expansion(self):
        """Toggle the expanded state of the notification frame."""
        self.contract() if self.is_expanded else self.expand()
        self.timer.stop()

    def expand(self):
        """Expanded the notification so that the full message is visible."""
        curr = self.geometry()
        self.geom_anim.setDuration(100)
        self.geom_anim.setStartValue(curr)
        new_height = self.sizeHint().height()
        if new_height < curr.height():
            # new height would shift notification down, ensure some expansion
            new_height = curr.height() + self.MIN_EXPANSION
        delta = new_height - curr.height()
        self.geom_anim.setEndValue(
            QRect(
                curr.x(),
                curr.y() - delta if self.is_bottom else curr.y(),
                curr.width(),
                new_height,
            )
        )
        self.geom_anim.setEasingCurve(QEasingCurve.OutQuad)
        self.geom_anim.start()
        self.setProperty("expanded", True if self.is_bottom else False)
        self.expand_btn.expanded = False if self.is_bottom else True

    def contract(self):
        """Contract notification to a single elided line of the message."""
        geom = self.geometry()
        self.geom_anim.setDuration(100)
        self.geom_anim.setStartValue(geom)
        dlt = geom.height() - self.minimumHeight()
        self.geom_anim.setEndValue(
            QRect(
                geom.x(),
                geom.y() + dlt if self.is_bottom else geom.y(),
                geom.width(),
                geom.height() - dlt,
            )
        )
        self.geom_anim.setEasingCurve(QEasingCurve.OutQuad)
        self.geom_anim.start()
        self.setProperty("expanded", False if self.is_bottom else True)
        self.expand_btn.expanded = True if self.is_bottom else False

    def show(self):
        """Show the message with a fade and slight slide in from the bottom."""

        def _update_timer_indicator():
            with suppress(RuntimeError):
                self._timer_indicator.setValue(self.timer.remainingTime() / self.DISMISS_AFTER * 100)

        super().show()
        self.slide_in()
        if self.DISMISS_AFTER > 0:
            self.timer.setInterval(get_settings().notification.dismiss_time)
            self.timer.setSingleShot(True)
            self.timer.timeout.connect(self.close)
            self.timer.start()

            self.timer_bar.setInterval(50)
            self.timer_bar.setSingleShot(False)
            self.timer_bar.timeout.connect(_update_timer_indicator)
            self.timer_bar.start()

    def close(self):
        """Fade out then close."""
        try:
            self.opacity_anim.setDuration(self.FADE_OUT_RATE)
            self.opacity_anim.setStartValue(self.MAX_OPACITY)
            self.opacity_anim.setEndValue(0)
            self.opacity_anim.start()
            self.opacity_anim.finished.connect(super().close)
        except RuntimeError:
            pass

    def mouseMoveEvent(self, event):
        """On hover, stop the self-destruct timer."""
        self.timer.stop()
        self.timer_bar.stop()
        self._timer_indicator.setVisible(False)
        return super().mouseMoveEvent(event)

    def setup_buttons(self, actions: ActionSequence = ()):
        """Add buttons to the dialog.

        Parameters
        ----------
        actions : tuple, optional
            A sequence of 2-tuples, where each tuple is a string and a
            callable. Each tuple will be used to create button in the dialog,
            where the text on the button is determine by the first item in the
            tuple, and a callback function to call when the button is pressed
            is the second item in the tuple. by default ()
        """
        if actions is None:
            return

        if isinstance(actions, dict):
            actions = list(actions.items())

        for text, callback in actions:
            btn = hp.make_btn(None, text)

            def call_back_with_self(callback, self):
                """We need a higher order function this to capture the reference to self."""

                def _inner():
                    return callback(self)

                return _inner

            btn.clicked.connect(call_back_with_self(callback, self))
            btn.clicked.connect(self.close)
            self.row2.addWidget(btn)
        if actions:
            self.row2_widget.show()
            self.setMinimumHeight(self.row2_widget.maximumHeight() + self.minimumHeight())

    def sizeHint(self):
        """Return the size required to show the entire message."""
        return QSize(
            super().sizeHint().width(),
            self.row2_widget.height() + self.message.sizeHint().height() + 30,
        )

    @property
    def is_expanded(self) -> bool:
        """Checks whether text is expanded."""
        return self.property("expanded") if self.is_bottom else not self.property("expanded")

    def settings(self):
        """Show settings popup."""
        self.timer.stop()
        SettingsPopup(self.parent() or self).show()

    @classmethod
    def from_notification(cls, notification: Notification) -> QtNotification:
        """From notification."""
        actions = notification.actions
        if isinstance(notification, ErrorNotification):
            actions = tuple(notification.actions) + (
                # ("Copy to clipboard", partial(copy_to_clipboard, notification)),
                ("Report on GitHub", partial(show_report, notification)),
                ("View Traceback", partial(show_tb, notification)),
            )

        return cls(
            message=notification.message,
            severity=notification.severity,
            source=notification.source,
            actions=actions,
            # is_bottom=notification.severity != NotificationSeverity.SUCCESS,
            #             expanded=notification.severity == NotificationSeverity.SUCCESS,
            auto_close=notification.auto_close,
        )

    @classmethod
    @qthrottled(timeout=250)
    @ensure_main_thread
    def show_notification(cls, notification: Notification):
        """Show notification."""
        if notification.severity >= get_settings().notification.level:
            application_instance = QApplication.instance()
            if application_instance:
                # Check if this is running from a thread
                if application_instance.thread() != QThread.currentThread():
                    EVENTS.evt_notification.emit(notification)
                    return
            cls.from_notification(notification).show()


class SettingsPopup(QtFramelessPopup):
    """Popup window to control extra settings."""

    def __init__(self, parent):
        super().__init__(parent)
        self.setMinimumWidth(300)

    # noinspection PyAttributeOutsideInit
    def make_panel(self) -> QFormLayout:
        """Make panel."""
        self.dismiss_time = hp.make_labelled_slider(
            self,
            minimum=1000,
            maximum=10000,
            step_size=500,
            tooltip="Specify the amount of time before the popup is automatically dismissed. Time in milliseconds.",
        )
        self.dismiss_time.setValue(get_settings().notification.dismiss_time)
        self.dismiss_time.valueChanged.connect(self.on_apply)

        self.auto_expand = hp.make_checkbox(self, tooltip="Auto-expand notification if the message is too long.")
        self.auto_expand.setChecked(get_settings().notification.auto_expand)
        self.auto_expand.stateChanged.connect(self.on_apply)

        self.level = hp.make_combobox(self, tooltip="Specify what kind of notifications you wish to see.")
        hp.set_combobox_data(self.level, NOTIFICATION_LEVELS, get_settings().notification.level)
        self.level.currentTextChanged.connect(self.on_apply)

        main_layout = hp.make_form_layout()
        main_layout.addRow(
            hp.make_label(self, "Notification Settings", alignment=Qt.AlignmentFlag.AlignHCenter, bold=True)
        )
        main_layout.addRow(hp.make_label(self, "Auto-dismiss time (ms)"), self.dismiss_time)
        main_layout.addRow(hp.make_label(self, "Auto-expand"), self.auto_expand)
        main_layout.addRow(hp.make_label(self, "Notification level"), self.level)
        return main_layout

    def on_apply(self):
        """Update configuration."""
        settings = get_settings()
        settings.notification.dismiss_time = self.dismiss_time.value()
        settings.notification.auto_expand = self.auto_expand.isChecked()
        settings.notification.level = self.level.currentData()


def show_tb(notification: ErrorNotification, parent):
    """Show traceback."""
    tb_dialog = QDialog(parent=parent.parent())
    tb_dialog.setModal(True)
    # this is about the minimum width to not get re-wrap and the minimum height to not have scrollbar
    tb_dialog.resize(650, 270)
    tb_dialog.setLayout(QVBoxLayout())

    text = hp.make_text_edit(None, "")
    text.setHtml(notification.as_html())
    text.setReadOnly(True)
    debug_btn = hp.make_btn(None, "Enter Debugger")

    def _enter_debug_mode():
        debug_btn.setText("Now Debugging. Please quit debugger in console to continue")
        _debug_tb(notification.exception.__traceback__)
        debug_btn.setText("Enter Debugger")

    debug_btn.clicked.connect(_enter_debug_mode)
    tb_dialog.layout().addWidget(text)
    tb_dialog.layout().addWidget(debug_btn, 0, Qt.AlignmentFlag.AlignRight)
    tb_dialog.show()


def copy_to_clipboard(notification: ErrorNotification, parent):
    """Copy traceback to clipboard."""
    from qtextra.utils.utilities import get_system_info
    from qtextra.widgets.qt_button_clipboard import copy_text_to_clipboard

    html = "<b>More information</b><br><br>" + get_system_info(as_html=True) + "<br><br><b>Exception</b><br>"
    exception = notification.as_html()
    html += f"``{exception}``"

    text = hp.make_text_edit(None, "")
    text.setHtml(html)

    copy_text_to_clipboard(text.toMarkdown())
    text.deleteLater()


def show_report(notification: ErrorNotification, parent):
    """Report traceback."""
    import webbrowser

    from qtextra import __issue_url__
    from qtextra.utils.utilities import get_system_info
    from qtextra.widgets.qt_button_clipboard import copy_text_to_clipboard

    def _go_to_github():
        copy_text_to_clipboard(text.toMarkdown())
        webbrowser.open(__issue_url__)
        github_btn.setText("Copied report to clipboard!")

    def _copy_to_clipboard():
        copy_text_to_clipboard(text.toMarkdown())
        copy_btn.setText("Copied!")
        hp.add_flash_animation(text, color=THEMES.get_hex_color("foreground"), duration=500)

    report_dialog = QDialog(parent=parent.parent())
    report_dialog.setModal(True)
    # this is about the minimum width to not get re-wrap and the minimum height to not have scrollbar
    report_dialog.resize(650, 270)
    report_dialog.setLayout(QVBoxLayout())

    html = get_system_info(as_html=True) + "<br><br><b>Exception</b><br>"
    exception = notification.as_html()
    html += f"``{exception}``"

    text = hp.make_text_edit(None, "")
    text.setHtml(html)
    text.setReadOnly(True)

    copy_btn = hp.make_btn(None, "Copy to clipboard")
    copy_btn.clicked.connect(_copy_to_clipboard)
    github_btn = hp.make_btn(None, "Go to GitHub")
    github_btn.clicked.connect(_go_to_github)

    btn_layout = QHBoxLayout()
    btn_layout.addStretch(True)
    btn_layout.addWidget(copy_btn, 0, Qt.AlignmentFlag.AlignRight)
    btn_layout.addWidget(github_btn, 0, Qt.AlignmentFlag.AlignRight)

    report_dialog.layout().addWidget(text)
    report_dialog.layout().addLayout(btn_layout)
    report_dialog.show()


def _debug_tb(tb):
    import pdb

    from qtextra.helpers import event_hook_removed

    QApplication.processEvents()
    QApplication.processEvents()
    with event_hook_removed():
        print("Entering debugger. Type 'q' to return to the app.\n")
        pdb.post_mortem(tb)
        print("\nDebugging finished.  App active again.")


if __name__ == "__main__":  # pragma: no cover

    def _main():  # type: ignore[no-untyped-def]
        import sys
        from random import choice

        from qtextra.config import THEMES
        from qtextra.utils.dev import qframe

        def _popup_notif(severity=None):
            if not isinstance(severity, NotificationSeverity):
                severity = choice(list(NotificationSeverity))
            if severity == NotificationSeverity.ERROR:
                notif = ErrorNotification(ValueError("This is going to be quite a long exception\n" * 4))
            else:
                notif = Notification(
                    message=f"This is a test message: {severity!s}\n" * choice(range(5)), severity=severity
                )
            pop = QtNotification.from_notification(notif)
            THEMES.set_theme_stylesheet(pop)
            pop.show()

        def _popup_error():
            _popup_notif(NotificationSeverity.ERROR)

        def _warning():
            notif = Notification(
                message="Some requirements were not met - see what is not quite right.",
                severity=NotificationSeverity.WARNING,
                actions=(("Open Requirements Dialog", print),),
            )
            pop = QtNotification.from_notification(notif)
            THEMES.set_theme_stylesheet(pop)
            pop.show()

        app, frame, ha = qframe(False)
        frame.setMinimumSize(600, 600)

        btn2 = hp.make_btn(frame, "Create random notification")
        btn2.clicked.connect(_popup_notif)
        ha.addWidget(btn2)
        btn2 = hp.make_btn(frame, "Create error notification")
        btn2.clicked.connect(_popup_error)
        ha.addWidget(btn2)
        btn2 = hp.make_btn(frame, "Create warning notification")
        btn2.clicked.connect(_warning)
        ha.addWidget(btn2)

        ha.addWidget(btn2)
        frame.show()
        sys.exit(app.exec_())

    _main()
