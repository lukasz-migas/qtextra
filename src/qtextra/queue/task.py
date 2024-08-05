"""Task."""

from __future__ import annotations

from time import time as time_

from qtextra.typing import TaskState


class Task:
    """Task.

    Parameters
    ----------
    task_id : str
        Task ID.
    commands : list[list[str]]
        List of commands.
    task_name : str, optional
        Task name, by default "Task".
    state : TaskState, optional
        Task state, by default TaskState.QUEUED.
    task_name_repr: : str, optional
        Task title representation, by default None. If specified, it will be used in the UI as is instead of the 'hyper'
        representation.
    """

    task_id: str
    commands: list[list[str]]
    task_name: str
    task_name_repr: str | None = None
    state: TaskState
    stdout_data: list[str]
    stdout: str

    command_index: int = 0
    active: bool = False
    locked: bool = False
    start_time: float | None = None
    end_time: float | None = None

    def __init__(
        self,
        task_id: str,
        commands: list[list[str]],
        task_name: str = "Task",
        state: TaskState = TaskState.QUEUED,
        task_name_repr: str | None = None,
        task_name_tooltip: str | None = None,
    ):
        self.task_id = task_id
        self.task_name = task_name
        self.task_name_repr = task_name_repr
        self.task_name_tooltip = task_name_tooltip
        self.commands = commands
        self.state = state
        self.stdout = ""
        self.stdout_data = []

    @property
    def pretty_info(self) -> str:
        """Return pretty representation of the info."""
        return f"{self.command_index + 1}/{len(self.commands)} commands"

    @property
    def duration(self) -> float:
        """Return duration."""
        if self.start_time == 0 or self.start_time is None or self.end_time == 0 or self.end_time is None:
            return 0
        return self.end_time - self.start_time

    @property
    def current_duration(self) -> float:
        """Return duration at this moment in time."""
        if self.start_time == 0 or self.start_time is None:
            return 0
        return time_() - self.start_time

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
        if self.end_time is None:
            self.end_time = time_()
        self.locked = False

    def set_command_index(self, index: int) -> None:
        """Set command index."""
        self.command_index = index

    @property
    def current_std_out(self) -> str:
        """Return current stdout."""
        if len(self.stdout_data) > 10:
            return "\n".join(self.stdout_data[-10:])
        return "\n".join(self.stdout_data)

    def append_output(self, stdout: str | None = None) -> None:
        """Append output."""
        if stdout:
            self.stdout_data.append(stdout)
