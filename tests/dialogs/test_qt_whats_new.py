from __future__ import annotations

import pytest

from qtextra.dialogs.qt_whats_new import WhatsNewDialog, WhatsNewPage


@pytest.fixture
def pages() -> list[WhatsNewPage]:
    return [
        WhatsNewPage(title="Alpha", html="<p>First</p>"),
        WhatsNewPage(title="Beta", html="<p>Second</p>"),
        WhatsNewPage(title="Gamma", html="<p>Third</p>"),
    ]


def test_whats_new_dialog_navigation_labels(qtbot, pages) -> None:
    dialog = WhatsNewDialog(pages, version="1.2.3")
    qtbot.addWidget(dialog)
    dialog.show()

    assert dialog._prev_btn.text() == "< Previous"
    assert dialog._next_btn.text() == "Next >"
    assert dialog._prev_btn.isEnabled() is False

    dialog._next()
    assert dialog._prev_btn.isEnabled() is True
    assert dialog._next_btn.text() == "Next >"

    dialog._go_to(2, animate=False)
    assert dialog._next_btn.text() == "Done"


def test_whats_new_dialog_ignores_out_of_range_navigation(qtbot, pages) -> None:
    dialog = WhatsNewDialog(pages)
    qtbot.addWidget(dialog)

    dialog._go_to(0, animate=False)
    dialog._go_to(99, animate=False)
    assert dialog._current == 0

    dialog._go_to(-1, animate=False)
    assert dialog._current == 0
