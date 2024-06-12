import re
import typing as ty
from contextlib import suppress

from qtextra.typing import Callback

if ty.TYPE_CHECKING:
    from qtextra.queue.task import MasterTask


def iterable_callbacks(func: ty.Optional[ty.Union[ty.Callable, Callback]]) -> ty.Sequence[ty.Callable]:
    """Callbacks should always be a sequence."""
    if func is None:
        return []
    elif isinstance(func, ty.Sequence):
        return func
    return [func]


def _safe_call(
    func: ty.Optional[ty.Sequence[ty.Callable]], task: ty.Optional["MasterTask"] = None, which: str = ""
) -> None:
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
"""
)


def escape_ansi(text: str) -> str:
    """Try auto-escaping ANSI codes.

    See: https://stackoverflow.com/questions/14693701/how-can-i-remove-the-ansi-escape-sequences-from-a-string-in-python
    """
    try:
        return ansi_escape.sub("", text)
    except Exception:
        return text
