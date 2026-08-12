"""Tests for the frameless welcome dialog."""

from __future__ import annotations

from qtpy.QtCore import Qt
from qtpy.QtGui import QColor, QPixmap
from qtpy.QtWidgets import QDialog

from qtextra.dialogs.qt_welcome import QtWelcomeDialog, WelcomeListItem, WelcomePage


def _pages() -> list[WelcomePage]:
    return [
        WelcomePage(
            title="Welcome",
            description="Start here",
            action_text="Begin",
            items=[WelcomeListItem(title="First item", description="Details", icon="star")],
        ),
        WelcomePage(title="Configure", items=[WelcomeListItem(title="Second item")]),
        WelcomePage(title="Ready"),
    ]


def test_welcome_models_validate_nested_content() -> None:
    page = WelcomePage.model_validate(
        {
            "title": "Welcome",
            "items": [{"title": "Theme", "description": "Choose one", "icon": "paint_palette"}],
        }
    )

    assert page.title == "Welcome"
    assert page.description == ""
    assert page.image_path is None
    assert page.action_text is None
    assert page.items == [WelcomeListItem(title="Theme", description="Choose one", icon="paint_palette")]


def test_welcome_dialog_accepts_page_mappings_and_requires_content(qtbot) -> None:
    dialog = QtWelcomeDialog([{"title": "Mapped", "items": [{"title": "Nested"}]}])
    qtbot.addWidget(dialog)

    assert dialog.pages[0].title == "Mapped"
    assert dialog.pages[0].items[0].title == "Nested"

    try:
        QtWelcomeDialog([])
    except ValueError as exc:
        assert str(exc) == "At least one welcome page is required."
    else:
        raise AssertionError("An empty welcome dialog must be rejected")


def test_welcome_navigation_updates_header_buttons_and_signals(qtbot) -> None:
    dialog = QtWelcomeDialog(_pages())
    qtbot.addWidget(dialog)
    dialog.show()

    changed: list[int] = []
    dialog.evt_current_changed.connect(changed.append)

    assert dialog.current_index == 0
    assert dialog.step_count_label.text() == "\u00b7 1 of 3"
    assert dialog.step_indicator.count == 3
    assert dialog.step_indicator.current_index == 0
    assert not dialog.back_button.isEnabled()
    assert dialog.skip_button.isVisible()
    assert dialog.primary_button.text() == "Begin"

    dialog.next_page()
    assert dialog.current_index == 1
    assert changed == [1]
    assert dialog.step_count_label.text() == "\u00b7 2 of 3"
    assert dialog.step_indicator.current_index == 1
    assert dialog.back_button.isEnabled()
    assert dialog.primary_button.text() == "Continue"

    dialog.set_current_index(99)
    assert dialog.current_index == 2
    assert changed == [1, 2]
    assert dialog.step_count_label.text() == "\u00b7 3 of 3"
    assert not dialog.skip_button.isVisible()
    assert dialog.primary_button.text() == "Let's go"

    dialog.set_current_index(-10)
    assert dialog.current_index == 0
    dialog.previous_page()
    assert dialog.current_index == 0


def test_welcome_skip_accepts_and_close_rejects(qtbot) -> None:
    skipped_dialog = QtWelcomeDialog(_pages())
    qtbot.addWidget(skipped_dialog)
    skipped: list[bool] = []
    finished: list[bool] = []
    skipped_dialog.evt_skipped.connect(lambda: skipped.append(True))
    skipped_dialog.evt_finished.connect(lambda: finished.append(True))

    skipped_dialog.skip_button.click()
    assert skipped == [True]
    assert finished == []
    assert skipped_dialog.result() == QDialog.DialogCode.Accepted

    closed_dialog = QtWelcomeDialog(_pages())
    qtbot.addWidget(closed_dialog)
    closed_skipped: list[bool] = []
    closed_dialog.evt_skipped.connect(lambda: closed_skipped.append(True))
    closed_dialog.close_button.click()

    assert closed_skipped == []
    assert closed_dialog.result() == QDialog.DialogCode.Rejected


def test_welcome_final_action_emits_finished_and_accepts(qtbot) -> None:
    dialog = QtWelcomeDialog([WelcomePage(title="Only", action_text="Open project")])
    qtbot.addWidget(dialog)
    finished: list[bool] = []
    dialog.evt_finished.connect(lambda: finished.append(True))

    assert dialog.primary_button.text() == "Open project"
    assert dialog.skip_button.isHidden()
    dialog.next_page()

    assert finished == [True]
    assert dialog.result() == QDialog.DialogCode.Accepted


def test_welcome_keyboard_navigation_and_escape(qtbot) -> None:
    dialog = QtWelcomeDialog(_pages())
    qtbot.addWidget(dialog)
    dialog.show()

    qtbot.keyClick(dialog, Qt.Key.Key_Right)
    assert dialog.current_index == 1
    qtbot.keyClick(dialog, Qt.Key.Key_Left)
    assert dialog.current_index == 0
    qtbot.keyClick(dialog, Qt.Key.Key_Return)
    assert dialog.current_index == 1
    qtbot.keyClick(dialog, Qt.Key.Key_Escape)
    assert dialog.result() == QDialog.DialogCode.Rejected


def test_welcome_uses_frameless_translucent_chrome(qtbot) -> None:
    dialog = QtWelcomeDialog(_pages(), title="Project setup", show_skip=False)
    qtbot.addWidget(dialog)

    assert dialog.windowFlags() & Qt.WindowType.FramelessWindowHint
    assert dialog.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    assert dialog.header_title_label.text() == "Project setup"
    assert dialog.skip_button.isHidden()
    assert dialog.close_button.accessibleName() == "Close"


def test_welcome_page_loads_local_image_and_collapses_missing_image(qtbot, tmp_path) -> None:
    image_path = tmp_path / "welcome.png"
    pixmap = QPixmap(320, 80)
    pixmap.fill(QColor("red"))
    assert pixmap.save(str(image_path))

    dialog = QtWelcomeDialog(
        [
            WelcomePage(title="Image", image_path=str(image_path)),
            WelcomePage(title="Missing", image_path=str(tmp_path / "missing.png")),
        ]
    )
    qtbot.addWidget(dialog)

    image_page = dialog.stack.widget(0).widget()
    missing_page = dialog.stack.widget(1).widget()
    assert image_page.image_widget is not None
    assert image_page.image_widget.heightForWidth(160) == 40
    assert missing_page.image_widget is None


def test_welcome_page_renders_long_structured_content_in_scroll_area(qtbot) -> None:
    page = WelcomePage(
        title="Long page",
        description="A wrapped description " * 20,
        items=[WelcomeListItem(title=f"Item {index}", description="Description " * 8) for index in range(12)],
    )
    dialog = QtWelcomeDialog([page])
    qtbot.addWidget(dialog)
    dialog.resize(720, 520)
    dialog.show()

    scroll = dialog.stack.widget(0)
    page_widget = scroll.widget()
    assert scroll.widgetResizable()
    assert page_widget.item_list is not None
    assert len(page_widget.item_list._item_widgets) == 12
    assert page_widget.sizeHint().height() > scroll.viewport().height()
