"""Mixin class for QtAwesome widgets."""

from __future__ import annotations

import typing as ty

import qtawesome
from loguru import logger
from qtpy.QtCore import QSize

from qtextra.assets import MISSING, get_icon
from qtextra.config import THEMES


class QtaMixin:
    """Mixin class for Qta widgets."""

    _qta_data: tuple | None = None
    _checked_qta_data: tuple | None = None
    _icon_color: str | None = None

    setIcon: ty.Callable
    setMinimumSize: ty.Callable
    setMaximumSize: ty.Callable
    setIconSize: ty.Callable
    setObjectName: ty.Callable

    def _set_icon(self, *args: ty.Any, **kwargs: ty.Any) -> None:
        """Set icon."""
        try:
            icon = qtawesome.icon(*args, **kwargs)
            self.setIcon(icon)
        except Exception as exc:
            logger.warning(f"Failed to set icon: args={args};  kws={kwargs}\n{exc}")
            icon, _ = get_icon(MISSING)  # type: ignore[misc]
            icon = qtawesome.icon(icon, color=THEMES.get_hex_color("warning"))
            self.setIcon(icon)

    def set_qta(self, name: str | tuple[str, dict], **kwargs: ty.Any) -> None:
        """Set QtAwesome icon."""
        name_, kwargs_ = get_icon(name)  # type: ignore[misc]
        kwargs.update(kwargs_)
        self._qta_data = (name_, kwargs)
        color_ = kwargs.pop("color", None)
        if color_:
            self._icon_color = color_
        color = color_ or self._icon_color or THEMES.get_hex_color("icon")
        if "spin" in kwargs:
            kwargs["animation"] = qtawesome.Spin(self, autostart=True)
            kwargs.pop("spin")
        if "pulse" in kwargs:
            kwargs["animation"] = qtawesome.Pulse(self, autostart=True)
            kwargs.pop("pulse")
        self._set_icon(name_, **self._qta_data[1], color=color)

    def _set_qta_icon(self, name: str, **kwargs: ty.Any) -> None:
        """Update icon without setting any attributes."""
        color = self._icon_color or THEMES.get_hex_color("icon")
        self._set_icon(name, **kwargs, color=color)

    def set_default_size(
        self,
        xxsmall: bool = False,
        xsmall: bool = False,
        small: bool = False,
        normal: bool = False,
        average: bool = False,
        medium: bool = False,
        large: bool = False,
        xlarge: bool = False,
        xxlarge: bool = False,
    ) -> None:
        """Set size of the icon."""
        if xxsmall:
            self.set_xxsmall()
        elif xsmall:
            self.set_xsmall()
        elif small:
            self.set_small()
        elif normal:
            self.set_normal()
        elif average:
            self.set_average()
        elif medium:
            self.set_medium()
        elif large:
            self.set_large()
        elif xlarge:
            self.set_xlarge()
        elif xxlarge:
            self.set_xxlarge()

    def set_qta_size(self, size: ty.Tuple[int, int]) -> None:
        """Set maximum size of the icon."""
        size = QSize(*size)  # type: ignore[assignment]
        self.setMinimumSize(size)
        self.setMaximumSize(size)
        self.setIconSize(size)
        self.setObjectName("")

    @classmethod
    def get_icon_size_for_name(cls, name: str) -> tuple[str, tuple[int, int]]:
        """Get icon size for name."""
        if name == "xxsmall":
            return "xxsmall_icon", (10, 10)
        elif name in ("xsmall", "small"):
            return "xsmall_icon", (16, 16)
        elif name == "normal":
            return "normal_icon", (20, 20)
        elif name == "average":
            return "average_icon", (24, 24)
        elif name == "medium":
            return "medium_icon", (28, 28)
        elif name == "large":
            return "large_icon", (32, 32)
        elif name == "xlarge":
            return "xlarge_icon", (60, 60)
        elif name == "xxlarge":
            return "xxlarge_icon", (80, 80)
        elif name == "xxxlarge":
            return "xxxlarge_icon", (120, 120)
        return "average_icon", (24, 24)

    def set_xxsmall(self) -> None:
        """Set large."""
        self.setObjectName("xxsmall_icon")
        self.setIconSize(QSize(10, 10))

    def set_xsmall(self) -> None:
        """Set large."""
        self.setObjectName("xsmall_icon")
        self.setIconSize(QSize(16, 16))

    def set_small(self) -> None:
        """Set large font."""
        self.setObjectName("small_icon")
        self.setIconSize(QSize(16, 16))

    def set_normal(self) -> None:
        """Set medium font."""
        self.setObjectName("normal_icon")
        self.setIconSize(QSize(20, 20))

    def set_average(self) -> None:
        """Set medium font."""
        self.setObjectName("average_icon")
        self.setIconSize(QSize(24, 24))

    def set_medium(self) -> None:
        """Set medium font."""
        self.setObjectName("medium_icon")
        self.setIconSize(QSize(28, 28))

    def set_large(self) -> None:
        """Set large font."""
        self.setObjectName("large_icon")
        self.setIconSize(QSize(32, 32))

    def set_xlarge(self) -> None:
        """Set large."""
        self.setObjectName("xlarge_icon")
        self.setIconSize(QSize(60, 60))

    def set_xxlarge(self) -> None:
        """Set large."""
        self.setObjectName("xxlarge_icon")
        self.setIconSize(QSize(80, 80))

    def set_xxxlarge(self) -> None:
        """Set large."""
        self.setObjectName("xxxlarge_icon")
        self.setIconSize(QSize(120, 120))

    def _update_qta(self) -> None:
        """Update qta icon."""
        if self._qta_data:
            name, kwargs = self._qta_data
            size = self.minimumSize()
            self.set_qta(name, **kwargs)
            self.setMinimumSize(size)

    def _update_from_event(self, event):
        """Update theme based on event."""
        if event.type == "icon":
            self._update_qta()

    # Alias methods to offer Qt-like interface
    _setIcon = _set_icon
    setQta = set_qta
    _setQtaIcon = _set_qta_icon
    getIconSizeForName = get_icon_size_for_name
    setDefaultSize = set_default_size
    setQtaSize = set_qta_size
    setXXSmall = set_xxsmall
    setXSmall = set_xsmall
    setSmall = set_small
    setNormal = set_normal
    setAverage = set_average
    setMedium = set_medium
    setLarge = set_large
    setXLarge = set_xlarge
    setXXLarge = set_xxlarge
    setXXXLarge = set_xxxlarge
