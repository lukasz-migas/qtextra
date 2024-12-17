"""Typing utilities."""

import typing as ty
from enum import Enum

Callback = ty.Union[ty.Callable, ty.Sequence[ty.Callable]]
Orientation = ty.Literal["horizontal", "vertical"]


class TaskState(str, Enum):
    """State of the task."""

    QUEUED = "queued"
    RUN_NEXT = "run_next"
    RUNNING = "running"
    PAUSING = "pausing"
    PAUSED = "paused"
    INCOMPLETE = "incomplete"
    FINISHED = "finished"
    PART_FAILED = "part-failed"
    FAILED = "failed"
    CANCELLING = "cancelling"
    CANCELLED = "cancelled"
    LOCKED = "locked"


class WorkerState(str, Enum):
    """Worker state."""

    FINISHED = "finished"
    NOT_ENOUGH_SPACE = "not_enough_space"
