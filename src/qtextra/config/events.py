"""Events emitter."""

from qtpy.QtCore import QObject, Signal

try:
    from qtextra.utils.notifications import Notification
except ImportError:
    Notification = object


class Events(QObject):
    """Events emitter."""

    # emitted when help view is requested
    evt_help_request = Signal(str)

    # logger/information events
    evt_msg_info = Signal(str)  # message
    evt_msg_success = Signal(str)  # message
    evt_msg_warning = Signal(str)  # message
    evt_msg_error = Signal(str)  # message
    evt_msg_critical = Signal(str)  # message

    # notification
    evt_notification_popup = Signal(str, str, str)  # title, message, type
    evt_notification_long_popup = Signal(str, str, str)  # title, message, type
    evt_notification_info = Signal(str, str)  # title, message
    evt_notification_success = Signal(str, str)  # title, message
    evt_notification_warning = Signal(str, str)  # title, message
    evt_notification_error = Signal(str, str)  # title, message
    evt_notification_critical = Signal(str, str)  # title, message

    # exception
    evt_exception = Signal(tuple)

    # notification events
    evt_notification_action = Signal(str, tuple)
    evt_notification_dismiss = Signal()
    evt_notification = Signal(Notification)

    # splash screen events
    evt_splash_msg = Signal(str)  # message to be displayed
    evt_splash_close = Signal()

    # Statusbar events
    evt_statusbar_help = Signal(object)
    evt_statusbar_status = Signal(object)

    # exit events
    evt_force_exit = Signal()

    def emit_evt_statusbar_status(self, obj):
        """Emit statusbar status event."""
        self.evt_statusbar_status.emit(obj)

    def emit_evt_statusbar_help(self, obj):
        """Emit statusbar help event."""
        self.evt_statusbar_help.emit(obj)


EVENTS: Events = Events()
