"""Tests for the README showcase example."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest
from qtpy.QtWidgets import QLabel, QPushButton
from scripts.capture_readme_showcase import _activate_capture_button, _display_path, _get_capture_buttons

from qtextra.widgets.qt_countdown import QtCountdownWidget
from qtextra.widgets.qt_toolbar_panel import QtPanelToolbar

ROOT = Path(__file__).resolve().parents[1]
SHOWCASE_PATH = ROOT / "examples" / "showcase.py"


def _load_showcase_module() -> ModuleType:
    """Load the showcase module from the examples directory."""
    spec = importlib.util.spec_from_file_location("qtextra_examples_showcase", SHOWCASE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not import showcase example from {SHOWCASE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_build_showcase_uses_toolbar_capture_buttons(qtbot):
    module = _load_showcase_module()

    window = module.build_showcase()
    qtbot.addWidget(window)
    window.show()

    toolbar = getattr(window, "_showcase_toolbar", None)
    assert isinstance(toolbar, QtPanelToolbar)

    capture_buttons = _get_capture_buttons(window)
    assert len(capture_buttons) == 4

    expected_panels = [
        "showcase_overview_panel",
        "showcase_inputs_panel",
        "showcase_tables_panel",
        "showcase_tools_panel",
    ]
    assert toolbar.stack_widget.currentWidget().objectName() == expected_panels[0]

    for button, panel_name in zip(capture_buttons[1:], expected_panels[1:]):
        _activate_capture_button(window, button)
        qtbot.waitUntil(lambda: toolbar.stack_widget.currentWidget().objectName() == panel_name)  # noqa: B023

    toggle_labels_btn = window.findChild(QPushButton, "showcase_toggle_toolbar_labels")
    assert toggle_labels_btn is not None
    assert toolbar.label_hidden is False

    toggle_labels_btn.click()
    assert toolbar.label_hidden is True

    toggle_labels_btn.click()
    assert toolbar.label_hidden is False


def test_showcase_overview_embeds_countdown_controls(qtbot):
    module = _load_showcase_module()

    window = module.build_showcase()
    qtbot.addWidget(window)
    window.show()

    countdown = window.findChild(QtCountdownWidget, "showcase_countdown")
    status_label = window.findChild(QLabel, "showcase_countdown_status")
    start_btn = window.findChild(QPushButton, "showcase_countdown_start")
    stop_btn = window.findChild(QPushButton, "showcase_countdown_stop")
    reset_btn = window.findChild(QPushButton, "showcase_countdown_reset")
    toggle_label_btn = window.findChild(QPushButton, "showcase_countdown_toggle_label")

    assert countdown is not None
    assert status_label is not None
    assert start_btn is not None
    assert stop_btn is not None
    assert reset_btn is not None
    assert toggle_label_btn is not None

    qtbot.waitUntil(lambda: status_label.text().startswith("Remaining:"), timeout=1000)

    stop_btn.click()
    remaining_at_stop = countdown.remaining_seconds
    qtbot.wait(200)
    assert countdown.remaining_seconds == pytest.approx(remaining_at_stop)

    reset_btn.click()
    assert countdown.remaining_seconds == pytest.approx(45.0)
    assert status_label.text().startswith("Remaining:")

    label_visible = countdown.label_visible
    toggle_label_btn.click()
    assert countdown.label_visible is (not label_visible)

    start_btn.click()
    qtbot.wait(200)
    assert countdown.remaining_seconds < 45.0


def test_capture_readme_showcase_display_path_handles_external_paths():
    assert _display_path(SHOWCASE_PATH).replace("\\", "/") == "examples/showcase.py"
    assert _display_path(Path("/tmp/readme_showcase.jpg")) == "/tmp/readme_showcase.jpg"
