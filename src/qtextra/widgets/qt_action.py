"""QtAction."""

import typing as ty
from contextlib import suppress
from sys import platform

import qtawesome
from qtpy.QtGui import QIcon
from qtpy.QtWidgets import QAction, QMenu, QMenuBar

from qtextra.assets import get_icon
from qtextra.config import THEMES


class QtQtaAction(QAction):
    """Icon."""

    def __init__(self, *args: ty.Any, **kwargs: ty.Any) -> None:
        super().__init__(*args, **kwargs)
        self._qta_data: tuple[str, dict[str, ty.Any]] | None = None
        self._native_menu = False
        with suppress(RuntimeError):
            THEMES.evt_theme_icon_changed.connect(self._update_qta)

    def set_qta(self, name: str, **kwargs: ty.Any) -> None:
        """Set QtAwesome icon."""
        self._qta_data = (name, kwargs.copy())
        self._update_qta()

    def _update_qta(self) -> None:
        """Update qta icon."""
        if self._qta_data is None:
            return
        original_name, original_kwargs = self._qta_data
        name, mapped_kwargs = get_icon(original_name)
        kwargs = {**original_kwargs, **mapped_kwargs}
        if self._native_menu:
            kwargs["color"] = "black"
        else:
            kwargs.setdefault("color", THEMES.get_hex_color("icon"))
        with suppress(RuntimeError):
            icon = qtawesome.icon(name, **kwargs)
            if self._native_menu:
                # QtAwesome caches its icons and its icon engine cannot be cloned.
                mask = QIcon()
                for size in (16, 32, 64):
                    mask.addPixmap(icon.pixmap(size, size))
                mask.setIsMask(True)
                icon = mask
            self.setIcon(icon)

    def _set_native_menu(self, native_menu: bool) -> None:
        if self._native_menu != native_menu:
            self._native_menu = native_menu
            self._update_qta()


def _associated_objects(action: QAction) -> list[ty.Any]:
    """Return the widgets or objects associated with an action across Qt versions."""
    associated = getattr(action, "associatedObjects", None) or action.associatedWidgets
    return associated()


def _is_native_menu(menu: QMenu) -> bool:
    """Check whether a menu belongs to a native macOS menu bar."""
    if platform != "darwin":
        return False
    pending = [menu]
    visited: set[QMenu] = set()
    while pending:
        current = pending.pop()
        if current in visited:
            continue
        visited.add(current)
        for associated in _associated_objects(current.menuAction()):
            if isinstance(associated, QMenuBar) and associated.isNativeMenuBar():
                return True
            if isinstance(associated, QMenu):
                pending.append(associated)
    return False


def _prepare_menu_icons(menu: QMenu) -> None:
    """Refresh actions just before the menu is displayed."""
    native_menu = _is_native_menu(menu)
    pending = [menu]
    visited: set[QMenu] = set()
    while pending:
        current = pending.pop()
        if current in visited:
            continue
        visited.add(current)
        for action in current.actions():
            if isinstance(action, QtQtaAction):
                action._set_native_menu(native_menu)
            if action.menu() is not None:
                pending.append(action.menu())
