"""Context managers."""
import signal
import socket
from contextlib import contextmanager

from qtpy.QtCore import QSocketNotifier


@contextmanager
def _maybe_allow_interrupt(qapp):
    """
    This manager allows to terminate a plot by sending a SIGINT. It is
    necessary because the running Qt backend prevents Python interpreter to
    run and process signals (i.e., to raise KeyboardInterrupt exception). To
    solve this one needs to somehow wake up the interpreter and make it close
    the plot window. We do this by using the signal.set_wakeup_fd() function
    which organizes a write of the signal number into a socketpair connected
    to the QSocketNotifier (since it is part of the Qt backend, it can react
    to that write event). Afterwards, the Qt handler empties the socketpair
    by a recv() command to re-arm it (we need this if a signal different from
    SIGINT was caught by set_wakeup_fd() and we shall continue waiting). If
    the SIGINT was caught indeed, after exiting the on_signal() function the
    interpreter reacts to the SIGINT according to the handle() function which
    had been set up by a signal.signal() call: it causes the qt_object to
    exit by calling its quit() method. Finally, we call the old SIGINT
    handler with the same arguments that were given to our custom handle()
    handler.
    We do this only if the old handler for SIGINT was not None, which means
    that a non-python handler was installed, i.e. in Julia, and not SIG_IGN
    which means we should ignore the interrupts.

    code from https://github.com/matplotlib/matplotlib/pull/13306
    """
    old_sigint_handler = signal.getsignal(signal.SIGINT)
    handler_args = None
    if old_sigint_handler in (None, signal.SIG_IGN, signal.SIG_DFL):
        yield
        return

    wsock, rsock = socket.socketpair()
    wsock.setblocking(False)
    old_wakeup_fd = signal.set_wakeup_fd(wsock.fileno())
    sn = QSocketNotifier(rsock.fileno(), QSocketNotifier.Type.Read)

    # Clear the socket to re-arm the notifier.
    sn.activated.connect(lambda *args: rsock.recv(1))

    def handle(*args):
        nonlocal handler_args
        handler_args = args
        qapp.exit()

    signal.signal(signal.SIGINT, handle)
    try:
        yield
    finally:
        wsock.close()
        rsock.close()
        sn.setEnabled(False)
        signal.set_wakeup_fd(old_wakeup_fd)
        signal.signal(signal.SIGINT, old_sigint_handler)
        if handler_args is not None:
            old_sigint_handler(*handler_args)
