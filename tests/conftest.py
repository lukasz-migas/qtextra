"""Configuration for pytest."""

from collections.abc import Iterator
from typing import Any, TypeVar

import pytest
from pytestqt.qtbot import QtBot

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


@pytest.fixture(autouse=True)
def _hold_qtbot_widgets(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Keep widgets registered with ``qtbot.addWidget`` alive until pytest-qt closes them in teardown.

    pytest-qt only keeps weak references. A widget that sits in a Python reference cycle is then freed by
    the cyclic garbage collector at a random moment once the test function returns - if that happens while
    Qt is painting it (pytest-qt processes events right after the test), PySide6 crashes with a segfault or
    'pure virtual method called'.
    """
    held: list[Any] = []
    add_widget = QtBot.addWidget

    def _add_widget(self: QtBot, widget: Any, *args: Any, **kwargs: Any) -> None:
        held.append(widget)
        add_widget(self, widget, *args, **kwargs)

    monkeypatch.setattr(QtBot, "addWidget", _add_widget)
    yield
    held.clear()


@pytest.fixture(scope="session", autouse=False)
def add_qt_widget() -> Any:
    """Return a helper that registers a widget with ``qtbot``."""

    def _add(qtbot: Any, widget: T) -> T:
        qtbot.addWidget(widget)
        return widget

    return _add
