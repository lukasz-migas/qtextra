"""Task."""
from __future__ import annotations

from qtextra.typing import TaskState


class Task:
    """Task."""

    task_id: str
    task_name: str = "Master Task"
    state: TaskState = TaskState.QUEUED
    n_commands: int = 1

    def command_args(self) -> list[str]:
        """Command args."""
        return []


class MasterTask:
    """Master task wrapper."""

    task_id: str
    task_name: str = "Master Task"
    state: TaskState = TaskState.QUEUED
    tasks: list[Task]

    def summary(self) -> str:
        """Summary."""
        return f"Task ID: {self.task_id}"

    def get_task_for_id(self, task_id: str | None):
        """Get task for ID."""
        for task in self.tasks:
            if task.task_id == task_id:
                return task
        return None
