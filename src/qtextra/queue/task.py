"""Task."""

from __future__ import annotations

from qtextra.typing import TaskState


class Task:
    """Task."""

    task_id: str
    task_name: str = "Master Task"
    state: TaskState = TaskState.QUEUED
    commands: list[list[str]]

    def command_args(self) -> list[list[str]]:
        """Command args."""
        return self.commands

    def command_iter(self) -> list[str]:  # type: ignore[misc]
        """Command iterator."""
        yield from self.commands
