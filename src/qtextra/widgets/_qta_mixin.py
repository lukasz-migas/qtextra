"""Mixin class for QtAwesome widgets."""

from __future__ import annotations

import typing as ty

import qtawesome
from qtpy.QtCore import QSize

from qtextra.assets import get_icon
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

    def set_qta(self, name: str, **kwargs: ty.Any) -> None:
        """Set QtAwesome icon."""
        name = get_icon(name)
        self._qta_data = (name, kwargs)
        color_ = kwargs.pop("color", None)
        color = color_ or self._icon_color or THEMES.get_hex_color("icon")
        try:
            icon = qtawesome.icon(name, **self._qta_data[1], color=color)
            self.setIcon(icon)
        except Exception:
            raise Exception(f"Failed to set icon: {name}")

    def _set_qta_icon(self, name: str, **kwargs: ty.Any) -> None:
        """Update icon without setting any attributes."""
        color = self._icon_color or THEMES.get_hex_color("icon")
        icon = qtawesome.icon(name, **kwargs, color=color)
        self.setIcon(icon)

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

    def set_size(self, size: ty.Tuple[int, int]) -> None:
        """Set maximum size of the icon."""
        size = QSize(*size)  # type: ignore[assignment]
        self.setMinimumSize(size)
        self.setMaximumSize(size)
        self.setIconSize(size)

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
            self.set_qta(name, **kwargs)
