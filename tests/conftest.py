"""Configuration for pytest."""

from typing import Any, TypeVar

import pytest

T = TypeVar("T")
try:
    from PIL import Image
except ImportError:
    Image = None


@pytest.fixture(scope="session", autouse=False)
def get_icon_path(tmpdir_factory):
    """Get icon path."""
    if Image is None:
        return None
    icon = Image.new("RGB", (16, 16), color="red")
    path = str(tmpdir_factory.mktemp("data").join("img.png"))
    icon.save(path)
    return path


@pytest.fixture(scope="session", autouse=False)
def add_qt_widget() -> Any:
    """Return a helper that registers a widget with ``qtbot``."""

    def _add(qtbot: Any, widget: T) -> T:
        qtbot.addWidget(widget)
        return widget

    return _add
