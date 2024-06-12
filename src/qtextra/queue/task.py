"""Task."""

from __future__ import annotations

from qtextra.typing import TaskState


class Task:
    """Task."""

    task_id: str
    commands: list[list[str]]
    task_name: str
    state: TaskState

    _command_index: int = 0
    active: bool = False
    locked: bool = False
    start_time: float | None = None
    end_time: float | None = None

    def __init__(
        self, task_id: str, commands: list[list[str]], task_name: str = "Task", state: TaskState = TaskState.QUEUED
    ):
        self.task_id = task_id
        self.task_name = task_name
        self.commands = commands
        self.state = state

    def summary(self) -> str:
        """Summary."""
        return f"{self.task_name}: {self.state.name}"

    def command_args(self) -> list[list[str]]:
        """Command args."""
        return self.commands

    def command_iter(self, command_index: int = 0) -> list[str]:  # type: ignore[misc]
        """Command iterator."""
        if command_index:
            yield from self.commands[command_index:]
        else:
            yield from self.commands

    def is_active(self) -> bool:
        """Check if task is active."""
        return self.active

    def activate(self) -> None:
        """Activate task."""
        self.active = True

    def is_locked(self) -> bool:
        """Check if task is locked."""
        return self.locked

    def lock(self) -> None:
        """Lock task."""
        self.locked = False

    def set_command_index(self, index: int) -> None:
        """Set command index."""
        self._command_index = index
