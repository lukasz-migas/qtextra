"""Typing utilities."""
import typing as ty
from enum import Enum

Callback = ty.Sequence[ty.Callable]


class TaskState(str, Enum):
    """State of the task."""

    QUEUED = "queued"
    RUNNING = "running"
    PAUSING = "pausing"
    PAUSED = "paused"
    INCOMPLETE = "incomplete"
    FINISHED = "finished"
    PART_FAILED = "part-failed"
    FAILED = "failed"
    CANCELLING = "cancelling"
    CANCELLED = "cancelled"
