"""Utilities."""
import sys
import typing as ty

from loguru import logger

IS_WIN = sys.platform == "win32"
IS_LINUX = sys.platform == "linux"
IS_MAC = sys.platform == "darwin"


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


def check_url(url: str) -> bool:
    """Parse typical URL.

    See: https://stackoverflow.com/a/50352868
    """
    from urllib.parse import urljoin, urlparse

    final_url = urlparse(urljoin(url, "/"))
    return all([final_url.scheme, final_url.netloc, final_url.path]) and len(final_url.netloc.split(".")) > 1
