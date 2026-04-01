import sys

from qtextra.dialogs.qt_update_available import UpdateAvailableDialog, UpdateInfo
from qtextra.utils.dev import apply_style, qapplication

app = qapplication()
dlg = UpdateAvailableDialog(
    UpdateInfo(
        app_name="My Application",
        current_version="6.6.10",
        available_version="6.6.11",
        whats_new_url="internal://whats-new",
        message="A new version of My Application is available!",
    ),
)
apply_style(dlg)


def on_update() -> None:
    print("User chose update")


def on_later() -> None:
    print("User chose not now")


def on_whats_new() -> None:
    print("Show What's New dialog/page here")


dlg.evt_update_requested.connect(on_update)
dlg.evt_remind_later_requested.connect(on_later)
dlg.evt_whats_new_requested.connect(on_whats_new)

dlg.exec()
print("Result action:", dlg.result_action)
sys.exit(0)
