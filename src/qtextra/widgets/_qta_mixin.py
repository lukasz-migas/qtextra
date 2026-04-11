"""Mixin class for QtAwesome widgets."""

from __future__ import annotations

import typing as ty
import warnings

import qtawesome
from loguru import logger
from qtpy.QtCore import QSize

from qtextra.assets import MISSING, get_icon
from qtextra.config import THEMES
from qtextra.typing import QtaSizePreset


class QtaMixin:
    """Mixin class for Qta widgets."""

    QTA_ICON_SIZE_FOLLOWS_WIDGET_SIZE: ty.ClassVar[bool] = False
    QTA_SIZE_MAP: ty.ClassVar[dict[QtaSizePreset, tuple[QSize, QSize]]] = {
        "xxsmall": (QSize(10, 10), QSize(10, 10)),
        "xsmall": (QSize(16, 16), QSize(16, 16)),
        "small": (QSize(20, 20), QSize(16, 16)),
        "normal": (QSize(20, 20), QSize(20, 20)),
        "average": (QSize(24, 24), QSize(24, 24)),
        "medium": (QSize(28, 28), QSize(28, 28)),
        "large": (QSize(40, 40), QSize(32, 32)),
        "xlarge": (QSize(60, 60), QSize(60, 60)),
        "xxlarge": (QSize(80, 80), QSize(80, 80)),
        "xxxlarge": (QSize(120, 120), QSize(120, 120)),
    }
    LEGACY_OBJECT_NAMES: ty.ClassVar[dict[QtaSizePreset, str]] = {preset: f"{preset}_icon" for preset in QTA_SIZE_MAP}

    _qta_data: tuple | None = None
    _checked_qta_data: tuple | None = None
    _icon_color: str | None = None

    setIcon: ty.Callable
    setMinimumSize: ty.Callable
    setMaximumSize: ty.Callable
    setIconSize: ty.Callable
    setObjectName: ty.Callable
    setProperty: ty.Callable
    objectName: ty.Callable

    @classmethod
    def _get_qta_size_spec(cls, preset: QtaSizePreset) -> tuple[QSize, QSize]:
        """Return the widget and icon size for a preset."""
        try:
            widget_size, icon_size = cls.QTA_SIZE_MAP[preset]
        except KeyError as exc:
            presets = ", ".join(cls.QTA_SIZE_MAP)
            raise ValueError(f"Unknown qta size preset '{preset}'. Expected one of: {presets}.") from exc
        if cls.QTA_ICON_SIZE_FOLLOWS_WIDGET_SIZE:
            return QSize(widget_size), QSize(widget_size)
        return QSize(widget_size), QSize(icon_size)

    @classmethod
    def _normalize_qta_size(cls, size: int | QSize | tuple[int, int]) -> QSize:
        """Normalise a qta size input to a QSize."""
        if isinstance(size, QSize):
            return QSize(size)
        if isinstance(size, int):
            return QSize(size, size)
        return QSize(*size)

    def _clear_legacy_size_object_name(self) -> None:
        """Remove the legacy size object name if it is currently set."""
        object_name = self.objectName()
        if object_name in self.LEGACY_OBJECT_NAMES.values():
            self.setObjectName("")

    def _apply_qta_size(
        self,
        widget_size: QSize,
        icon_size: QSize,
        *,
        preset: QtaSizePreset | None = None,
        use_legacy_object_name: bool = False,
    ) -> None:
        """Apply widget and icon sizes directly in code."""
        self.setMinimumSize(widget_size)
        self.setMaximumSize(widget_size)
        self.setIconSize(icon_size)
        self.setProperty("qta_size_preset", preset)
        if preset and use_legacy_object_name:
            self.setObjectName(self.LEGACY_OBJECT_NAMES[preset])
        else:
            self._clear_legacy_size_object_name()

    def _set_legacy_size_preset(self, preset: QtaSizePreset) -> None:
        """Apply a preset while preserving the legacy object name contract."""
        widget_size, icon_size = self._get_qta_size_spec(preset)
        self._apply_qta_size(widget_size, icon_size, preset=preset, use_legacy_object_name=True)

    def _warn_deprecated_size_method(self, legacy_name: str, replacement: str) -> None:
        """Emit a standard deprecation warning for size helpers."""
        warnings.warn(
            f"`{legacy_name}` is deprecated, use `{replacement}` instead.",
            DeprecationWarning,
            stacklevel=2,
        )

    def _set_icon(self, *args: ty.Any, **kwargs: ty.Any) -> None:
        """Set icon."""
        try:
            icon = qtawesome.icon(*args, **kwargs)
            self.setIcon(icon)
        except Exception as exc:  # noqa: BLE001
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
        """Set a named qta size preset."""
        if not any((xxsmall, xsmall, small, normal, average, medium, large, xlarge, xxlarge)):
            return
        self._warn_deprecated_size_method("set_default_size", "set_qta_size_preset")
        if xxsmall:
            self._set_legacy_size_preset("xxsmall")
        elif xsmall:
            self._set_legacy_size_preset("xsmall")
        elif small:
            self._set_legacy_size_preset("small")
        elif normal:
            self._set_legacy_size_preset("normal")
        elif average:
            self._set_legacy_size_preset("average")
        elif medium:
            self._set_legacy_size_preset("medium")
        elif large:
            self._set_legacy_size_preset("large")
        elif xlarge:
            self._set_legacy_size_preset("xlarge")
        elif xxlarge:
            self._set_legacy_size_preset("xxlarge")

    def set_qta_size_preset(self, preset: QtaSizePreset) -> None:
        """Apply a named qta size preset."""
        widget_size, icon_size = self._get_qta_size_spec(preset)
        self._apply_qta_size(widget_size, icon_size, preset=preset)

    def set_qta_size(self, size: int | QSize | tuple[int, int]) -> None:
        """Set an explicit fixed qta size."""
        qsize = self._normalize_qta_size(size)
        self._apply_qta_size(qsize, qsize)

    @classmethod
    def get_icon_size_for_name(cls, name: QtaSizePreset) -> tuple[str, tuple[int, int]]:
        """Get icon size for name."""
        warnings.warn(
            "`get_icon_size_for_name` is deprecated, use `QTA_SIZE_MAP` or `set_qta_size_preset` instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        widget_size, _ = cls._get_qta_size_spec(name)
        return cls.LEGACY_OBJECT_NAMES[name], (widget_size.width(), widget_size.height())

    def set_xxsmall(self) -> None:
        """Set the xxsmall qta size preset."""
        self._warn_deprecated_size_method("set_xxsmall", "set_qta_size_preset('xxsmall')")
        self._set_legacy_size_preset("xxsmall")

    def set_xsmall(self) -> None:
        """Set the xsmall qta size preset."""
        self._warn_deprecated_size_method("set_xsmall", "set_qta_size_preset('xsmall')")
        self._set_legacy_size_preset("xsmall")

    def set_small(self) -> None:
        """Set the small qta size preset."""
        self._warn_deprecated_size_method("set_small", "set_qta_size_preset('small')")
        self._set_legacy_size_preset("small")

    def set_normal(self) -> None:
        """Set the normal qta size preset."""
        self._warn_deprecated_size_method("set_normal", "set_qta_size_preset('normal')")
        self._set_legacy_size_preset("normal")

    def set_average(self) -> None:
        """Set the average qta size preset."""
        self._warn_deprecated_size_method("set_average", "set_qta_size_preset('average')")
        self._set_legacy_size_preset("average")

    def set_medium(self) -> None:
        """Set the medium qta size preset."""
        self._warn_deprecated_size_method("set_medium", "set_qta_size_preset('medium')")
        self._set_legacy_size_preset("medium")

    def set_large(self) -> None:
        """Set the large qta size preset."""
        self._warn_deprecated_size_method("set_large", "set_qta_size_preset('large')")
        self._set_legacy_size_preset("large")

    def set_xlarge(self) -> None:
        """Set the xlarge qta size preset."""
        self._warn_deprecated_size_method("set_xlarge", "set_qta_size_preset('xlarge')")
        self._set_legacy_size_preset("xlarge")

    def set_xxlarge(self) -> None:
        """Set the xxlarge qta size preset."""
        self._warn_deprecated_size_method("set_xxlarge", "set_qta_size_preset('xxlarge')")
        self._set_legacy_size_preset("xxlarge")

    def set_xxxlarge(self) -> None:
        """Set the xxxlarge qta size preset."""
        self._warn_deprecated_size_method("set_xxxlarge", "set_qta_size_preset('xxxlarge')")
        self._set_legacy_size_preset("xxxlarge")

    def _get_current_icon_size(self) -> QSize | None:
        """Return the currently applied icon size if the widget exposes it."""
        icon_size = getattr(self, "iconSize", None)
        if callable(icon_size):
            return QSize(icon_size())
        current_size = getattr(self, "_size", None)
        if isinstance(current_size, QSize):
            return QSize(current_size)
        return None

    def _update_qta(self) -> None:
        """Update qta icon."""
        if self._qta_data:
            name, kwargs = self._qta_data
            minimum_size = QSize(self.minimumSize())
            maximum_size = QSize(self.maximumSize())
            icon_size = self._get_current_icon_size()
            object_name = self.objectName()
            size_preset = self.property("qta_size_preset")
            self.set_qta(name, **kwargs)
            self.setMinimumSize(minimum_size)
            self.setMaximumSize(maximum_size)
            if icon_size is not None:
                self.setIconSize(icon_size)
            self.setProperty("qta_size_preset", size_preset)
            if object_name:
                self.setObjectName(object_name)

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
    setQtaSizePreset = set_qta_size_preset
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
