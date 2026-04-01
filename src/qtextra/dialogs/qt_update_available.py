"""Update-available dialog."""

from __future__ import annotations

from pydantic import BaseModel
from qtpy.QtCore import Qt, Signal
from qtpy.QtWidgets import QWidget

import qtextra.helpers as hp
from qtextra.widgets.qt_dialog import QtDialog


class UpdateInfo(BaseModel):
    """Data model for an available-update notification.

    Parameters
    ----------
    current_version : str
        The version the user is currently running.
    available_version : str
        The version that is available to install.
    app_name : str
        Human-readable application name shown in the default message.
    whats_new_url : str | None
        When provided, a "what's new" hyperlink is shown in the body.
    message : str | None
        Custom body message; falls back to a generic string when ``None``.
    """

    current_version: str
    available_version: str
    app_name: str = "Application"
    whats_new_url: str | None = None
    message: str | None = None


class UpdateAvailableDialog(QtDialog):
    """Dialog informing the user that a newer version of the application is available."""

    evt_update_requested = Signal()
    evt_remind_later_requested = Signal()
    evt_whats_new_requested = Signal()
    evt_dismissed = Signal()

    def __init__(self, info: UpdateInfo, parent: QWidget | None = None) -> None:
        self.info = info
        self._result_action = "dismissed"
        super().__init__(parent, title="Update available")
        self.setMinimumSize(760, 460)
        self.resize(980, 560)

    # noinspection PyAttributeOutsideInit
    def make_panel(self):
        """Build and return the dialog layout."""
        title_lbl = hp.make_label(self, "Update available", bold=True, font_size=24)
        header = hp.make_h_layout(title_lbl)

        message = self.info.message or f"A new version of {self.info.app_name} is available!"
        msg_lbl = hp.make_label(self, message, wrap=True, font_size=14)

        self.whats_new_lbl = hp.make_label(self, enable_url=True)
        if self.info.whats_new_url:
            self.whats_new_lbl.setText('See <a href="whats_new">what\'s new</a> in this version.')
            self.whats_new_lbl.linkActivated.connect(self._on_whats_new_clicked)
        else:
            self.whats_new_lbl.hide()

        # Version comparison grid
        grid = hp.make_grid_layout(column_to_stretch={0: 1, 2: 1}, spacing=8)

        current_caption = hp.make_label(self, "Current version", bold=True, alignment=Qt.AlignmentFlag.AlignCenter)

        self.current_ver_lbl = hp.make_label(
            self, self.info.current_version, alignment=Qt.AlignmentFlag.AlignHCenter, object_name="72px_300w"
        )

        arrow_lbl = hp.make_label(self, "⟶", alignment=Qt.AlignmentFlag.AlignCenter, object_name="96px")

        new_caption = hp.make_label(self, "Now available", bold=True)
        new_caption.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        self.new_ver_lbl = hp.make_label(
            self, self.info.available_version, alignment=Qt.AlignmentFlag.AlignHCenter, object_name="72px_300w"
        )

        grid.addWidget(current_caption, 0, 0, Qt.AlignmentFlag.AlignHCenter)
        grid.addWidget(arrow_lbl, 0, 1, 2, 1, Qt.AlignmentFlag.AlignCenter)
        grid.addWidget(new_caption, 0, 2, Qt.AlignmentFlag.AlignHCenter)
        grid.addWidget(self.current_ver_lbl, 1, 0, Qt.AlignmentFlag.AlignHCenter)
        grid.addWidget(self.new_ver_lbl, 1, 2, Qt.AlignmentFlag.AlignHCenter)

        self.not_now_btn = hp.make_btn(
            self,
            "Not now",
            func=self._on_not_now_clicked,
            object_name="cancel_btn",
        )
        self.update_btn = hp.make_btn(
            self,
            "Update",
            func=self._on_update_clicked,
            object_name="update_btn",
        )
        self.update_btn.setDefault(True)
        self.update_btn.setAutoDefault(True)

        footer = hp.make_h_layout(stretch_before=True, spacing=12)
        footer.addWidget(self.not_now_btn)
        footer.addWidget(self.update_btn)

        layout = hp.make_v_layout(spacing=16, margin=(20, 16, 20, 16))
        layout.addLayout(header)
        layout.addWidget(hp.make_h_line(self))
        layout.addWidget(msg_lbl)
        layout.addWidget(self.whats_new_lbl)
        layout.addLayout(grid, 1)
        layout.addWidget(hp.make_h_line(self))
        layout.addLayout(footer)
        return layout

    def _on_whats_new_clicked(self, _: str) -> None:
        self._result_action = "whats_new"
        self.evt_whats_new_requested.emit()

    def _on_not_now_clicked(self) -> None:
        self._result_action = "later"
        self.evt_remind_later_requested.emit()
        self.reject()

    def _on_update_clicked(self) -> None:
        self._result_action = "update"
        self.evt_update_requested.emit()
        self.accept()

    def reject(self) -> None:
        """Emit ``dismissed`` if no other action was taken before closing."""
        if self._result_action == "dismissed":
            self.evt_dismissed.emit()
        super().reject()

    # ── Convenience ───────────────────────────────────────────────────────────

    @property
    def result_action(self) -> str:
        """Return one of: ``update``, ``later``, ``whats_new``, ``dismissed``."""
        return self._result_action
