# ruff: noqa: INP001

from __future__ import annotations

import importlib
import sys
from contextlib import contextmanager
from types import ModuleType, SimpleNamespace


def _install_fake_sentry(monkeypatch):
    state = SimpleNamespace(
        init_kwargs=None,
        tags=[],
        user=None,
        captured_messages=[],
    )

    class FakeScope:
        def __init__(self, client=None):
            self.client = client
            self.tags = {}
            self.extras = {}

        def set_tag(self, key, value):
            self.tags[key] = value

        def set_extra(self, key, value):
            self.extras[key] = value

        def capture_exception(self, exc):
            payload = {
                "exception": {"values": [{"type": type(exc).__name__}]},
                "tags": self.tags.copy(),
                "extra": self.extras.copy(),
            }
            transport = self.client.kwargs.get("transport")
            if transport is not None:
                transport(payload)
            return "event-456"

    @contextmanager
    def new_scope():
        yield FakeScope()

    class FakeClient:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def close(self):
            return None

    class FakeLoguruIntegration:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

    class FakeCriticalLevel:
        value = 50

    fake_sentry = ModuleType("sentry_sdk")
    fake_sentry.capture_exception = lambda *args, **kwargs: None
    fake_sentry.capture_message = lambda message, level="info", scope=None: (
        state.captured_messages.append(
            {"message": message, "level": level, "scope": scope},
        )
        or "event-123"
    )
    fake_sentry.init = lambda **kwargs: setattr(state, "init_kwargs", kwargs)
    fake_sentry.set_tag = lambda key, value: state.tags.append((key, value))
    fake_sentry.set_user = lambda value: setattr(state, "user", value)
    fake_sentry.new_scope = new_scope
    fake_sentry.Client = FakeClient
    fake_sentry.Scope = FakeScope

    fake_integrations = ModuleType("sentry_sdk.integrations")
    fake_loguru = ModuleType("sentry_sdk.integrations.loguru")
    fake_loguru.LoggingLevels = SimpleNamespace(CRITICAL=FakeCriticalLevel())
    fake_loguru.LoguruIntegration = FakeLoguruIntegration

    monkeypatch.setitem(sys.modules, "sentry_sdk", fake_sentry)
    monkeypatch.setitem(sys.modules, "sentry_sdk.integrations", fake_integrations)
    monkeypatch.setitem(sys.modules, "sentry_sdk.integrations.loguru", fake_loguru)
    return state


def _reload_sentry_modules():
    for name in [
        "qtextra.dialogs.sentry",
        "qtextra.dialogs.sentry.feedback",
        "qtextra.dialogs.sentry.telemetry",
        "qtextra.dialogs.sentry.utilities",
    ]:
        sys.modules.pop(name, None)

    utilities = importlib.import_module("qtextra.dialogs.sentry.utilities")
    telemetry = importlib.import_module("qtextra.dialogs.sentry.telemetry")
    feedback = importlib.import_module("qtextra.dialogs.sentry.feedback")
    sentry_dialogs = importlib.import_module("qtextra.dialogs.sentry")
    return utilities, telemetry, feedback, sentry_dialogs


def test_get_sentry_settings_reads_environment(monkeypatch):
    _install_fake_sentry(monkeypatch)
    monkeypatch.setenv("QTEXTRA_TELEMETRY_SENTRY_DSN", "https://dsn.example")
    monkeypatch.setenv("QTEXTRA_TELEMETRY_SHOW_HOSTNAME", "1")
    monkeypatch.setenv("QTEXTRA_TELEMETRY_SHOW_LOCALS", "0")
    monkeypatch.setenv("QTEXTRA_TELEMETRY_TRACES_SAMPLE_RATE", "0.25")
    monkeypatch.setenv("QTEXTRA_TELEMETRY_PROFILES_SAMPLE_RATE", "0.5")

    utilities, _, _, _ = _reload_sentry_modules()
    settings = utilities.get_sentry_settings()

    assert settings["dsn"] == "https://dsn.example"
    assert settings["include_local_variables"] is False
    assert settings["traces_sample_rate"] == 0.25
    assert settings["profiles_sample_rate"] == 0.5
    assert "enable_tracing" not in settings
    assert settings["server_name"]


def test_install_error_monitor_initializes_sdk(monkeypatch):
    state = _install_fake_sentry(monkeypatch)
    utilities, _, _, sentry_dialogs = _reload_sentry_modules()

    monkeypatch.setattr(sentry_dialogs, "ask_opt_in", lambda settings, force=False, parent=None: settings)
    monkeypatch.setattr(
        utilities,
        "get_sentry_settings",
        lambda **overrides: {"dsn": "https://dsn.example", "release": "1.2.3", **overrides},
    )

    settings = SimpleNamespace(telemetry_enabled=True, telemetry_with_locals=False)
    sentry_dialogs.install_error_monitor(settings, app_name="demo")

    assert state.init_kwargs["dsn"] == "https://dsn.example"
    assert state.init_kwargs["include_local_variables"] is False
    assert "enable_tracing" not in state.init_kwargs
    assert state.user["username"]
    assert ("app_name", "demo") in state.tags


def test_get_sample_event_returns_preview_payload(monkeypatch):
    _install_fake_sentry(monkeypatch)
    utilities, _, _, _ = _reload_sentry_modules()

    event = utilities.get_sample_event(include_local_variables=True)

    assert event["exception"]["values"][0]["type"] == "ZeroDivisionError"
    assert "platform.system" in event["tags"]


def test_telemetry_dialog_updates_preview_and_tooltips(monkeypatch, qtbot):
    _install_fake_sentry(monkeypatch)
    _, telemetry, _, _ = _reload_sentry_modules()

    monkeypatch.setattr(
        telemetry,
        "get_sample_event",
        lambda include_local_variables=False: {"include_local_variables": include_local_variables},
    )

    dialog = telemetry.TelemetryOptInDialog(with_locals=False)
    qtbot.addWidget(dialog)

    assert "sensitive values" in dialog.send_locals.toolTip()
    assert "False" in dialog.txt.toPlainText() or "false" in dialog.txt.toPlainText()

    dialog.send_locals.setChecked(True)
    assert dialog._send_locals is True
    assert "True" in dialog.txt.toPlainText() or "true" in dialog.txt.toPlainText()


def test_submit_feedback_posts_only_when_configured(monkeypatch):
    state = _install_fake_sentry(monkeypatch)
    monkeypatch.setenv("QTEXTRA_TELEMETRY_SENTRY_DSN", "dsn")
    monkeypatch.setenv("QTEXTRA_TELEMETRY_ORGANIZATION", "org")
    monkeypatch.setenv("QTEXTRA_TELEMETRY_PROJECT", "proj")

    _, _, feedback, _ = _reload_sentry_modules()
    monkeypatch.setattr(feedback, "_post_feedback", lambda data: data["event_id"] == "event-123")

    event_id = feedback.submit_feedback("Feedback title", "Something happened", name="Tester", email="a@b.c")

    assert event_id == "event-123"
    assert state.captured_messages[0]["level"] == "info"
    assert state.captured_messages[0]["scope"].extras["feedback.name"] == "Tester"

    monkeypatch.delenv("QTEXTRA_TELEMETRY_PROJECT")
    _, _, feedback, _ = _reload_sentry_modules()
    assert feedback.submit_feedback("Feedback title", "Something happened") is None
