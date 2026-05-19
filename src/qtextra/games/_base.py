"""Shared base classes for all mini-game board widgets and dialogs."""

from __future__ import annotations

from qtpy.QtCore import Qt, QTimer
from qtpy.QtGui import QColor
from qtpy.QtWidgets import QHBoxLayout, QSizePolicy, QVBoxLayout, QWidget

import qtextra.helpers as hp
from qtextra.config.theme import THEMES


class GameBoardWidget(QWidget):
    """Base QWidget for painting a mini-game board.

    Provides shared state storage and a game-over overlay colour helper.
    Subclasses implement :meth:`paintEvent` and :meth:`sizeHint`.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the board widget."""
        super().__init__(parent)
        self._state: object = None
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_state(self, state: object) -> None:
        """Store *state* and schedule a repaint."""
        self._state = state
        self.update()

    def _game_over_overlay(self, alpha: int = 70) -> QColor:
        """Return a semi-transparent error colour for the game-over overlay."""
        color = QColor(THEMES.get_hex_color("error"))
        color.setAlpha(alpha)
        return color


class GameDialogMixin:
    """Mixin providing shared timer, pause, restart, and UI-refresh logic.

    Mix this in before :class:`~qtextra.widgets.qt_dialog.QtDialog`::

        class MyDialog(GameDialogMixin, QtDialog): ...

    Concrete subclasses **must** implement:

    * :meth:`_create_board_widget` -- return the game-specific board widget.
    * :meth:`_instructions_text` -- return the instruction string.
    * :meth:`_do_restart` -- reset ``self._state`` for a new game.
    * :meth:`_do_advance_state` -- advance ``self._state`` by one tick.

    Optionally override (sensible defaults provided):

    * :meth:`_score_text` -- score label string (default ``"Score: <n>"``).
    * :meth:`_game_over_status` -- status when the game ends (default ``"Game over"``).
    * :meth:`_is_terminal_state` -- True when the game has reached an end state.
    * :meth:`_status_text` -- full status string (uses the above helpers).
    * :meth:`_setup_extra_header_widgets` -- insert extra widgets into the header row.
    * :meth:`_refresh_extra_labels` -- update any additional labels after a state change.
    """

    # ── abstract interface ─────────────────────────────────────────────────────

    def _create_board_widget(self) -> GameBoardWidget:
        """Return the game-specific board widget instance."""
        raise NotImplementedError

    def _instructions_text(self) -> str:
        """Return the instruction string shown below the board."""
        raise NotImplementedError

    def _do_restart(self) -> None:
        """Reset ``self._state`` for a new game."""
        raise NotImplementedError

    def _do_advance_state(self) -> None:
        """Advance ``self._state`` by one tick."""
        raise NotImplementedError

    # ── overridable defaults ───────────────────────────────────────────────────

    def _score_text(self) -> str:
        """Return the score label text."""
        return f"Score: {self._state.score}"  # type: ignore[attr-defined]

    def _game_over_status(self) -> str:
        """Return the status string when the game has ended."""
        return "Game over"

    def _is_terminal_state(self) -> bool:
        """Return True when the game has reached an end state."""
        return self._state.is_game_over  # type: ignore[attr-defined]

    def _status_text(self) -> str:
        """Return the full status bar string for the current game state."""
        if self._is_terminal_state():
            return self._game_over_status()
        if self._is_paused:  # type: ignore[attr-defined]
            return "Paused"
        return "Running"

    def _setup_extra_header_widgets(self, header_layout: QHBoxLayout) -> None:
        """Add extra widgets between the score label and the stretch before the status label."""

    def _refresh_extra_labels(self) -> None:
        """Update any additional labels after a state change."""

    # ── concrete shared implementation ────────────────────────────────────────

    def _setup_game_timer(self, interval_ms: int) -> None:
        """Create and connect the game timer.

        Call from ``__init__`` *after* ``super().__init__()`` so the board
        widget already exists when the timer fires.
        """
        self.timer = QTimer(self)  # type: ignore[attr-defined]
        self.timer.setInterval(interval_ms)
        self.timer.timeout.connect(self.advance_game)  # type: ignore[attr-defined]

    def make_panel(self) -> QVBoxLayout:
        """Build the standard game dialog layout."""
        self.score_label = hp.make_label(  # type: ignore[attr-defined]
            self,  # type: ignore[arg-type]
            "",
            bold=True,
            alignment=Qt.AlignmentFlag.AlignLeft,
        )
        self.status_label = hp.make_label(  # type: ignore[attr-defined]
            self,  # type: ignore[arg-type]
            "",
            alignment=Qt.AlignmentFlag.AlignRight,
        )

        header_layout = QHBoxLayout()
        header_layout.addWidget(self.score_label)
        self._setup_extra_header_widgets(header_layout)
        header_layout.addStretch(1)
        header_layout.addWidget(self.status_label)

        self.board_widget = self._create_board_widget()  # type: ignore[attr-defined]
        self.instructions_label = hp.make_label(  # type: ignore[attr-defined]
            self,  # type: ignore[arg-type]
            self._instructions_text(),
            wrap=True,
            alignment=Qt.AlignmentFlag.AlignHCenter,
        )

        self.pause_button = hp.make_btn(self, "Pause")  # type: ignore[attr-defined]
        self.pause_button.clicked.connect(self.toggle_pause)  # type: ignore[attr-defined]
        self.restart_button = hp.make_btn(self, "Restart")  # type: ignore[attr-defined]
        self.restart_button.clicked.connect(self.restart_game)  # type: ignore[attr-defined]

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.pause_button)
        button_layout.addWidget(self.restart_button)

        layout = hp.make_v_layout()
        layout.addLayout(header_layout)
        layout.addWidget(self.board_widget, stretch=1)
        layout.addWidget(self.instructions_label)
        layout.addLayout(button_layout)
        return layout

    def closeEvent(self, event: object) -> None:  # type: ignore[override]
        """Stop the timer when the dialog closes."""
        self.timer.stop()  # type: ignore[attr-defined]
        super().closeEvent(event)  # type: ignore[misc]

    def restart_game(self) -> None:
        """Reset the game state and start a new round."""
        self._do_restart()
        self._is_paused = False  # type: ignore[attr-defined]
        self.timer.start()  # type: ignore[attr-defined]
        self._refresh_ui()
        self.setFocus()  # type: ignore[attr-defined]

    def toggle_pause(self) -> None:
        """Pause or resume the running game."""
        if self._is_terminal_state():
            self.setFocus()  # type: ignore[attr-defined]
            return
        self._is_paused = not self._is_paused  # type: ignore[attr-defined]
        if self._is_paused:
            self.timer.stop()  # type: ignore[attr-defined]
        else:
            self.timer.start()  # type: ignore[attr-defined]
        self._refresh_ui()
        self.setFocus()  # type: ignore[attr-defined]

    def advance_game(self) -> None:
        """Advance the game by one timer tick."""
        if self._is_paused or self._is_terminal_state():  # type: ignore[attr-defined]
            return
        self._do_advance_state()
        if self._is_terminal_state():
            self.timer.stop()  # type: ignore[attr-defined]
        self._refresh_ui()

    def _refresh_ui(self) -> None:
        """Synchronize score label, status label, and board widget from state."""
        self.score_label.setText(self._score_text())  # type: ignore[attr-defined]
        self._refresh_extra_labels()
        self.status_label.setText(self._status_text())  # type: ignore[attr-defined]
        self.pause_button.setText("Resume" if self._is_paused else "Pause")  # type: ignore[attr-defined]
        self.board_widget.set_state(self._state)  # type: ignore[attr-defined]
