from __future__ import annotations

from dataclasses import dataclass

from qtpy.QtWidgets import QPushButton

from qtextra.dialogs.qt_close_window import QtConfirmCloseDialog
from qtextra.dialogs.qt_confirm import QtConfirmWithTextDialog
from qtextra.dialogs.qt_update_available import UpdateAvailableDialog, UpdateInfo


@dataclass
class DummyConfig:
    ask_before_close: bool = True


def test_qt_confirm_with_text_dialog_validates_input(qtbot):
    dialog = QtConfirmWithTextDialog(request="delete")
    qtbot.addWidget(dialog)

    assert dialog.ok_btn.isEnabled() is False

    dialog.request_edit.setText("wrong")
    dialog.validate()
    assert dialog.ok_btn.isEnabled() is False

    dialog.request_edit.setText("delete")
    dialog.validate()
    assert dialog.ok_btn.isEnabled() is True


def test_qt_confirm_close_dialog_save_and_do_not_ask(qtbot):
    saved = []
    config = DummyConfig()
    dialog = QtConfirmCloseDialog(
        parent=None,
        attr="ask_before_close",
        save_func=lambda: saved.append(True),
        config=config,
        no_icon=True,
    )
    qtbot.addWidget(dialog)

    dialog.do_not_ask.setChecked(True)
    dialog.save_and_accept()

    assert saved == [True]
    assert dialog.result() == dialog.DialogCode.Accepted
    assert config.ask_before_close is False


def test_qt_confirm_close_dialog_hides_save_when_no_callback(qtbot):
    dialog = QtConfirmCloseDialog(parent=None, save_func=None, no_icon=True)
    qtbot.addWidget(dialog)

    save_buttons = [btn for btn in dialog.findChildren(QPushButton) if btn.text() == "Save"]
    assert save_buttons
    assert save_buttons[0].isHidden() is True


def test_update_available_dialog_emits_actions(qtbot):
    dialog = UpdateAvailableDialog(
        UpdateInfo(
            app_name="App",
            current_version="1.0.0",
            available_version="1.1.0",
            whats_new_url="internal://whats-new",
        ),
    )
    qtbot.addWidget(dialog)

    seen: list[str] = []
    dialog.evt_update_requested.connect(lambda: seen.append("update"))
    dialog.evt_remind_later_requested.connect(lambda: seen.append("later"))
    dialog.evt_whats_new_requested.connect(lambda: seen.append("whats_new"))
    dialog.evt_dismissed.connect(lambda: seen.append("dismissed"))

    dialog._on_whats_new_clicked("whats_new")
    assert dialog.result_action == "whats_new"
    assert seen == ["whats_new"]

    dialog._result_action = "dismissed"
    dialog._on_not_now_clicked()
    assert dialog.result_action == "later"
    assert seen[-1] == "later"

    dialog = UpdateAvailableDialog(
        UpdateInfo(app_name="App", current_version="1.0.0", available_version="1.1.0"),
    )
    qtbot.addWidget(dialog)
    dismissed: list[str] = []
    dialog.evt_dismissed.connect(lambda: dismissed.append("dismissed"))
    dialog.reject()
    assert dialog.result_action == "dismissed"
    assert dismissed == ["dismissed"]


def test_update_available_dialog_update_accepts(qtbot):
    dialog = UpdateAvailableDialog(
        UpdateInfo(app_name="App", current_version="1.0.0", available_version="1.1.0"),
    )
    qtbot.addWidget(dialog)

    seen: list[str] = []
    dialog.evt_update_requested.connect(lambda: seen.append("update"))
    dialog._on_update_clicked()

    assert seen == ["update"]
    assert dialog.result_action == "update"
    assert dialog.result() == dialog.DialogCode.Accepted
