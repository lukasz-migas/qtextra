from __future__ import annotations

import pytest
from qtpy.QtCore import Qt

from qtextra.dialogs.qt_onboarding import OnboardingDialog, WhatsNewPage


@pytest.fixture
def pages() -> list[WhatsNewPage]:
    return [
        WhatsNewPage(title="Alpha", body_html="<p>First</p>"),
        WhatsNewPage(title="Beta", body_html="<p>Second</p>"),
        WhatsNewPage(title="Gamma", body_html="<p>Third</p>"),
    ]


def test_whats_new_page_uses_pydantic_model() -> None:
    page = WhatsNewPage(title="Alpha", body_html="<p>Hello</p>")
    dumped = page.model_dump()

    assert dumped["title"] == "Alpha"
    assert dumped["body_html"] == "<p>Hello</p>"
    assert dumped["image_path"] is None


def test_onboarding_dialog_requires_pages() -> None:
    with pytest.raises(ValueError, match="At least one page is required"):
        OnboardingDialog([])


def test_onboarding_dialog_navigation(qtbot, pages) -> None:
    dialog = OnboardingDialog(pages, app_name="App", version="1.2.3")
    qtbot.addWidget(dialog)
    dialog.show()

    assert dialog.current_index() == 0
    assert dialog.back_button.isEnabled() is False
    assert dialog.next_button.isVisible() is True
    assert dialog.next_button.text() == "Next >"

    dialog.next_page()
    assert dialog.current_index() == 1
    assert dialog.back_button.isEnabled() is True

    dialog.set_current_index(2)
    assert dialog.current_index() == 2
    assert dialog.next_button.text() == "Done"

    dialog.previous_page()
    assert dialog.current_index() == 1


def test_onboarding_dialog_signals_and_checkbox(qtbot, pages) -> None:
    dialog = OnboardingDialog(pages, show_dont_show_again=True)
    qtbot.addWidget(dialog)

    seen: list[str | bool] = []
    dialog.skipped.connect(lambda: seen.append("skipped"))
    dialog.finished_viewing.connect(lambda: seen.append("finished"))
    dialog.dont_show_again_changed.connect(lambda state: seen.append(state))

    dialog.dont_show_again_checkbox.setChecked(True)
    assert dialog.dont_show_again() is True
    assert True in seen

    dialog._on_skip()
    assert "skipped" in seen

    dialog = OnboardingDialog(pages)
    qtbot.addWidget(dialog)
    done: list[str] = []
    dialog.finished_viewing.connect(lambda: done.append("finished"))
    dialog.set_current_index(2)
    dialog.next_page()
    assert done == ["finished"]
    assert dialog.result() == dialog.DialogCode.Accepted


def test_onboarding_dialog_key_navigation(qtbot, pages) -> None:
    dialog = OnboardingDialog(pages)
    qtbot.addWidget(dialog)
    dialog.show()

    qtbot.keyClick(dialog, Qt.Key.Key_Right)
    assert dialog.current_index() == 1

    qtbot.keyClick(dialog, Qt.Key.Key_Left)
    assert dialog.current_index() == 0
