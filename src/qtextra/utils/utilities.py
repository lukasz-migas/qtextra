"""Extra utilities for qtextra."""

from __future__ import annotations

import sys
import typing as ty
from functools import lru_cache
from pathlib import Path

from koyo.utilities import running_as_pyinstaller_app
from loguru import logger

from qtextra.typing import Connectable


def running_under_pytest() -> bool:
    """Return True if currently running under py.test.

    This function is used to do some adjustment for testing. The environment
    variable ORIGAMI_PYTEST is defined in conftest.py.
    """
    import os

    return bool(os.environ.get("QTEXTRA_PYTEST"))


def get_docs_path() -> Path:
    """Get path to docs directory."""
    base_path = Path(sys.executable).parent

    if running_as_pyinstaller_app():
        docs_path = base_path
    else:
        docs_path = base_path.parent
    return docs_path


def check_url(url: str) -> bool:
    """Parse typical URL.

    See: https://stackoverflow.com/a/50352868
    """
    from urllib.parse import urljoin, urlparse

    final_url = urlparse(urljoin(url, "/"))
    return all([final_url.scheme, final_url.netloc, final_url.path]) and len(final_url.netloc.split(".")) > 1


def memory_usage() -> float:
    """
    Return physical memory usage (float)
    Requires the cross-platform psutil (>=v0.3) library
    (https://github.com/giampaolo/psutil).
    """
    import psutil

    # This is needed to avoid a deprecation warning error with
    # newer psutil versions
    try:
        percent = psutil.virtual_memory().percent
    except Exception:
        percent = psutil.phymem_usage().percent
    return percent


def process_memory_usage() -> float:
    """Return process memory usage (float)."""
    import psutil

    process = psutil.Process()
    return process.memory_percent()


@lru_cache(maxsize=2)
def get_system_info(as_html=False) -> str:
    """Gathers relevant module versions for troubleshooting purposes.

    Parameters
    ----------
    as_html : bool
        if True, info will be returned as HTML, suitable for a QTextEdit widget
    """
    import platform
    import sys

    from qtextra import __version__ as qtextra_version

    sys_version = sys.version.replace("\n", " ")

    text = f"<b>Python</b>: {sys_version}<br>"
    text += f"<b>Platform</b>: {platform.platform()}<br><br>"
    text += f"<b>qtextra</b>: {qtextra_version}<br>"

    try:
        from qtpy import API_NAME, PYQT_VERSION, PYSIDE_VERSION, QtCore

        if API_NAME == "PySide2":
            API_VERSION = PYSIDE_VERSION
        elif API_NAME == "PyQt5":
            API_VERSION = PYQT_VERSION
        else:
            API_VERSION = ""

        text += f"<b>Qt</b>: {QtCore.__version__}<br>"
        text += f"<b>{API_NAME}</b>: {API_VERSION}<br>"

    except Exception as e:
        text += f"<b>Qt</b>: Import failed ({e})<br>"

    modules = (
        ("numpy", "NumPy"),
        ("scipy", "SciPy"),
        ("vispy", "VisPy"),
        ("napari", "Napari"),
        ("sklearn", "Scikit-Learn"),
        ("xgboost", "XGBoost"),
    )
    loaded = {}
    for module, name in modules:
        try:
            loaded[module] = __import__(module)
            text += f"<b>{name}</b>: {loaded[module].__version__}<br>"
        except Exception as e:
            text += f"<b>{name}</b>: Import failed ({e})<br>"

    text += "<br><b>OpenGL:</b><br>"

    if loaded.get("vispy", False):
        sys_info_text = (
            "<br>".join([loaded["vispy"].sys_info().split("\n")[index] for index in [-4, -3]])
            .replace("'", "")
            .replace("<br>", "<br>  - ")
        )
        text += f"  - {sys_info_text}<br>"
    else:
        text += "  - failed to load vispy"

    text += "<br><b>Screens:</b><br>"

    try:
        from qtpy.QtGui import QGuiApplication

        screen_list = QGuiApplication.screens()
        for i, screen in enumerate(screen_list, start=1):
            text += (
                f"  - screen {i}: resolution {screen.geometry().width()}x{screen.geometry().height()},"
                f" scale {screen.devicePixelRatio()}<br>"
            )
    except Exception as e:
        text += f"  - failed to load screen information {e}"

    if not as_html:
        text = text.replace("<br>", "\n").replace("<b>", "").replace("</b>", "")
    return text


def connect(
    connectable: Connectable, func: ty.Callable, state: bool = True, source: str = "", silent: bool = False
) -> None:
    """Function that connects/disconnects."""
    try:
        connectable_func = connectable.connect if state else connectable.disconnect
        connectable_func(func)
    except Exception as exc:
        if not silent:
            text = (
                f"Failed to {'' if state else 'dis'}connect function; error='{exc}'; func={func};"
                f" connectable={connectable}"
            )
            if source:
                text += f"; source={source}"
            logger.trace(text)


def s(path: Path) -> str:
    """Return a short path."""
    return f"{path.parent.name}/{path.name}"


def hyper(link: Path | str, value: str | Path | None = None, prefix: str = "goto") -> str:
    """Parse into a hyperlink."""
    if value is None:
        value = link
    if isinstance(link, Path):
        ret = f"<a href='{link.as_uri()}'>{value}</a>"
    elif prefix:
        ret = f"<a href='{prefix}:{link}'>{value}</a>"
    else:
        ret = f"<a href='{link}'>{value}</a>"
    return ret
