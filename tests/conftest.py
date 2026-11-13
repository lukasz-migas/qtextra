"""Configuration for pytest."""

from collections.abc import Iterator
from typing import Any, TypeVar

import pytest
from pytestqt.qtbot import QtBot
from qtpy import API_NAME

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
    import pytestqt.plugin

    held: list[Any] = []
    add_widget = QtBot.addWidget
    close_widgets = pytestqt.plugin._close_widgets

    def _add_widget(self: QtBot, widget: Any, *args: Any, **kwargs: Any) -> None:
        held.append(widget)
        add_widget(self, widget, *args, **kwargs)

    def _close_live_widgets(item: pytest.Item) -> None:
        # widgets deleted on the C++ side during the test (e.g. WA_DeleteOnClose) are still referenced here, so
        # drop them before pytest-qt tries to close them
        widgets = getattr(item, "qt_widgets", None)
        if widgets:
            item.qt_widgets = [(ref, func) for ref, func in widgets if not _is_deleted(ref())]
        close_widgets(item)

    monkeypatch.setattr(QtBot, "addWidget", _add_widget)
    monkeypatch.setattr(pytestqt.plugin, "_close_widgets", _close_live_widgets)
    yield
    held.clear()


def _is_deleted(widget: Any) -> bool:
    """Return whether the C++ object behind a Qt wrapper no longer exists."""
    if widget is None:
        return True
    if API_NAME.startswith("PySide"):
        import shiboken6

        return not shiboken6.isValid(widget)
    from qtpy import sip

    return sip.isdeleted(widget)


@pytest.fixture(scope="session", autouse=False)
def add_qt_widget() -> Any:
    """Return a helper that registers a widget with ``qtbot``."""

    def _add(qtbot: Any, widget: T) -> T:
        qtbot.addWidget(widget)
        return widget

    return _add
