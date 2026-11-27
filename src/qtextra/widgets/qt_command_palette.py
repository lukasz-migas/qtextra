"""A searchable command popup for Qt applications."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass, replace
from html import escape

from qtpy.compat import isalive
from qtpy.QtCore import QEvent, QObject, QPoint, QSize, Qt
from qtpy.QtGui import (  # type: ignore[attr-defined]
    QAction,
    QHideEvent,
    QIcon,
    QKeyEvent,
    QKeySequence,
    QShortcut,
    QShowEvent,
)
from qtpy.QtWidgets import (
    QFrame,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMenuBar,
    QSizePolicy,
    QWidget,
)

_DEFAULT_SHORTCUT = "Ctrl+Shift+P"
_RESULT_LIMIT = 10
_RECENT_LIMIT = 5
_MENU_SEPARATOR = " \u203a "


def _action_text(text: str) -> str:
    """Keep literal ampersands while stripping Qt mnemonics and legacy shortcut text."""
    return text.partition("\t")[0].replace("&&", "\0").replace("&", "").replace("\0", "&").strip()


@dataclass(frozen=True)
class _Command:
    title: str = ""
    callback: Callable[[], None] | None = None
    action: QAction | None = None
    category: str | None = None
    icon: QIcon | str | None = None
    keywords: tuple[str, ...] = ()
    enabled: Callable[[], bool] | None = None
    scope: str | None = None

    @property
    def key(self) -> object:
        """Identity used to remember recently run commands."""
        return self.action if self.action is not None else self.callback

    def is_available(self) -> bool:
        action = self.action
        if action is not None and not (
            isalive(action)  # type: ignore[no-untyped-call]
            and action.isVisible()
            and action.isEnabled()
            and bool(_action_text(action.text()))
        ):
            return False
        if self.enabled is None:
            return True
        try:
            return bool(self.enabled())
        except Exception:  # noqa: BLE001 - a failing app check must not break the palette
            return False


class _CommandRegistration:
    _registered: dict[object, _Command]
    _recent: list[object]
    _context_provider: Callable[[], str | None] | None

    def add_command(
        self,
        title: str,
        callback: Callable[[], None],
        *,
        category: str | None = None,
        icon: QIcon | str | None = None,
        keywords: Iterable[str] = (),
        enabled: Callable[[], bool] | None = None,
        scope: str | None = None,
    ) -> object:
        """Register a zero-argument callback and return its removal handle.

        An icon name refers to a qtextra icon. Keywords are optional search aliases.
        `enabled` hides the command whenever it returns False (or raises). Commands whose
        `scope` matches the current context (see :meth:`set_context_provider`) are listed first.
        """
        handle = object()
        self._registered[handle] = _Command(
            title, callback, category=category, icon=icon, keywords=tuple(keywords), enabled=enabled, scope=scope
        )
        self._registrations_changed()
        return handle

    def add_action(
        self,
        action: QAction,
        *,
        category: str | None = None,
        keywords: Iterable[str] = (),
        enabled: Callable[[], bool] | None = None,
        scope: str | None = None,
    ) -> object:
        """Register an existing QAction and return its removal handle.

        For menu actions, supplied metadata takes precedence over automatic discovery.
        """
        handle = object()
        self._registered[handle] = _Command(
            action=action, category=category, keywords=tuple(keywords), enabled=enabled, scope=scope
        )
        self._registrations_changed()
        return handle

    def set_context_provider(self, provider: Callable[[], str | None] | None) -> None:
        """Set a callable returning the current scope, e.g. the active tab.

        Commands registered with a matching `scope` are listed first when the search is
        empty and ranked ahead of equally good matches otherwise.
        """
        self._context_provider = provider

    def remove_command(self, handle: object) -> None:
        """Remove a manual registration. Menu actions remain available through discovery."""
        if self._registered.pop(handle, None) is not None:
            self._registrations_changed()

    def _registrations_changed(self) -> None:
        raise NotImplementedError


class CommandPaletteController(QObject, _CommandRegistration):
    """Window-owned registration and activation for a lazily created palette."""

    def __init__(self, window: QMainWindow, shortcut: str | QKeySequence | None = _DEFAULT_SHORTCUT) -> None:
        super().__init__(window)
        self._window = window
        self._registered = {}
        self._recent = []
        self._context_provider = None
        self._palette: QtCommandPalette | None = None
        if shortcut is not None:
            binding = QShortcut(QKeySequence(shortcut), window)
            binding.setContext(Qt.ShortcutContext.WindowShortcut)
            binding.setAutoRepeat(False)
            binding.activated.connect(self.open)

    def open(self) -> None:
        """Create the popup on demand and show it."""
        if self._palette is None:
            self._palette = QtCommandPalette(self._window)
            self._palette._registered = self._registered
            self._palette._recent = self._recent
        self._palette._context_provider = self._context_provider
        self._palette.open()

    def _registrations_changed(self) -> None:
        if self._palette is not None:
            self._palette._registrations_changed()


def _menu_actions(menu: QMenuBar | QMenu, path: tuple[str, ...] = ()) -> Iterator[tuple[QAction, str]]:
    for action in menu.actions():
        if action.isSeparator() or not action.isVisible() or not action.isEnabled():
            continue
        submenu = action.menu()
        title = _action_text(action.text())
        if submenu is not None:
            yield from _menu_actions(submenu, (*path, title) if title else path)
        elif title:
            yield action, _MENU_SEPARATOR.join(path)


def _match(text: str, query: str, letters: str) -> tuple[tuple[int, int], tuple[int, ...]] | None:
    """Rank exact, word-prefix, substring, and ordered subsequence matches."""
    folded = text.casefold()
    # Some characters expand on case folding, so map matches back to the visible string.
    positions = (
        [index for index, char in enumerate(text) for _ in char.casefold()] if len(folded) != len(text) else None
    )
    match_score = None
    match_positions: tuple[int, ...] = ()
    start = folded.find(query)
    while start != -1:
        rank = 0 if folded == query else 1 if start == 0 or not folded[start - 1].isalnum() else 2
        if match_score is None or rank < match_score[0]:
            match_score = (rank, 0)
            match_positions = tuple(start + offset for offset, char in enumerate(query) if not char.isspace())
        if rank < 2:
            break
        start = folded.find(query, start + 1)

    if match_score is None:
        start = folded.find(letters[0])
        while start != -1:
            indices = [start]
            for letter in letters[1:]:
                index = folded.find(letter, indices[-1] + 1)
                if index == -1:
                    break
                indices.append(index)
            if len(indices) != len(letters):
                break
            gaps = indices[-1] - start + 1 - len(indices)
            if match_score is None or gaps < match_score[1]:
                match_score = (3, gaps)
                match_positions = tuple(indices)
            start = folded.find(letters[0], start + 1)

    if match_score is None:
        return None
    if positions is not None:
        match_positions = tuple(positions[index] for index in match_positions)
    return match_score, match_positions


@dataclass(frozen=True)
class _Result:
    command: _Command
    title: str
    prefix: str
    positions: tuple[int, ...] = ()

    @property
    def label(self) -> str:
        return self.prefix + self.title

    def match(self, query: str, letters: str) -> tuple[tuple[int, int, int], _Result] | None:
        candidates = []
        for priority, text in enumerate((self.title, self.label, *self.command.keywords)):
            if priority == 1 and not self.prefix:
                continue
            match = _match(text, query, letters)
            if match is None:
                continue
            rank, positions = match
            if priority == 0:
                positions = tuple(index + len(self.prefix) for index in positions)
            elif priority > 1:
                positions = ()
            candidates.append(((*rank, priority), positions))
        if not candidates:
            return None
        score, positions = min(candidates)
        # Preserve visible highlights even if an alias was a stronger match.
        if not positions:
            positions = min((candidate for candidate in candidates if candidate[1]), default=(score, ()))[1]
        return score, replace(self, positions=positions)


class QtCommandPalette(QWidget, _CommandRegistration):
    """A themed, keyboard-driven command popup.

    Construct directly for a custom widget or dialog. Use :meth:`install` to
    defer creating the popup and discovering a main window's menu actions.
    """

    def __init__(self, parent: QWidget) -> None:
        import qtextra.helpers as hp
        from qtextra.assets import STYLE_PATH
        from qtextra.config import THEMES

        super().__init__(parent, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self._themes = THEMES
        self._stylesheet_template = (STYLE_PATH / "04_command_palette.qss").read_text(encoding="utf-8")
        self._registered = {}
        self._recent = []
        self._context_provider = None
        self._commands: list[_Command] = []
        self._matches: list[_Result] = []
        self._results_height_limit = 0

        self.setObjectName("command_palette")
        self.setAccessibleName("Command palette")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        panel = QFrame(self)
        panel.setObjectName("command_palette_panel")
        self._outer_layout = hp.make_v_layout(panel, margin=0, parent=self)
        self._search = hp.make_line_edit(
            panel, placeholder="Search for commands...", object_name="command_palette_search"
        )
        self._search.setAccessibleName("Search for commands")
        self._search.installEventFilter(self)
        self._search.returnPressed.connect(self._run_current)
        self._search.textChanged.connect(self._show_matches)
        self._search_icon = QAction(self._search)
        self._search.addAction(self._search_icon, self._search.ActionPosition.LeadingPosition)

        self._results = QListWidget(panel)
        self._results.setObjectName("command_palette_results")
        self._results.setAccessibleName("Matching commands")
        self._results.setFrameShape(QFrame.Shape.NoFrame)
        self._results.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._results.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._results.setUniformItemSizes(True)
        self._results.itemClicked.connect(self._run_item)
        self._empty = hp.make_label(
            panel, "No matching commands", alignment=Qt.AlignmentFlag.AlignCenter, object_name="command_palette_empty"
        )
        self._panel_layout = hp.make_v_layout(
            self._search, self._results, self._empty, margin=8, spacing=6, parent=panel
        )
        THEMES.evt_theme_changed.connect(self._apply_theme)
        THEMES.evt_theme_icon_changed.connect(self._update_icons)
        self._apply_theme()
        self._update_icons()

    @staticmethod
    def install(
        window: QMainWindow, *, shortcut: str | QKeySequence | None = _DEFAULT_SHORTCUT
    ) -> CommandPaletteController:
        """Install a window shortcut and return a controller without creating the popup.

        Pass `shortcut=None` to open the palette solely through the controller's
        `open()` method, for example from a toolbar button.
        """
        return CommandPaletteController(window, shortcut)

    def open(self) -> None:
        """Open the popup and focus its search field."""
        self.show()
        self._search.setFocus(Qt.FocusReason.PopupFocusReason)

    def showEvent(self, event: QShowEvent | None) -> None:
        """Refresh commands and place the popup near the top of the parent window."""
        super().showEvent(event)
        parent = self.parentWidget()
        window = (parent.window() if parent is not None else None) or self
        screen = window.screen()
        available = screen.availableGeometry() if screen is not None else window.frameGeometry()
        self._results_height_limit = max(self._row_height, available.height() - 120)
        self._commands = self._collect_commands()
        self._search.blockSignals(True)
        self._search.clear()
        self._search.blockSignals(False)
        self._show_matches("")
        width = min(600, max(240, window.width() - 32), available.width())
        self.resize(width, self.sizeHint().height())
        anchor = window.mapToGlobal(QPoint(window.width() // 2, 48))
        x = max(available.left(), min(anchor.x() - self.width() // 2, available.right() - self.width() + 1))
        y = max(available.top(), min(anchor.y(), available.bottom() - self.height() + 1))
        self.move(x, y)
        self._search.setFocus(Qt.FocusReason.PopupFocusReason)

    def hideEvent(self, event: QHideEvent | None) -> None:
        """Release references to actions discovered for this opening."""
        self._commands.clear()
        self._matches.clear()
        super().hideEvent(event)

    def eventFilter(self, watched: QObject | None, event: QEvent | None) -> bool:
        """Keep the keyboard focus in the search field while navigating results."""
        if watched is self._search and isinstance(event, QKeyEvent) and event.type() == QEvent.Type.KeyPress:
            key = event.key()
            if key == Qt.Key.Key_Escape:
                self.hide()
                return True
            if key in (Qt.Key.Key_Up, Qt.Key.Key_Down):
                step = 1 if key == Qt.Key.Key_Down else -1
                row = self._results.currentRow() + step
                if 0 <= row < self._results.count():
                    self._results.setCurrentRow(row)
                return True
        return super().eventFilter(watched, event)

    def _collect_commands(self) -> list[_Command]:
        commands = []
        actions = {entry.action: entry for entry in self._registered.values() if entry.action is not None}
        seen = set()
        window = self.parentWidget()
        menu = window.menuWidget() if isinstance(window, QMainWindow) else None
        if isinstance(menu, QMenuBar):
            for menu_action, path in _menu_actions(menu):
                if menu_action in seen:
                    continue
                entry = actions.get(menu_action)
                if entry is None:
                    entry = _Command(action=menu_action, category=path)
                elif entry.category is None:
                    entry = replace(entry, category=path)
                commands.append(entry)
                seen.add(menu_action)
        for entry in self._registered.values():
            action = entry.action
            if action is None:
                commands.append(entry)
            elif action not in seen:
                commands.append(actions[action])
                seen.add(action)
        return commands

    def _registrations_changed(self) -> None:
        if self.isVisible():
            self._commands = self._collect_commands()
            self._show_matches(self._search.text())

    def _show_matches(self, text: str) -> None:
        query = " ".join(text.casefold().split())
        letters = query.replace(" ", "")
        context = self._current_context()
        recent = {key: index for index, key in enumerate(self._recent)}
        results: list[tuple[tuple[int, ...], _Result]] = []
        for command in self._commands:
            if not command.is_available():
                continue
            title = _action_text(command.action.text()) if command.action is not None else command.title
            prefix = f"{command.category}: " if command.category else ""
            result = _Result(command, title, prefix)
            in_scope = context is not None and command.scope == context
            if not query:
                # Current scope first, then recently run commands, then everything else in discovery order.
                if in_scope:
                    results.append(((0, 0), result))
                elif command.key in recent:
                    results.append(((1, recent[command.key]), result))
                else:
                    results.append(((2, 0), result))
            elif (match := result.match(query, letters)) is not None:
                score, matched = match
                results.append(((score[0], 0 if in_scope else 1, *score[1:]), matched))
        results.sort(key=lambda match: match[0])
        self._matches = [result for _, result in results[:_RESULT_LIMIT]]
        self._results.clear()
        for result in self._matches:
            self._add_row(result)
        self._results.setFixedHeight(min(len(self._matches) * self._row_height, self._results_height_limit))
        self._results.setVisible(bool(self._matches))
        self._empty.setVisible(not self._matches)
        if self._matches:
            self._results.setCurrentRow(0)
        self._panel_layout.activate()
        self._outer_layout.invalidate()
        # Apply the new minimum height before resize can clamp to the old one.
        self._outer_layout.activate()
        self.resize(self.width(), self.sizeHint().height())

    def _add_row(self, result: _Result) -> None:
        import qtextra.helpers as hp

        command = result.command
        icon, shortcut = command.icon, ""
        if command.action is not None:
            icon = command.action.icon()
            shortcut = command.action.shortcut().toString(QKeySequence.SequenceFormat.NativeText)
        if isinstance(icon, str):
            icon = hp.make_qta_icon(icon)

        item = QListWidgetItem()
        item.setData(Qt.ItemDataRole.AccessibleTextRole, f"{result.label}, {shortcut}" if shortcut else result.label)
        item.setToolTip(result.label)
        item.setSizeHint(QSize(0, self._row_height))
        self._results.addItem(item)

        row = QWidget(self._results)
        row.setObjectName("command_palette_row")
        row.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        icon_label = hp.make_label(row)
        icon_label.setFixedWidth(18)
        if icon is not None:
            icon_label.setPixmap(icon.pixmap(18, 18))

        title = hp.make_label(row, self._format_label(result), text_format=Qt.TextFormat.RichText)
        title.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        keys = hp.make_label(
            row,
            shortcut,
            object_name="command_palette_keys",
            text_format=Qt.TextFormat.PlainText,
            visible=bool(shortcut),
        )
        hp.make_h_layout(icon_label, title, keys, stretch_id=1, margin=(9, 0, 9, 0), spacing=9, parent=row)
        self._results.setItemWidget(item, row)

    def _format_label(self, result: _Result) -> str:
        hits = set(result.positions)
        parts = [
            f'<b style="color: {self._match_color}"><u>{escape(char)}</u></b>' if index in hits else escape(char)
            for index, char in enumerate(result.label)
        ]
        prefix = "".join(parts[: len(result.prefix)])
        title = "".join(parts[len(result.prefix) :])
        return f'<span style="white-space: nowrap"><span style="color: {self._muted_color}">{prefix}</span><b>{title}</b></span>'

    def _run_current(self) -> None:
        row = self._results.currentRow()
        if 0 <= row < len(self._matches):
            command = self._matches[row].command
            if not command.is_available():
                self._registrations_changed()
                return
            self.hide()
            self._remember(command)
            if command.action is not None and command.is_available():
                command.action.trigger()
            elif command.callback is not None:
                command.callback()

    def _current_context(self) -> str | None:
        if self._context_provider is None:
            return None
        try:
            return self._context_provider()
        except Exception:  # noqa: BLE001 - a failing app check must not break the palette
            return None

    def _remember(self, command: _Command) -> None:
        key = command.key
        if key is None:
            return
        if key in self._recent:
            self._recent.remove(key)
        self._recent.insert(0, key)
        del self._recent[_RECENT_LIMIT:]

    def _run_item(self, item: QListWidgetItem) -> None:
        self._results.setCurrentItem(item)
        self._run_current()

    def _apply_theme(self) -> None:
        from qtextra.utils.template import template

        themes = self._themes
        self._muted_color = themes.get_hex_color("icon")
        match = themes.get_qt_color("info")
        self._match_color = (match if themes.is_dark else match.darker(140)).name()
        self.setStyleSheet(template(self._stylesheet_template, **themes.active.to_dict()))  # type: ignore[no-untyped-call]
        self._search.ensurePolished()
        self._row_height = self._search.fontMetrics().height() + 14
        if self.isVisible():
            self._show_matches(self._search.text())

    def _update_icons(self) -> None:
        from qtextra.helpers import make_qta_icon

        self._search_icon.setIcon(make_qta_icon("search"))
        if self.isVisible():
            self._show_matches(self._search.text())
