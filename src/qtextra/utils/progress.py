"""tqdm-based progress manager."""

import typing as ty

from tqdm import tqdm

try:
    from napari.utils.events.event import EmitterGroup, Event
except ImportError:
    raise ImportError("please install napari using 'pip install napari'") from None


class Progress(tqdm):
    """This class inherits from tqdm and provides an interface for
    progress bars in the napari viewer. Progress bars can be created
    directly by wrapping an iterable or by providing a total number
    of expected updates.

    While this interface is primarily designed to be displayed in
    the viewer, it can also be used without a viewer open, in which
    case it behaves identically to tqdm and produces the progress
    bar in the terminal.

    See tqdm.tqdm API for valid args and kwargs:
    https://tqdm.github.io/docs/tqdm/

    Examples
    --------
    >>> def long_running(steps=10, delay=0.1):
    ...     for i in Progress(range(steps)):
    ...         sleep(delay)

    it can also be used as a context manager:

    >>> def long_running(steps=10, repeats=4, delay=0.1):
    ...     with progress(range(steps)) as pbr:
    ...         for i in pbr:
    ...             sleep(delay)

    or equivalently, using the `progrange` shorthand

    .. code-block:: python

        with progrange(steps) as pbr:
            for i in pbr:
                sleep(delay)

    For manual updates:

    >>> def manual_updates(total):
    ...     pbr = Progress(total=total)
    ...     sleep(10)
    ...     pbr.setDescription("Step 1 Complete")
    ...     pbr.update(1)
    ...     # must call pbr.close() when using outside for loop
    ...     # or context manager
    ...     pbr.close()

    """

    monitor_interval = 0  # set to 0 to disable the thread

    def __init__(
        self,
        iterable: ty.Optional[ty.Iterable] = None,
        desc: ty.Optional[str] = None,
        total: ty.Optional[int] = None,
        bar_format: str = "|{bar}| {n_fmt}/{total_fmt} [ETA: {remaining}/{elapsed} {rate_fmt}]",
        *args: ty.Any,
        **kwargs: ty.Any,
    ) -> None:
        self.events = EmitterGroup(value=Event, description=Event, overflow=Event, eta=Event, close=Event)
        self.is_init = True
        super().__init__(iterable, *args, desc=desc, total=total, bar_format=bar_format, **kwargs)

        if not self.desc:
            self.set_description("")
        self.is_init = False

    def __repr__(self) -> str:
        """Return description."""
        return self.desc

    def display(self, msg: ty.Optional[str] = None, pos: ty.Optional[int] = None) -> None:
        """Update the display and emit eta event."""
        # just plain tqdm if we don't have gui
        if not self.gui and not self.is_init:
            super().display(msg, pos)
            return
        etas = ""
        if self.total != 0:  # type: ignore[has-type]
            etas = str(self).split("|")[-1]
        self.events.eta(value=etas)

    def update(self, n: ty.Optional[float] = None) -> None:
        """Update progress value by n and emit value event."""
        super().update(n)
        self.events.value(value=self.n)

    def increment_with_overflow(self) -> None:
        """Update if not exceeding total, else set indeterminate range."""
        if self.n == self.total:  # type: ignore[has-type]
            self.total = 0
            self.events.overflow()
        else:
            self.update(1)

    def set_description(self, desc: str) -> None:
        """Update progress description and emit description event."""
        super().set_description(desc, refresh=True)
        self.events.description(value=desc)

    def close(self) -> None:
        """Close progress object and emit event."""
        if self.disable:
            return
        self.events.close()
        self.events.disconnect()
        super().close()
