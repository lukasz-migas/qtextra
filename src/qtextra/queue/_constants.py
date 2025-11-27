"""Constants for task state icons and colors."""

from qtextra.typing import TaskState

STATE_TO_ICON = {
    TaskState.QUEUED: "queue",
    TaskState.RUN_NEXT: "run_next",
    TaskState.RUNNING: "run",
    TaskState.PAUSING: "pause",
    TaskState.PAUSED: "pause",
    TaskState.FINISHED: "finish",
    TaskState.LOCKED: "lock",
    TaskState.PART_FAILED: "warning",
    TaskState.FAILED: "error",
    TaskState.CANCELLING: "cross_full",
    TaskState.CANCELLED: "cross_full",
}
STATE_TO_COLOR = {
    TaskState.QUEUED: "#00C851",
    TaskState.RUN_NEXT: "#e04196",
    TaskState.RUNNING: "#8E24AA",
    TaskState.PAUSING: "#1DE9B6",
    TaskState.PAUSED: "#e91e63",
    TaskState.LOCKED: "#e0115f",
    TaskState.FINISHED: "#4285F4",
    TaskState.PART_FAILED: "#ff3d00",
    TaskState.FAILED: "#ff4444",
    TaskState.CANCELLING: "#546e7a",
    TaskState.CANCELLED: "#263238",
}
STATE_TO_STATE = {
    TaskState.QUEUED: "wait",
    TaskState.RUNNING: "active",
    TaskState.FINISHED: "check",
    TaskState.FAILED: "cross",
    TaskState.CANCELLED: "cross",
    TaskState.PAUSED: "wait",
}
