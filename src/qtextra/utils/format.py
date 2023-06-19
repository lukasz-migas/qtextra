import io
import traceback
import typing as ty


def format_exception(exc_info: ty.Union[ty.Tuple, ty.List, Exception]):
    """Format exception."""
    if isinstance(exc_info, BaseException):
        exc_info = (type(exc_info), exc_info, exc_info.__traceback__)

    if not isinstance(exc_info, (list, tuple)):
        raise ValueError("Cannot format exception")

    # if len(exc_info) == 1:
    #     exc_info = exc_info[0]

    if len(exc_info) < 3:
        raise ValueError("Expected an item with >= 3 items!")

    sio = io.StringIO()
    traceback.print_exception(exc_info[0], exc_info[1], exc_info[2], None, sio)
    s = sio.getvalue()
    sio.close()
    if s[-1:] == "\n":
        s = s[:-1]
    return s
