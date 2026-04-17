from typing import Any, TypeVar

T = TypeVar("T")


def add_widget(qtbot: Any, widget: T) -> T:
    """Register a widget with ``qtbot`` and return it."""
    qtbot.addWidget(widget)
    return widget
