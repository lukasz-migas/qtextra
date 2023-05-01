"""Utilities."""
import typing as ty

from loguru import logger

IS_WIN = False
IS_MAC = False
IS_LINUX = False


def get_module_path(module: str, filename: str) -> str:
    """Get module path."""
    import importlib.resources

    if not filename.endswith(".py"):
        filename += ".py"

    with importlib.resources.path(module, filename) as f:
        path = str(f)
    return path


def connect(connectable, func: ty.Callable, state: bool = True, source: str = ""):
    """Function that connects/disconnects."""
    try:
        connectable_func = connectable.connect if state else connectable.disconnect
        connectable_func(func)
    except Exception as exc:
        text = (
            f"Failed to {'' if state else 'dis'}connect function; error='{exc}'; func={func}; connectable={connectable}"
        )
        if source:
            text += f"; source={source}"
        logger.debug(text)
