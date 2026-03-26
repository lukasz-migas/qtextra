"""Tests for mixin helpers."""

from __future__ import annotations

from qtpy.QtWidgets import QHBoxLayout, QWidget

from qtextra.config import EVENTS
from qtextra.mixins import ConfigMixin, DocumentationMixin, IndicatorMixin, MinimizeMixin, TimerMixin


class _ConfigProbe(ConfigMixin):
    def __init__(self):
        self.seen_settings = None

    def _on_set_from_config(self, settings=None):
        self.seen_settings = settings


class _ConfigProbeRaises(ConfigMixin):
    def _on_set_from_config(self, settings=None):
        raise RuntimeError("boom")


class _DocumentationProbe(QWidget, DocumentationMixin):
    ENABLE_TUTORIAL = True
    ENABLE_HTML = True

    def __init__(self):
        super().__init__()


class _TimerProbe(QWidget, TimerMixin):
    def __init__(self):
        super().__init__()
        self.triggered = 0

    def on_timeout(self):
        self.triggered += 1


class _MinimizeProbe(QWidget, MinimizeMixin):
    def __init__(self):
        super().__init__()
        self.hidden_called = 0
        self.focus_cleared = 0

    def _make_move_handle(self):
        return QHBoxLayout()

    def hide(self):
        self.hidden_called += 1
        super().hide()

    def clearFocus(self):
        self.focus_cleared += 1
        super().clearFocus()


def test_documentation_mixin_opens_local_docs_link(qtbot):
    with qtbot.waitSignal(EVENTS.evt_help_request, timeout=500) as blocker:
        DocumentationMixin._open_info_link("docs/index.md")
    assert blocker.args[0].startswith("file:///")


def test_documentation_mixin_emits_warning_for_invalid_link(qtbot):
    with qtbot.waitSignal(EVENTS.evt_msg_warning, timeout=500) as blocker:
        DocumentationMixin._open_info_link("not-a-real-link")
    assert blocker.args == ["The provided link is not valid"]


def test_documentation_mixin_builds_info_layout(qtbot):
    widget = _DocumentationProbe()
    qtbot.addWidget(widget)

    info_btn, layout = widget._make_info_layout(parent=widget)

    assert info_btn is widget._docs_info_btn
    assert widget._docs_tutorial_btn is not None
    assert layout.count() == 3
    assert layout.itemAt(1).widget() is widget._docs_tutorial_btn
    assert layout.itemAt(2).widget() is widget._docs_info_btn


def test_config_mixin_sets_and_resets_flags(monkeypatch):
    probe = _ConfigProbe()
    monkeypatch.setattr("qtextra.mixins.get_settings", lambda: {"theme": "dark"})

    probe.on_set_from_config()

    assert probe.seen_settings == {"theme": "dark"}
    assert probe._initialized_config is True
    assert probe._is_setting_config is False


def test_config_mixin_resets_flag_after_exception(monkeypatch):
    probe = _ConfigProbeRaises()
    monkeypatch.setattr("qtextra.mixins.get_settings", lambda: {"theme": "dark"})

    try:
        probe.on_set_from_config()
    except RuntimeError as exc:
        assert str(exc) == "boom"
    else:  # pragma: no cover
        raise AssertionError("Expected on_set_from_config to propagate the error.")

    assert probe._initialized_config is False
    assert probe._is_setting_config is False


def test_timer_mixin_adds_single_shot_timer(qtbot):
    widget = _TimerProbe()
    qtbot.addWidget(widget)

    timer = widget._add_single_shot_timer(10, widget.on_timeout)

    assert timer.isSingleShot() is True
    assert timer.isActive() is True
    qtbot.waitUntil(lambda: widget.triggered == 1, timeout=1000)
    assert timer.isActive() is False


def test_minimize_mixin_hides_and_clears_focus(qtbot):
    widget = _MinimizeProbe()
    qtbot.addWidget(widget)

    button, layout = widget._make_hide_handle()
    assert button is not None
    assert layout.count() == 1

    widget.on_hide()
    assert widget.hidden_called == 1
    assert widget.focus_cleared == 1


def test_indicator_mixin_emits_success_signal(qtbot):
    seen = []

    with qtbot.waitSignal(EVENTS.evt_msg_success, timeout=500) as blocker:
        IndicatorMixin.on_notify_success("Saved", func=seen.append)

    assert blocker.args == ["Saved"]
    assert seen == ["Saved"]
