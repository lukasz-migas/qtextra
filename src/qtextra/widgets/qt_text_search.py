"""Search panel widget."""

from __future__ import annotations

import contextlib
import re

from qtpy.QtCore import Qt, Signal
from qtpy.QtGui import QPalette, QTextCharFormat, QTextCursor
from qtpy.QtWidgets import QPlainTextEdit, QSizePolicy, QTextEdit, QWidget

import qtextra.helpers as hp
from qtextra.config import QtStyler
from qtextra.widgets.qt_button_icon import QtImagePushButton

TextEditor = QPlainTextEdit | QTextEdit


class QtSearchPanel(QWidget):
    """Reusable find and replace panel."""

    evt_search_changed = Signal(str)
    evt_find_next = Signal(str)
    evt_find_previous = Signal(str)
    evt_replace_one = Signal(str, str)
    evt_replace_all = Signal(str, str)
    evt_options_changed = Signal()
    evt_closed = Signal()

    def __init__(
        self,
        parent: QWidget | None = None,
        placeholder: str = "Search...",
        replace_placeholder: str = "Replace...",
        *,
        show_replace: bool = True,
        show_close: bool = True,
    ) -> None:
        super().__init__(parent)
        self._target_editor: TextEditor | None = None
        self._matches: list[tuple[int, int]] = []
        self._current_match_index: int = -1

        self.search_edit = hp.make_line_edit(
            self,
            placeholder=placeholder,
            func_changed=self._on_search_changed,
            func_enter=self.find_next,
        )
        self.search_edit.addAction(
            hp.make_action(self, "zoom", tooltip="Find next match.", func=self.find_next),
            self.search_edit.ActionPosition.LeadingPosition,
        )

        self.match_label = hp.make_label(
            self, "0 matches", alignment=Qt.AlignmentFlag.AlignCenter, object_name="match_label"
        )
        self.match_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        self.previous_button = hp.make_qta_btn(
            self,
            "previous",
            tooltip="Find previous match.",
            average=True,
            func=self.find_previous,
        )
        self.next_button = hp.make_qta_btn(self, "next", tooltip="Find next match.", average=True, func=self.find_next)
        self.close_button = hp.make_qta_btn(
            self,
            "cross",
            tooltip="Close search panel.",
            average=True,
            func=self.close_panel,
        )
        self.close_button.setVisible(show_close)

        self.case_checkbox = self._make_option_button("Aa", "Match case")
        self.whole_word_checkbox = self._make_option_button("Word", "Match whole words")
        self.regex_checkbox = self._make_option_button(".*", "Treat the query as a regular expression")

        for button in (self.case_checkbox, self.whole_word_checkbox, self.regex_checkbox):
            button.toggled.connect(self._on_options_changed)

        self.replace_edit = hp.make_line_edit(self, placeholder=replace_placeholder, func_enter=self.replace_one)
        self.replace_button = self._make_action_button("replace", "Replace the current match.", self.replace_one)
        self.replace_all_button = self._make_action_button("replace_all", "Replace all matches.", self.replace_all)

        search_row = hp.make_h_layout(
            self.search_edit,
            self.match_label,
            self.previous_button,
            self.next_button,
            self.close_button,
            spacing=2,
            margin=0,
            stretch_id=0,
            widget_alignment={1: hp.Qt.AlignmentFlag.AlignVCenter},
        )
        replace_row = hp.make_h_layout(
            self.replace_edit,
            self.replace_button,
            self.replace_all_button,
            self.case_checkbox,
            self.whole_word_checkbox,
            self.regex_checkbox,
            spacing=3,
            margin=0,
            stretch_id=0,
            widget_alignment={
                3: hp.Qt.AlignmentFlag.AlignVCenter,
                4: hp.Qt.AlignmentFlag.AlignVCenter,
                5: hp.Qt.AlignmentFlag.AlignVCenter,
            },
        )

        hp.make_v_layout(search_row, replace_row, spacing=4, margin=0, parent=self)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.set_replace_visible(show_replace)
        self.set_match_count(0)

    @property
    def case_sensitive(self) -> bool:
        """Return whether case matching is enabled."""
        return self.case_checkbox.isChecked()

    @property
    def whole_word(self) -> bool:
        """Return whether whole-word matching is enabled."""
        return self.whole_word_checkbox.isChecked()

    @property
    def regex(self) -> bool:
        """Return whether regex mode is enabled."""
        return self.regex_checkbox.isChecked()

    def search_text(self) -> str:
        """Return the current search text."""
        return self.search_edit.text()

    def set_search_text(self, text: str) -> None:
        """Set the search text."""
        self.search_edit.setText(text)

    def replace_text(self) -> str:
        """Return the current replacement text."""
        return self.replace_edit.text()

    def set_replace_text(self, text: str) -> None:
        """Set the replacement text."""
        self.replace_edit.setText(text)

    def search_options(self) -> dict[str, bool]:
        """Return the current search options."""
        return {
            "case_sensitive": self.case_sensitive,
            "whole_word": self.whole_word,
            "regex": self.regex,
        }

    def set_match_count(self, total: int, current: int | None = None) -> None:
        """Update the visible search status."""
        if current is None or total <= 0:
            text = f"{total} match" if total == 1 else f"{total} matches"
        else:
            text = f"{current} / {total}"
        self.match_label.setText(text)

    def set_replace_visible(self, visible: bool) -> None:
        """Show or hide the replace controls."""
        for widget in (
            self.replace_edit,
            self.replace_button,
            self.replace_all_button,
        ):
            widget.setVisible(visible)

    def clear(self) -> None:
        """Clear the search and replace contents."""
        self.search_edit.clear()
        self.replace_edit.clear()
        self._clear_highlights()

    def find_next(self) -> None:
        """Emit a request to navigate to the next match."""
        self._move_to_relative_match(1)
        self.evt_find_next.emit(self.search_text())

    def find_previous(self) -> None:
        """Emit a request to navigate to the previous match."""
        self._move_to_relative_match(-1)
        self.evt_find_previous.emit(self.search_text())

    def replace_one(self) -> None:
        """Emit a request to replace the current match."""
        if self._target_editor and self._matches:
            self._replace_current_match()
        self.evt_replace_one.emit(self.search_text(), self.replace_text())

    def replace_all(self) -> None:
        """Emit a request to replace all matches."""
        if self._target_editor and self._matches:
            self._replace_all_matches()
        self.evt_replace_all.emit(self.search_text(), self.replace_text())

    def close_panel(self) -> None:
        """Hide the panel and emit a close signal."""
        self.hide()
        self.evt_closed.emit()

    def set_target_editor(self, editor: TextEditor | None) -> None:
        """Attach a text editor and drive search state from its content."""
        if self._target_editor is editor:
            return
        if self._target_editor is not None:
            with contextlib.suppress(TypeError, RuntimeError):
                self._target_editor.textChanged.disconnect(self._refresh_matches)
            self._clear_highlights()
        self._target_editor = editor
        if self._target_editor is not None:
            self._target_editor.textChanged.connect(self._refresh_matches)
        self._refresh_matches()

    def _on_search_changed(self, text: str) -> None:
        if self._target_editor is not None:
            self._refresh_matches()
        self.evt_search_changed.emit(text)

    def _on_options_changed(self) -> None:
        if self._target_editor is not None:
            self._refresh_matches()
        self.evt_options_changed.emit()
        self.evt_search_changed.emit(self.search_text())

    def _make_option_button(self, text: str, tooltip: str) -> QtImagePushButton:
        button = QtImagePushButton(parent=self)
        button.setText(text)
        button.setToolTip(tooltip)
        button.setCheckable(True)
        button.setProperty("checkable", True)
        button.setProperty("with_text", True)
        button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        button.setMinimumWidth(max(42, button.fontMetrics().horizontalAdvance(text) + 18))
        return button

    def _make_action_button(self, icon_name: str, tooltip: str, func) -> QtImagePushButton:
        return hp.make_qta_btn(self, icon_name, tooltip=tooltip, func=func, average=True)

    def _refresh_matches(self) -> None:
        if self._target_editor is None:
            return

        text = self._target_editor.toPlainText()
        self._matches = self._find_matches(text)
        if not self._matches:
            self._current_match_index = -1
            self.set_match_count(0)
            self._clear_highlights()
            return

        if self._current_match_index < 0 or self._current_match_index >= len(self._matches):
            self._current_match_index = self._best_match_index_for_cursor()
        self._apply_highlights()
        self._update_match_label()

    def _find_matches(self, text: str) -> list[tuple[int, int]]:
        query = self.search_text()
        if not query:
            return []

        if self.regex:
            flags = 0 if self.case_sensitive else re.IGNORECASE
            try:
                pattern = re.compile(query, flags)
            except re.error:
                return []
            return [(match.start(), match.end()) for match in pattern.finditer(text) if match.start() != match.end()]

        if self.whole_word:
            escaped = re.escape(query)
            flags = 0 if self.case_sensitive else re.IGNORECASE
            pattern = re.compile(rf"\b{escaped}\b", flags)
            return [(match.start(), match.end()) for match in pattern.finditer(text)]

        haystack = text if self.case_sensitive else text.casefold()
        needle = query if self.case_sensitive else query.casefold()
        matches: list[tuple[int, int]] = []
        start = 0
        while True:
            index = haystack.find(needle, start)
            if index < 0:
                break
            end = index + len(query)
            matches.append((index, end))
            start = end
        return matches

    def _apply_highlights(self) -> None:
        if self._target_editor is None:
            return

        palette = self._target_editor.palette()
        all_color = QtStyler.primary()
        all_color.setAlpha(90)
        current_color = QtStyler.highlight()
        current_color.setAlpha(180)

        all_format = QTextCharFormat()
        all_format.setBackground(all_color)
        current_format = QTextCharFormat()
        current_format.setBackground(current_color)
        current_format.setForeground(palette.color(QPalette.ColorRole.HighlightedText))

        selections = []
        for index, (start, end) in enumerate(self._matches):
            cursor = self._target_editor.textCursor()
            cursor.setPosition(start)
            cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
            selection = QTextEdit.ExtraSelection()
            selection.cursor = cursor
            selection.format = current_format if index == self._current_match_index else all_format
            selections.append(selection)
        self._target_editor.setExtraSelections(selections)

    def _clear_highlights(self) -> None:
        if self._target_editor is not None:
            self._target_editor.setExtraSelections([])

    def _best_match_index_for_cursor(self) -> int:
        if self._target_editor is None or not self._matches:
            return -1
        position = self._target_editor.textCursor().selectionStart()
        for index, (start, _) in enumerate(self._matches):
            if start >= position:
                return index
        return 0

    def _move_to_relative_match(self, step: int) -> None:
        if self._target_editor is None or not self._matches:
            return
        self._current_match_index = (self._current_match_index + step) % len(self._matches)
        self._select_current_match()

    def _select_current_match(self) -> None:
        if self._target_editor is None or not self._matches or self._current_match_index < 0:
            return
        start, end = self._matches[self._current_match_index]
        cursor = self._target_editor.textCursor()
        cursor.setPosition(start)
        cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
        self._target_editor.setTextCursor(cursor)
        self._target_editor.ensureCursorVisible()
        self._apply_highlights()
        self._update_match_label()

    def _update_match_label(self) -> None:
        if not self._matches:
            self.set_match_count(0)
            return
        self.set_match_count(len(self._matches), self._current_match_index + 1)

    def _replace_current_match(self) -> None:
        assert self._target_editor is not None
        if self._current_match_index < 0 or self._current_match_index >= len(self._matches):
            return
        start, end = self._matches[self._current_match_index]
        cursor = self._target_editor.textCursor()
        cursor.setPosition(start)
        cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
        cursor.insertText(self.replace_text())
        self._refresh_matches()
        if self._matches:
            self._current_match_index = min(self._current_match_index, len(self._matches) - 1)
            self._select_current_match()

    def _replace_all_matches(self) -> None:
        assert self._target_editor is not None
        text = self._target_editor.toPlainText()
        query = self.search_text()
        if not query:
            return
        if self.regex:
            flags = 0 if self.case_sensitive else re.IGNORECASE
            try:
                text = re.sub(query, self.replace_text(), text, flags=flags)
            except re.error:
                return
        elif self.whole_word:
            escaped = re.escape(query)
            flags = 0 if self.case_sensitive else re.IGNORECASE
            text = re.sub(rf"\b{escaped}\b", self.replace_text(), text, flags=flags)
        elif self.case_sensitive:
            text = text.replace(query, self.replace_text())
        else:
            pattern = re.compile(re.escape(query), re.IGNORECASE)
            text = pattern.sub(self.replace_text(), text)
        self._target_editor.setPlainText(text)
        self._refresh_matches()

    # Alias methods to offer Qt-like interface
    searchText = search_text
    setSearchText = set_search_text
    replaceText = replace_text
    setReplaceText = set_replace_text
    searchOptions = search_options
    setMatchCount = set_match_count
    setReplaceVisible = set_replace_visible
    setTargetEditor = set_target_editor
    closePanel = close_panel
    findNext = find_next
    findPrevious = find_previous
    replaceOne = replace_one
    replaceAll = replace_all


if __name__ == "__main__":  # pragma: no cover
    import sys

    from qtextra.utils.dev import qframe

    app, frame, ha = qframe(horz=False)

    editor = QPlainTextEdit()
    editor.setPlainText(
        "QtSearchPanel is useful for common desktop workflows.\n"
        "Search, navigate, and replace text from a shared reusable panel.\n"
        "This example wires the panel to a text area in a minimal way.",
    )

    status = hp.make_label(frame, "Type into the search box to search the editor.")
    search_panel = QtSearchPanel()
    search_panel.set_target_editor(editor)

    def _update_status(text: str) -> None:
        status.setText(f"Searching for: {text or '<empty>'}")

    search_panel.evt_search_changed.connect(_update_status)

    ha.addWidget(search_panel)
    ha.addWidget(editor)
    ha.addWidget(status)

    frame.show()
    sys.exit(app.exec_())
