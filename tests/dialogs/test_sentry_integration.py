"""Exercise the installed Sentry SDK without sending events over the network."""

from __future__ import annotations

import subprocess
import sys

import pytest


def test_real_sentry_sdk() -> None:
    """Run in isolation because the other Sentry tests replace SDK modules."""
    result = subprocess.run([sys.executable, __file__, "check"], capture_output=True, text=True, check=False)
    if result.returncode == 77:
        pytest.skip("sentry-sdk is not installed")
    assert result.returncode == 0, result.stdout + result.stderr


def _check_real_sentry_sdk() -> None:
    try:
        import sentry_sdk
    except ImportError:
        sys.exit(77)

    from types import SimpleNamespace

    from loguru import logger
    from sentry_sdk.transport import Transport

    import qtextra.dialogs.sentry as dialogs
    from qtextra.dialogs.sentry import utilities

    class CaptureTransport(Transport):
        def __init__(self) -> None:
            super().__init__()
            self.events = []

        def capture_envelope(self, envelope) -> None:
            event = envelope.get_event()
            if event:
                self.events.append(event)

    for include_locals in (True, False):
        event = utilities.get_sample_event(include_local_variables=include_locals)
        frame = event["exception"]["values"][0]["stacktrace"]["frames"][-1]
        assert ("some_variable" in frame.get("vars", {})) == include_locals

    transport = CaptureTransport()
    original_settings = utilities.get_sentry_settings
    utilities.get_sentry_settings = lambda **kwargs: original_settings(
        dsn=utilities.SAMPLE_DSN, transport=transport, **kwargs
    )
    dialogs.ask_opt_in = lambda settings: settings
    dialogs.install_error_monitor(SimpleNamespace(telemetry_enabled=True, telemetry_with_locals=True))
    options = sentry_sdk.get_client().options
    if utilities.SENTRY_MAJOR_VERSION >= 3:
        assert options["profile_lifecycle"] == "trace"
        assert options["profile_session_sample_rate"] == utilities.get_profiles_sample_rate()
    else:
        assert options["profiles_sample_rate"] == utilities.get_profiles_sample_rate()
    logger.critical("qtextra sentinel critical")
    sentry_sdk.capture_message("qtextra sentinel message")

    def capture_secret() -> None:
        password = "not-a-real-password"  # noqa: F841
        visible_value = "ordinary-value"  # noqa: F841
        try:
            raise ValueError("test failure")  # noqa: TRY301
        except ValueError as exc:
            sentry_sdk.capture_exception(exc)

    capture_secret()
    assert any("sentinel critical" in str(event.get("logentry", {})) for event in transport.events)
    message = next(event for event in transport.events if event.get("message") == "qtextra sentinel message")
    assert any("sentinel critical" in str(item) for item in message.get("breadcrumbs", {}).get("values", []))
    error = next(event for event in transport.events if event.get("exception"))
    variables = error["exception"]["values"][0]["stacktrace"]["frames"][-1]["vars"]
    assert "ordinary-value" in variables["visible_value"]
    if utilities.SENTRY_MAJOR_VERSION >= 3:
        assert "not-a-real-password" not in str(variables["password"])
    sentry_sdk.get_client().close()


if __name__ == "__main__":
    _check_real_sentry_sdk()
