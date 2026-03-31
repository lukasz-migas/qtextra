"""Sentry utilities."""

from __future__ import annotations

import logging
import os
import platform
import socket
import typing as ty
import warnings
from contextlib import suppress
from functools import lru_cache
from importlib import metadata
from subprocess import run

from loguru import logger
from sentry_sdk.integrations.loguru import LoggingLevels, LoguruIntegration

try:
    from rich import print as pprint
except ImportError:  # pragma: no cover
    from pprint import pprint

from getpass import getuser

import sentry_sdk
from koyo.system import running_as_pyinstaller_app

# disable logging from sentry_sdk
logging.getLogger("sentry_sdk").setLevel(logging.ERROR)
warnings.filterwarnings("ignore", category=ResourceWarning, module="sentry_sdk")

PACKAGE: str = os.getenv("QTEXTRA_TELEMETRY_PACKAGE", "qtextra")
ENVIRONMENT: str = os.getenv("QTEXTRA_TELEMETRY_ENVIRONMENT", "desktop")
SAMPLE_DSN = "https://public@example.ingest.sentry.io/1"


def env_flag(name: str, default: bool = False) -> bool:
    """Return a bool parsed from an environment variable."""
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_float(name: str, default: float | None) -> float | None:
    """Return a float parsed from an environment variable."""
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    try:
        return float(value)
    except ValueError:
        return default


def get_username() -> str:
    """Return the current username if available."""
    with suppress(Exception):
        return getuser()
    return "unknown"


def get_sentry_dsn() -> str:
    """Return the configured Sentry DSN."""
    return os.getenv("QTEXTRA_TELEMETRY_SENTRY_DSN", "")


def get_show_hostname() -> bool:
    """Return whether the hostname should be attached to events."""
    return env_flag("QTEXTRA_TELEMETRY_SHOW_HOSTNAME", default=False)


def get_show_locals() -> bool:
    """Return whether local variables should be attached to stack frames."""
    return env_flag("QTEXTRA_TELEMETRY_SHOW_LOCALS", default=True)


def get_debug() -> bool:
    """Return whether Sentry debug logging is enabled."""
    return env_flag("QTEXTRA_TELEMETRY_DEBUG", default=False)


def get_version() -> str:
    """Return the configured release version override, if any."""
    return os.getenv("QTEXTRA_TELEMETRY_VERSION", "")


def get_traces_sample_rate() -> float | None:
    """Return the traces sample rate."""
    return env_float("QTEXTRA_TELEMETRY_TRACES_SAMPLE_RATE", 1.0)


def get_profiles_sample_rate() -> float | None:
    """Return the profiles sample rate."""
    return env_float("QTEXTRA_TELEMETRY_PROFILES_SAMPLE_RATE", 1.0)


def get_server_name() -> str:
    """Return the hostname to send to Sentry, if enabled."""
    return socket.gethostname() if get_show_hostname() else ""


def strip_sensitive_data(event: dict, hint: dict) -> dict:
    """Pre-send hook to strip sensitive data from `event` dict.
    https://docs.sentry.io/platforms/python/configuration/filtering/#filtering-error-events.
    """
    # strip `abs_paths` from stack_trace to hide local paths
    with suppress(KeyError, IndexError):
        for exc in event["exception"]["values"]:
            for frame in exc["stacktrace"]["frames"]:
                frame.pop("abs_path", None)
        # only include the name of the executable in sys.argv (remove paths)
        if args := event.get("extra", {}).get("sys.argv"):
            args[0] = args[0].split(os.sep)[-1]
    if not get_show_hostname():
        event.pop("server_name", None)
    if get_debug():  # pragma: no cover
        pprint(event)
    logger.trace(f"Sending sentry event - ({hint})")
    return event


def is_editable_install(dist_name: str) -> bool:
    """Return True if `dist_name` is installed as editable.
    i.e: if the package isn't in site-packages or user site-packages.
    """
    from site import getsitepackages, getusersitepackages

    dist = metadata.distribution(dist_name)
    installed_paths = [*getsitepackages(), getusersitepackages()]
    root = str(dist.locate_file(""))
    return all(loc not in root for loc in installed_paths)


def try_get_git_sha(package: str | None = None) -> str:
    """Try to return a git sha, for `dist_name` and detect if dirty.
    Return empty string on failure.
    """
    package = package or PACKAGE
    try:
        ff = metadata.distribution(package).locate_file("")
        out = run(["git", "-C", ff, "rev-parse", "HEAD"], capture_output=True)
        if out.returncode:  # pragma: no cover
            return ""
        sha = out.stdout.decode().strip()
        # exit with 1 if there are differences and 0 means no differences
        # disallow external diff drivers
        out = run(["git", "-C", ff, "diff", "--no-ext-diff", "--quiet", "--exit-code"])
        if out.returncode:  # pragma: no cover
            sha += "-dirty"
    except (metadata.PackageNotFoundError, FileNotFoundError, OSError):  # pragma: no cover
        return ""
    else:
        return sha


@lru_cache
def get_release(package: str | None = None) -> str:
    """Get the current release string for `package`.
    If the package is an editable install, it will return the current git sha.
    Otherwise return version string from package metadata.
    """
    package = package or PACKAGE
    with suppress(ModuleNotFoundError, ImportError, metadata.PackageNotFoundError, OSError):
        if is_editable_install(package):
            sha = try_get_git_sha(package)
            if sha:
                return sha
        return metadata.version(package)
    return "UNDETECTED"


def _get_tags() -> dict:
    tags = {
        "platform.system": platform.system(),
        "platform.platform": platform.platform(),
    }

    with suppress(ImportError):
        from napari.utils.info import _sys_name

        sys = _sys_name()
        if sys:
            tags["system_name"] = sys

    with suppress(ImportError):
        import qtpy

        tags["qtpy.API_NAME"] = qtpy.API_NAME
        tags["qtpy.QT_VERSION"] = qtpy.QT_VERSION

    with suppress(ModuleNotFoundError, ImportError):
        tags["editable_install"] = str(is_editable_install(PACKAGE))
    tags["frozen"] = running_as_pyinstaller_app()
    return tags


def configure_user() -> None:
    """Set the Sentry user after the SDK has been initialized."""
    sentry_sdk.set_user({"username": get_username(), "ip_address": "{{auto}}"})


def configure_scope_tags(scope: ty.Any | None = None) -> None:
    """Apply common tags to the current scope or to a provided scope."""
    setter = scope.set_tag if scope is not None else sentry_sdk.set_tag
    for key, value in _get_tags().items():
        setter(key, value)


def get_sentry_settings(**overrides: ty.Any) -> dict[str, ty.Any]:
    """Return Sentry SDK settings derived from environment variables."""
    settings = {
        "dsn": get_sentry_dsn(),
        "release": get_version() or get_release(),
        # When enabled, local variables are sent along with stackframes.
        # This can have a performance and PII impact.
        "include_local_variables": get_show_locals(),
        "traces_sample_rate": get_traces_sample_rate(),
        "profiles_sample_rate": get_profiles_sample_rate(),
        # Empty server name prevents the SDK from auto-discovering the hostname.
        "server_name": get_server_name(),
        "send_default_pii": True,
        "before_send": strip_sensitive_data,
        "debug": get_debug(),
        "environment": ENVIRONMENT,
        "integrations": INTEGRATIONS,
        "auto_enabling_integrations": False,
        "profiler_mode": "thread",
    }
    settings.update(overrides)
    return settings


def get_sample_event(**kwargs: ty.Any) -> dict:
    """Return an example event as would be generated by an exception."""
    event: dict[str, ty.Any] = {}

    def _transport(payload: dict) -> None:
        nonlocal event
        event = payload

    settings = get_sentry_settings(dsn=SAMPLE_DSN, transport=_transport, **kwargs)

    client = sentry_sdk.Client(**settings)
    with sentry_sdk.new_scope() as scope:
        scope.set_client(client)
        configure_scope_tags(scope)
        try:
            some_variable = 1  # noqa
            another_variable = "my_string"  # noqa
            1 / 0  # noqa
        except ZeroDivisionError as exc:
            scope.capture_exception(exc)
        finally:
            client.close()
    return event


SENTRY_LOGURU = LoguruIntegration(
    level=LoggingLevels.CRITICAL.value,  # Capture info and above as breadcrumbs
    event_level=LoggingLevels.CRITICAL.value,  # Send errors as events
)

INTEGRATIONS = [SENTRY_LOGURU]


SENTRY_SETTINGS = get_sentry_settings()
