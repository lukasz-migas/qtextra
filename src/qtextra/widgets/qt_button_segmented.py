"""Segmented button widget."""

from __future__ import annotations

import typing as ty

from qtpy.QtCore import QSize, Qt, Signal  # type: ignore[attr-defined]
from qtpy.QtWidgets import QFrame, QHBoxLayout, QPushButton, QSizePolicy, QWidget

import qtextra.helpers as hp
from qtextra.widgets.qt_button_icon import QtImagePushButton


class QtSegmentedButton(QFrame):
    """Segmented button: a main text button with attached icon action buttons.

    Layout: [ Main Button Text | action1 | action2 | ... ]

    The whole widget renders as a single unified frame. Actions are appended
    dynamically via :meth:`add_action`.

    Example usage::

        btn = QtSegmentedButton("Run", parent)
        btn.evt_clicked.connect(on_run)
        btn.add_action("settings", "Configure", on_settings)
        btn.add_action("close", "Cancel", on_cancel)
    """

    evt_clicked = Signal()

    def __init__(
        self,
        text: str = "",
        parent: QWidget | None = None,
        *,
        flat: bool = False,
    ):
        super().__init__(parent=parent)
        self._actions: list[QtImagePushButton] = []
        self._separators: list[QWidget] = []

        self._main_btn = QPushButton(text, self)
        self._main_btn.setObjectName("mainButton")
        self._main_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self._main_btn.clicked.connect(self.evt_clicked)

        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)
        self._layout.addWidget(self._main_btn, stretch=1)

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        if flat:
            self.set_flat(True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_action(
        self,
        icon_name: str,
        tooltip: str = "",
        func: ty.Callable | list[ty.Callable] | None = None,
        *,
        size_preset: str = "average",
    ) -> QtImagePushButton:
        """Append an icon action button to the right side of the widget.

        Parameters
        ----------
        icon_name:
            Icon key from ``QTA_MAPPING`` (e.g. ``"settings"``) or a full
            qtawesome string (e.g. ``"mdi6.cog"``).
        tooltip:
            Tooltip text shown on hover.
        func:
            Callable or list of callables connected to the button's
            ``clicked`` signal.
        size_preset:
            QtaMixin size preset controlling icon/button size.

        Returns
        -------
        QtImagePushButton
            The newly created action button, for further customisation.
        """
        sep = hp.make_v_line(self)
        self._layout.addWidget(sep)
        self._separators.append(sep)

        btn = hp.make_qta_btn(
            self,
            icon_name,
            tooltip=tooltip,
            size_preset=size_preset,
            func=func,
        )
        btn.setProperty("transparent", True)

        self._layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)
        self._actions.append(btn)
        return btn

    @property
    def text(self) -> str:
        """Return the main button label."""
        return self._main_btn.text()

    def setText(self, text: str) -> None:
        """Set the main button label."""
        self._main_btn.setText(text)

    def setEnabled(self, enabled: bool) -> None:  # type: ignore[override]
        """Enable or disable the whole widget including all action buttons."""
        self._main_btn.setEnabled(enabled)
        for btn in self._actions:
            btn.setEnabled(enabled)

    def set_flat(self, flat: bool) -> None:
        """Toggle flat (borderless) appearance."""
        self.setProperty("flat", str(flat).lower())
        hp.polish_widget(self)

    def sizeHint(self) -> QSize:
        """Return combined size hint."""
        w = self._main_btn.sizeHint().width()
        h = self._main_btn.sizeHint().height()
        for btn in self._actions:
            bh = btn.sizeHint()
            w += bh.width()
            h = max(h, bh.height())
        w += len(self._separators)  # 1 px per separator
        margins = self.contentsMargins()
        w += margins.left() + margins.right()
        h += margins.top() + margins.bottom()
        return QSize(w, h)

    def minimumSizeHint(self) -> QSize:
        """Return minimum size hint."""
        return self.sizeHint()


if __name__ == "__main__":  # pragma: no cover

    def _main() -> None:
        import sys

        from qtextra.utils.dev import qframe

        app, frame, va = qframe(False)
        frame.setMinimumSize(500, 200)

        # Basic segmented button
        btn1 = QtSegmentedButton("Run pipeline", frame)
        btn1.evt_clicked.connect(lambda: print("Run clicked"))
        btn1.add_action("settings", "Configure", lambda: print("Settings clicked"))
        btn1.add_action("close", "Cancel", lambda: print("Cancel clicked"))
        va.addWidget(btn1)

        # With multiple actions
        btn2 = QtSegmentedButton("Export", frame)
        btn2.evt_clicked.connect(lambda: print("Export clicked"))
        btn2.add_action("save", "Save to file", lambda: print("Save clicked"))
        btn2.add_action("copy", "Copy to clipboard", lambda: print("Copy clicked"))
        btn2.add_action("delete", "Discard", lambda: print("Discard clicked"))
        va.addWidget(btn2)

        # Flat style
        btn3 = QtSegmentedButton("Flat button", frame, flat=True)
        btn3.evt_clicked.connect(lambda: print("Flat clicked"))
        btn3.add_action("add", "Add item", lambda: print("Add clicked"))
        va.addWidget(btn3)

        # No actions - plain main button
        btn4 = QtSegmentedButton("No actions", frame)
        btn4.evt_clicked.connect(lambda: print("No-action clicked"))
        va.addWidget(btn4)

        frame.show()
        sys.exit(app.exec_())

    _main()
