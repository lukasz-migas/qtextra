"""Typing utilities."""

import typing as ty
from enum import Enum

Callback = ty.Union[ty.Callable, ty.Sequence[ty.Callable]]
OptionalCallback = ty.Optional[ty.Union[ty.Callable, ty.Sequence[ty.Callable]]]
Orientation = ty.Literal["horizontal", "vertical"]
IconType = ty.Union[str, tuple[str, dict[str, ty.Any]]]
GifOption = ty.Literal["dots", "infinity", "oval", "circle", "square"]


class TaskState(str, Enum):
    """State of the task."""

    QUEUED = "queued"
    RUN_NEXT = "run-next"
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
    INVALID = "invalid"


class TaskProgress(str, Enum):
    """Progress of a task."""

    PENDING = "wait"
    COMPLETE = "check"
    INCOMPLETE = "cross"
    ACTIVE = "active"


class WorkerState(str, Enum):
    """Worker state."""

    FINISHED = "finished"
    NOT_ENOUGH_SPACE = "not_enough_space"


class ProcessState(str, Enum):
    """Process state."""

    PASS = "pass"
    FAIL = "fail"
    CANCEL = "cancel"


class TaskType(str, Enum):
    """Task types."""

    PROCESS = "process"
    THREAD = "thread"
    CLI = "console"


class State(str, Enum):
    """State."""

    COMPLETE = "check"
    INCOMPLETE = "cross"


class Connectable(ty.Protocol):
    """Protocol for connectable objects."""

    def connect(self, func: ty.Callable) -> ty.Any:
        """Connect function."""

    def disconnect(self, func: ty.Callable) -> ty.Any:
        """Disconnect function."""
