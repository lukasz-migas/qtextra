"""Summary widget for multi-dictionary tag tables."""

from __future__ import annotations

from collections.abc import Mapping

from qtpy.QtCore import Qt
from qtpy.QtWidgets import QFrame, QSizePolicy, QWidget

import qtextra.helpers as hp
from qtextra.widgets.qt_button_tag import QtTagManager
from qtextra.widgets.qt_dict_tag_editor import DictTagValue


class _SummaryCard(QFrame):
    """Small summary card for one key."""

    def __init__(self, parent: QWidget | None, key: str, summary: dict) -> None:
        super().__init__(parent)
        self.setObjectName("multiDictSummaryCard")
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        title = hp.make_label(self, key, bold=True)
        subtitle = hp.make_label(
            self,
            f"{summary['sample_count']} sample{'s' if summary['sample_count'] != 1 else ''} represented",
        )
        options_title = hp.make_label(self, "Options", bold=True)
        matches_title = hp.make_label(self, "Matches", bold=True)

        options_tags = QtTagManager(self, allow_action=False, flow=True)
        options_tags.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        for option in summary["options"]:
            options_tags.add_tag(option, allow_check=False, hide_check=True)

        match_lines = []
        for option, samples in summary["matches"].items():
            sample_text = ", ".join(samples)
            match_lines.append(f"<b>{option}</b>: {sample_text}")
        matches = hp.make_label(self, "<br>".join(match_lines), wrap=True, text_format=Qt.TextFormat.RichText)

        hp.make_v_layout(
            title,
            subtitle,
            options_title,
            options_tags,
            matches_title,
            matches,
            spacing=4,
            margin=10,
            parent=self,
        )


class QtMultiDictSummaryWidget(QWidget):
    """Summary panel for nested dictionary data."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._summary_data: dict = {"sample_count": 0, "key_count": 0, "keys": {}}
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        self.setMinimumWidth(280)
        self._title_label = hp.make_label(self, "Summary", bold=True)
        self._stats_label = hp.make_label(self, "")
        self._title_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self._stats_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self._title_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._stats_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._header_widget = QWidget(self)
        self._header_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        hp.make_v_layout(
            self._title_label,
            self._stats_label,
            spacing=2,
            margin=0,
            parent=self._header_widget,
        )
        self._cards_inner, self._cards_scroll = hp.make_scroll_area(
            self,
            vertical=Qt.ScrollBarPolicy.ScrollBarAsNeeded,
            horizontal=Qt.ScrollBarPolicy.ScrollBarAlwaysOff,
        )
        self._cards_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._cards_scroll.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._cards_scroll.setMinimumHeight(180)
        self._cards_scroll.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self._cards_layout = hp.make_v_layout(spacing=8, margin=0, parent=self._cards_inner)
        self._cards_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self._body_widget = QWidget(self)
        self._body_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        body_layout = hp.make_v_layout(
            self._cards_scroll,
            spacing=0,
            margin=0,
            parent=self._body_widget,
        )
        body_layout.setStretch(0, 1)

        layout = hp.make_v_layout(
            self._header_widget,
            self._body_widget,
            spacing=6,
            margin=0,
            parent=self,
        )
        layout.setStretch(0, 0)
        layout.setStretch(1, 1)
        self._refresh_ui()

    def summary_data(self) -> dict:
        """Return the computed summary structure."""
        return self._summary_data

    def set_items(self, items: Mapping[str, Mapping[str, DictTagValue]]) -> None:
        """Compute summaries from nested dictionaries."""
        self._summary_data = self.build_summary(items)
        self._refresh_ui()

    def clear_items(self) -> None:
        """Clear all summaries."""
        self._summary_data = {"sample_count": 0, "key_count": 0, "keys": {}}
        self._refresh_ui()

    @staticmethod
    def _format_value(value: DictTagValue) -> str:
        return "None" if value is None else str(value)

    @classmethod
    def build_summary(cls, items: Mapping[str, Mapping[str, DictTagValue]]) -> dict:
        """Build structured summary data for nested dictionaries."""
        samples = list(items)
        key_summary: dict[str, dict[str, list[str]]] = {}

        for sample in samples:
            for key, value in items[sample].items():
                value_text = cls._format_value(value)
                key_summary.setdefault(key, {}).setdefault(value_text, []).append(sample)

        ordered_key_summary: dict[str, dict] = {}
        for key in sorted(key_summary, key=str.casefold):
            matches = {
                option: sorted(sample_names, key=str.casefold)
                for option, sample_names in sorted(key_summary[key].items(), key=lambda item: item[0].casefold())
            }
            ordered_key_summary[key] = {
                "sample_count": sum(len(sample_names) for sample_names in matches.values()),
                "options": list(matches),
                "matches": matches,
            }

        return {
            "sample_count": len(samples),
            "key_count": len(ordered_key_summary),
            "keys": ordered_key_summary,
        }

    def _refresh_ui(self) -> None:
        while self._cards_layout.count():
            item = self._cards_layout.takeAt(0)
            widget = item.widget() if item is not None else None
            if widget is not None:
                widget.deleteLater()

        self._stats_label.setText(
            f"{self._summary_data['sample_count']} sample{'s' if self._summary_data['sample_count'] != 1 else ''}  |  "
            f"{self._summary_data['key_count']} key{'s' if self._summary_data['key_count'] != 1 else ''}",
        )

        if not self._summary_data["keys"]:
            empty = hp.make_label(self._cards_inner, "No summaries available yet.", wrap=True)
            empty.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
            empty.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
            self._cards_layout.addWidget(empty)
            return

        for key, summary in self._summary_data["keys"].items():
            self._cards_layout.addWidget(_SummaryCard(self._cards_inner, key, summary))

    setItems = set_items
    clearItems = clear_items
    summaryData = summary_data
