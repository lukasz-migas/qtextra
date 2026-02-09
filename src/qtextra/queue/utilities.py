import re
import typing as ty
from contextlib import suppress

from koyo.system import IS_WIN
from loguru import logger
from qtpy.QtCore import QProcess

from qtextra.typing import Callback

if ty.TYPE_CHECKING:
    from qtextra.queue.task import Task


COLORS = {
    "error": "#ff121e",
    "warning": "#ff693c",
    "check_warning": "#ff693c",
    "success": "#1ed75f",
    "check": "#1ed75f",
    "normal": "#777777",
    "hint": "#00a6ff",
}
TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def set_process(process: QProcess, command: str, args: list[str]) -> None:
    """Set process."""
    process.setProgram(command)
    # Under Windows, the `setArguments` arguments are wrapped in a string which renders the arguments incorrect.
    # It's safer to simply join the arguments together and set them as one long string. The assumption being that
    # the arguments were properly set up in the first place!
    if IS_WIN:
        if hasattr(process, "setNativeArguments"):
            process.setNativeArguments(" ".join(args))  # type: ignore[arg-type]
        else:
            process.setArguments(args)  # type: ignore[arg-type]
    else:
        process.setArguments(args)  # type: ignore[arg-type]


def run_command(command: list[str]) -> None:
    """Execute command using the QProcess wrapper."""
    from qtextra.helpers import get_main_window

    program, args = command[0], command[1:]
    logger.trace(f"Running command: {program} {' '.join(args)}")

    process = QProcess(get_main_window())
    process.finished.connect(process.deleteLater)
    process.finished.connect(lambda exit_code, exit_status: logger.trace(f"Command finished with {exit_code}"))
    process.setProgram(program)
    # Under Windows, the `setArguments` arguments are wrapped in a string which renders the arguments
    # incorrect. It's safer to simply join the arguments  together and set them as one long string. The
    # assumption is that the arguments were properly setup in the first place!
    if IS_WIN and hasattr(process, "setNativeArguments"):
        process.setNativeArguments(" ".join(args))
    else:
        process.setArguments(args)
    process.start()


def listify_multiple(
    *values: str,
    key: str,
    pad: bool = True,
    join: bool = False,
    spacer: str = "",
    suffix: str = "",
) -> ty.List[str]:
    """Parse multiple inputs into single string."""
    ret = []
    for value in values:
        value = pad_str(value, suffix) if pad else f"{value!s}{suffix}"
        if join:
            ret.append(f"{key}{value}")
        else:
            ret.extend([key, value])
    return ret


def pad_str(value: ty.Any, suffix: str = "") -> str:
    """Pad string with quotes around out."""
    if IS_WIN:
        return f'"{value!s}{suffix}"'
    return f"{value!s}{suffix}"


def get_icon_state(errors: list[str]) -> tuple[str, str]:
    """Return icon state based on the error messages."""
    state = "check"
    if len([error for error in errors if 'class="warning"' in error]) > 0:
        state = "check_warning"
    if len([error for error in errors if 'class="error"' in error]) > 0:
        state = "error"
    return state, COLORS[state]


def format_interval(t: float) -> str:
    """
    Formats a number of seconds as a clock time, [H:]MM:SS.

    Parameters
    ----------
    t  : float
        Number of seconds.

    Returns
    -------
    out  : str
        [H:]MM:SS
    """
    if t is None:
        return "N/A"
    minutes, s = divmod(int(t), 60)
    h, m = divmod(minutes, 60)
    if h:
        return f"{h:d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def format_timestamp(timestamp: float) -> str:
    """Format timestamp so it returns a human-readable string."""
    import datetime

    if not timestamp:
        return "N/A"
    return datetime.datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")


def iterable_callbacks(func: ty.Optional[ty.Union[ty.Callable, Callback]]) -> ty.Sequence[ty.Callable]:
    """Callbacks should always be a sequence."""
    if func is None:
        return []
    if isinstance(func, ty.Sequence):
        return func
    return [func]


def _safe_call(func: ty.Optional[ty.Sequence[ty.Callable]], task: ty.Optional["Task"] = None, which: str = "") -> None:
    if func is not None:
        try:
            for _func in func:
                with suppress(Exception):
                    _func() if task is None else _func(task)
        except Exception as err:
            with suppress(Exception):
                print(f"Exception raised in call (source={which}): {err}; func={func}; task={task}")


# 7-bit C1 ANSI sequences
ansi_escape = re.compile(
    r"""
    \x1B  # ESC
    (?:   # 7-bit C1 Fe (except CSI)
        [@-Z\\-_]
    |     # or [ for CSI, followed by a control sequence
        \[
        [0-?]*  # Parameter bytes
        [ -/]*  # Intermediate bytes
        [@-~]   # Final byte
    )
""",
)


def escape_ansi(text: str) -> str:
    """Try auto-escaping ANSI codes.

    See: https://stackoverflow.com/questions/14693701/how-can-i-remove-the-ansi-escape-sequences-from-a-string-in-python
    """
    try:
        return ansi_escape.sub("", text)
    except Exception:
        return text


def format_command(commands: list[str], is_dev: bool = True) -> str:
    """Format command."""
    command = "; ".join(commands)
    if is_dev:
        command = command.replace("--no_color --debug", "--dev")
    else:
        command = command.replace("--no_color --debug", "--debug")
    return command


def decode(text: bytes) -> str:
    """Decode text."""
    try:
        return text.decode("utf-8-sig")
    except UnicodeDecodeError:
        return text.decode("latin1")
