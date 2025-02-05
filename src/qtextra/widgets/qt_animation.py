"""Animation base."""

import os.path
from contextlib import contextmanager
from enum import auto

from napari.utils.misc import StringEnum
from qtpy.QtCore import QObject, QTimer, Signal, Slot


class LoopMode(StringEnum):
    """Looping mode for animating an axis.

    LoopMode.ONCE
        Animation will stop once movie reaches the max frame (if fps > 0) or the first frame (if fps < 0).
    LoopMode.LOOP
        Movie will return to the first frame after reaching the last frame, looping continuously until stopped.
    LoopMode.BACK_AND_FORTH
        Movie will loop continuously until stopped, reversing direction when the maximum or minimum frame has been
         reached.
    """

    ONCE = auto()
    LOOP = auto()
    BACK_AND_FORTH = auto()


LOOP_COUNTS = {
    LoopMode.ONCE: 1,
    LoopMode.LOOP: 1,
    LoopMode.BACK_AND_FORTH: 2,
}
LOOP_MODE_TRANSLATIONS = {LoopMode.ONCE: "Once", LoopMode.LOOP: "Loop", LoopMode.BACK_AND_FORTH: "Back-and-forth"}


class QtAnimationBase(QObject):
    """Animation base.

    This class is responsible for animating/progressing through set of frames. This can include different ion images,
    mass spectra, m/z vs dt heatmaps or different ion mobility bins. The class should not be used directly, but rather
    subclassed and the `setup` and `update` methods must be implemented.

    Attributes
    ----------
    timer : QTimer
        Instance of the timer that takes care of updates.
    is_running : bool
        Flag to indicate whether the animator is running.
    interval : int
        Interval between each update (in ms)
    step : int
        Step size - this determines whether an update should occur on subsequent frames or some  frames should be
        skipped.
    current : int
        Current frame.
    min_point : int
        Minimum value to start animation from.
    max_point : int
        Maximum value where the animation should stop or reset.
    loop_mode : LoopMode
        Enum that determines what should happen when animation reaches its final frame. See `LoopMode` for available
        modes.

    Private Attributes
    ------------------
    _stop : bool
        Flag to indicate that animation was or should be stopped.
    """

    # event to lock certain ui elements when an action is taking place
    evt_lock = Signal(bool)
    # triggered when animation had started
    evt_started = Signal()
    # triggered when animation is finished
    evt_finished = Signal()
    # triggered whenever class is reset
    evt_reset = Signal()
    # triggered whenever animation was started or stopped
    evt_active = Signal(bool)
    # triggered when next frame is requested
    evt_next_requested = Signal(int)

    # triggered when writer has been setup
    evt_writer_setup = Signal()
    # triggered when writer had been updated
    evt_writer_updated = Signal(int, int)
    # triggered when writer had been closed
    evt_writer_finished = Signal()

    def __init__(self, parent, fps):
        QObject.__init__(self, parent)
        # timer
        self.timer = QTimer(self)

        self._stop: bool = False  # flag to indicate to stop the animation
        self.is_running: bool = False
        self.interval: int = 0
        self.step: int = 1
        self.current, self.min_point, self.max_point = 0, None, None
        self.loop_mode = str(LoopMode.ONCE)
        self.dim_range = (0, 0, 1)

        # writer attributes
        self._writer = None
        self._writer_n_loops: int = 1
        self._writer_current_iter: int = 0
        self._writer_max_iter: int = 0
        self._writer_finished: bool = False
        self._writer_current_step: int = 0
        self._writer_max_step: int = 0

    def reset(self):
        """Reset."""
        self.is_running: bool = False
        self.interval: int = 0
        self.step: int = 1
        self.current, self.min_point, self.max_point = 0, None, None
        self.loop_mode = str(LoopMode.ONCE)
        self.dim_range = (0, 0, 1)

        # writer attributes
        self._writer = None
        self._writer_n_loops: int = 1
        self._writer_current_iter: int = 0
        self._writer_max_iter: int = 0
        self._writer_finished: bool = False
        self._writer_current_step: int = 0
        self._writer_max_step: int = 0

    def setup(self, *args, **kwargs):
        """Setup."""
        raise NotImplementedError("Must implement method")

    def update(self, *args, **kwargs):
        """Update."""
        raise NotImplementedError("Must implement method")

    def _animate(self, current: int):
        """Yield animation data."""

    @property
    def writer(self):
        """Get handle to the writer."""
        return self._writer

    @property
    def writer_max_iter(self) -> int:
        """Get maximum number of iterations the loop should go on for."""
        return self._writer_max_iter

    @writer_max_iter.setter
    def writer_max_iter(self, value):
        self._writer_max_iter = value
        self._writer_current_iter = value
        self._writer_current_step = 0
        self._writer_max_step = value * self.max_point

    def set_writer(
        self,
        filename: str,
        fps: int = 10,
        loop: int = 0,
        duration: float = 0.1,
        n_loops: int = 1,
        quality: int = 5,
        **kwargs,
    ):
        """Set writer where canvas data can be written to.

        Parameters
        ----------
        filename : str
            Path to the filename where the writer can write to
        fps : int
            Frames per second to be written to the file
        loop : int
            Flag to indicate how many loops should be written to the file. Value of 0 means that gif will
            loop forever.
        duration : float
            Time (in seconds) between each frame.
        n_loops : int
            The number of iterations that should be written to the file
        quality : int
            Number from 1 (lowest quality) to 9. Only applies to non-gif extensions.
        **kwargs
            Additional keyword arguments
        """
        import imageio

        if n_loops < 1:
            raise ValueError("The `n_loops` value must be larger than 1.")
        if fps < 1:
            raise ValueError("The `fps` value must be larger than 1.")

        if self._writer is not None:
            self.close_writer()

        if filename.endswith(".gif"):
            self._writer = imageio.get_writer(filename, mode="I", duration=duration, fps=fps, loop=loop)
        elif os.path.splitext(filename)[-1] in [".mov", ".avi", ".mpg", ".mpeg", ".mp4", ".mkv", ".wmv"]:
            self._writer = imageio.get_writer(filename, mode="I", fps=fps, quality=quality)
        self._writer_n_loops = n_loops
        self.writer_max_iter = LOOP_COUNTS[self.loop_mode] * n_loops
        self._writer_finished = False
        self.set_writer_extras(**kwargs)
        self.evt_writer_setup.emit()

    def set_writer_extras(self, **kwargs):
        """Set any extra parameters that the writer might require."""

    def close_writer(self):
        """Close writer."""
        if self._writer:
            self._writer.close()
            self._writer = None
            self._writer_current_iter = 0

    @Slot(float)
    def set_fps(self, fps: float):
        """Set the frames per second value for the animation.

        Parameters
        ----------
        fps : float
            Frames per second for the animation.
        """
        if fps == 0:
            return self.finish()
        self.step = 1 if fps > 0 else -1  # negative fps plays in reverse
        self.interval = 1000 / abs(fps)

    @Slot(str)
    def set_loop_mode(self, mode: str):
        """Set the loop mode for the animation.

        Parameters
        ----------
        mode : str
            Loop mode for animation.
            Available options for the loop mode string enumeration are:
            - LoopMode.ONCE
                Animation will stop once movie reaches the max frame
                (if fps > 0) or the first frame (if fps < 0).
            - LoopMode.LOOP
                Movie will return to the first frame after reaching
                the last frame, looping continuously until stopped.
            - LoopMode.BACK_AND_FORTH
                Movie will loop continuously until stopped,
                reversing direction when the maximum or minimum frame
                has been reached.
        """
        self.loop_mode = LoopMode(mode)

    def start(self):
        """Start animation."""
        self._stop, self.is_running = False, True
        self.evt_active.emit(True)
        self.timer.singleShot(int(self.interval), self.advance)

    @contextmanager
    def pause(self):
        """Pause timer and then restart it."""
        if not self.is_running:
            raise ValueError("Cannot pause timer that is not running")
        self.timer.stop()
        yield
        self.timer.singleShot(int(self.interval), self.advance)

    def restart(self):
        """Restart animation."""
        self.finish()
        self.start()

    def finish(self):
        """Emit the finished event signal."""
        self._stop, self.is_running = True, False
        self.timer.stop()
        self.evt_active.emit(False)
        self.evt_finished.emit()

        if self._writer and self._writer_current_iter == 0:
            self._writer_finished = True
            self.evt_writer_finished.emit()

    def advance(self):
        """Advance the current frame in the animation.

        Takes dims scale into account and restricts the animation to the
        requested frame_range, if entered.
        """
        if self._stop:
            return

        self.current += self.step * self.dim_range[2]
        if self.current < self.min_point:
            self._writer_current_iter -= 1
            if self.loop_mode == LoopMode.BACK_AND_FORTH:  # 'loop_back_and_forth'
                self.step *= -1
                self.current = self.min_point + self.step * self.dim_range[2]
            elif self.loop_mode == LoopMode.LOOP:  # 'loop'
                self.current = self.max_point + self.current - self.min_point
            else:  # loop_mode == 'once'
                return self.finish()
        elif self.current >= self.max_point:
            self._writer_current_iter -= 1
            if self.loop_mode == LoopMode.BACK_AND_FORTH:  # 'loop_back_and_forth'
                self.step *= -1
                self.current = self.max_point + 2 * self.step * self.dim_range[2]
            elif self.loop_mode == LoopMode.LOOP:  # 'loop'
                self.current = self.min_point + self.current - self.max_point
            else:  # loop_mode == 'once'
                return self.finish()

        self.evt_next_requested.emit(self.current)
        # using a singleShot timer here instead of timer.start() because
        # it makes it easier to update the interval using signals/slots
        self.timer.singleShot(int(self.interval), self.advance)
