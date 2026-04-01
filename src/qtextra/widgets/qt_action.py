"""QtAction."""

import typing as ty
from contextlib import suppress

import qtawesome
from qtpy.QtWidgets import QAction

from qtextra.assets import get_icon
from qtextra.config import THEMES


class QtQtaAction(QAction):
    """Icon."""

    _qta_data = None

    def __init__(self, *args: ty.Any, **kwargs: ty.Any):
        super().__init__(*args, **kwargs)
        with suppress(RuntimeError):
            THEMES.evt_theme_icon_changed.connect(self._update_qta)

    def set_qta(self, name: str, **kwargs: ty.Any):
        """Set QtAwesome icon."""
        name, kwargs_ = get_icon(name)
        kwargs.update(kwargs_)
        self._qta_data = (name, kwargs)
        with suppress(RuntimeError):
            icon = qtawesome.icon(name, **self._qta_data[1], color=THEMES.get_hex_color("icon"))
            self.setIcon(icon)

    def _update_qta(self):
        """Update qta icon."""
        if self._qta_data:
            name, kwargs = self._qta_data
            self.set_qta(name, **kwargs)
