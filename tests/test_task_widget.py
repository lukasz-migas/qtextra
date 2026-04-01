from __future__ import annotations

import pytest

from qtextra.queue.item import TaskWidget


class _DialogRaisingRuntimeError:
    def update_progress(self) -> None:
        raise RuntimeError("dialog closed")


class _DialogRaisingValueError:
    def update_progress(self) -> None:
        raise ValueError("unexpected failure")


def test_task_widget_update_progress_swallows_runtime_error(qtbot) -> None:
    widget = TaskWidget()
    qtbot.addWidget(widget)
    widget.dlg_info = _DialogRaisingRuntimeError()

    widget.update_progress()

    assert widget.dlg_info is None


def test_task_widget_update_progress_propagates_unexpected_exceptions(qtbot) -> None:
    widget = TaskWidget()
    qtbot.addWidget(widget)
    dialog = _DialogRaisingValueError()
    widget.dlg_info = dialog

    with pytest.raises(ValueError, match="unexpected failure"):
        widget.update_progress()

    assert widget.dlg_info is dialog
