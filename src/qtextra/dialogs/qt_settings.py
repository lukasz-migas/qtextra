"""Searchable settings dialog with an icon sidebar and one page per category."""

from __future__ import annotations

from dataclasses import dataclass, field

from qtpy.QtCore import QSize, Qt
from qtpy.QtGui import QKeySequence, QShortcut
from qtpy.QtWidgets import (
    QAbstractButton,
    QFrame,
    QHBoxLayout,
    QLayout,
    QListWidget,
    QListWidgetItem,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

import qtextra.helpers as hp
from qtextra.config import THEMES
from qtextra.widgets.qt_dialog import QtDialog


@dataclass
class _Row:
    widget: QWidget
    text: str


@dataclass
class _Section:
    title: str
    header: QWidget | None
    rows: list[_Row] = field(default_factory=list)


class QtSettingsPage(QWidget):
    """Single page of a settings dialog: titled sections made of label/control rows.

    Parameters
    ----------
    title : str
        Page title, shown above the page and in the sidebar. A search matching it shows the whole page.
    parent : QWidget | None
        Parent widget.
    control_width : int
        Width of the control column, shared by all rows so controls line up.
    """

    def __init__(self, title: str, parent: QWidget | None = None, control_width: int = 320) -> None:
        super().__init__(parent)
        self.title = title
        self.control_width = control_width
        self._sections: list[_Section] = []

        self._inner, scroll = hp.make_scroll_area(self)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._layout = QVBoxLayout(self._inner)
        self._layout.setContentsMargins(0, 0, 8, 0)
        self._layout.setSpacing(0)
        self._layout.addStretch(1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(scroll)

    def _insert(self, widget: QWidget) -> None:
        """Insert widget above the trailing stretch."""
        self._layout.insertWidget(self._layout.count() - 1, widget)

    def add_section(self, title: str) -> QWidget:
        """Start a new section; rows added afterwards belong to it."""
        header = hp.make_label(self._inner, title, bold=True, object_name="settings_section")
        header.setContentsMargins(0, 14 if self._sections else 0, 0, 4)
        self._insert(header)
        self._sections.append(_Section(title, header))
        return header

    def add_row(
        self,
        title: str,
        widget: QWidget | QLayout,
        tooltip: str = "",
        keywords: str = "",
    ) -> QWidget:
        """Add a setting row with the label on the left and the control on the right.

        Parameters
        ----------
        title : str
            Row label. When empty, the control spans the full row width.
        widget : QWidget | QLayout
            Control (or layout of controls) for this setting.
        tooltip : str
            Tooltip of the label; also used by the search.
        keywords : str
            Extra words the search should match for this row.

        Returns
        -------
        QWidget
            Row container, which is hidden when it does not match the search.
        """
        if not self._sections:
            self._sections.append(_Section("", None))
        section = self._sections[-1]

        row = QWidget(self._inner)
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(12)
        if isinstance(widget, QLayout):
            control = QWidget(row)
            widget.setContentsMargins(0, 0, 0, 0)
            control.setLayout(widget)
        elif title:
            # fixed-width column keeps controls aligned between rows; buttons (checkboxes, swatches) sit on the right
            control = QWidget(row)
            control_layout = QHBoxLayout(control)
            control_layout.setContentsMargins(0, 0, 0, 0)
            if isinstance(widget, QAbstractButton):
                control_layout.addStretch(1)
                control_layout.addWidget(widget)
            else:
                control_layout.addWidget(widget, 1)
        else:
            control = widget
        if title:
            label = hp.make_label(row, title, tooltip=tooltip or None, wrap=True)
            control.setFixedWidth(self.control_width)
            layout.addWidget(label, stretch=1)
        layout.addWidget(control, 0 if title else 1)
        self._insert(row)

        tooltips = widget.toolTip() if isinstance(widget, QWidget) else ""
        text = " ".join((title, tooltip, keywords, tooltips)).lower()
        section.rows.append(_Row(row, text))
        return row

    def filter(self, text: str) -> int:
        """Show only rows matching `text` and return how many are visible."""
        query = text.strip().lower()
        show_all = not query or query in self.title.lower()
        count = 0
        for section in self._sections:
            section_match = show_all or bool(section.title and query in section.title.lower())
            visible = 0
            for row in section.rows:
                match = section_match or query in row.text
                row.widget.setHidden(not match)
                visible += match
            if section.header is not None:
                section.header.setHidden(visible == 0)
            count += visible
        return count


class QtSettingsDialog(QtDialog):
    """Settings dialog with a search box, an icon sidebar and one page per category.

    Subclasses implement `make_pages`, calling `add_page` and filling each returned `QtSettingsPage`.
    Extra buttons go in `sidebar_footer_layout` (below the sidebar) or `content_footer_layout` (below the page).
    """

    SIDEBAR_WIDTH: int = 220
    CONTROL_WIDTH: int = 320

    def make_pages(self) -> None:
        """Create the pages with `add_page`."""
        raise NotImplementedError("Must implement method")

    # noinspection PyAttributeOutsideInit
    def make_panel(self) -> QLayout:
        """Make panel."""
        self._pages: list[QtSettingsPage] = []
        self._icons: list[str] = []

        self._search = hp.make_line_edit(
            self, placeholder="Search", prefix_icon="search", func_changed=self.on_search, object_name="settings_search"
        )
        self._list = QListWidget(self)
        self._list.setObjectName("settings_sidebar")
        self._list.setFrameShape(QFrame.Shape.NoFrame)
        self._list.setIconSize(QSize(18, 18))
        self._list.setSpacing(1)
        self._list.currentRowChanged.connect(self._on_row_changed)

        self.sidebar_footer_layout = hp.make_v_layout(spacing=2, margin=0)
        sidebar = QWidget(self)
        sidebar.setMinimumWidth(150)
        sidebar_layout = hp.make_v_layout(spacing=6, margin=(0, 0, 4, 0), parent=sidebar)
        sidebar_layout.addWidget(self._search)
        sidebar_layout.addWidget(self._list, stretch=1)
        sidebar_layout.addLayout(self.sidebar_footer_layout)

        self._title = hp.make_label(self, "", object_name="header_label")
        self._stack = QStackedWidget(self)
        self._empty_label = hp.make_label(
            self, "No settings match your search.", alignment=Qt.AlignmentFlag.AlignCenter, hide=True
        )
        self.content_footer_layout = hp.make_h_layout(spacing=2, margin=0)

        content = QWidget(self)
        content.setMinimumWidth(300)
        content_layout = hp.make_v_layout(spacing=8, margin=(8, 0, 0, 0), parent=content)
        content_layout.addWidget(self._title)
        content_layout.addWidget(self._stack, stretch=1)
        content_layout.addWidget(self._empty_label, stretch=1)
        content_layout.addLayout(self.content_footer_layout)

        self._splitter = QSplitter(Qt.Orientation.Horizontal, self)
        self._splitter.setChildrenCollapsible(False)
        self._splitter.addWidget(sidebar)
        self._splitter.addWidget(content)
        self._splitter.setStretchFactor(1, 1)
        self._splitter.setSizes([self.SIDEBAR_WIDTH, 10_000])

        layout = hp.make_h_layout(spacing=0, margin=6)
        layout.addWidget(self._splitter)

        self._search_shortcut = QShortcut(QKeySequence(QKeySequence.StandardKey.Find), self)
        self._search_shortcut.activated.connect(self.focus_search)
        THEMES.evt_theme_changed.connect(self._update_icons)

        self.make_pages()
        if self._pages:
            self.set_index(0)
        return layout

    def _on_teardown(self) -> None:
        """Disconnect from global events."""
        THEMES.evt_theme_changed.disconnect(self._update_icons)
        super()._on_teardown()

    def add_page(self, title: str, icon: str = "") -> QtSettingsPage:
        """Add a page to the sidebar and return it.

        Parameters
        ----------
        title : str
            Page title, shown in the sidebar and above the page.
        icon : str
            qtextra icon key or qtawesome name (e.g. ``"mdi6.palette-outline"``).
        """
        page = QtSettingsPage(title, self._stack, control_width=self.CONTROL_WIDTH)
        item = QListWidgetItem(title)
        item.setSizeHint(QSize(0, 30))
        if icon:
            item.setIcon(hp.make_qta_icon(icon))
        self._list.addItem(item)
        self._stack.addWidget(page)
        self._pages.append(page)
        self._icons.append(icon)
        return page

    @property
    def pages(self) -> list[QtSettingsPage]:
        """Pages in sidebar order."""
        return list(self._pages)

    def set_index(self, index: int) -> None:
        """Show the page at `index`."""
        self._list.setCurrentRow(index)

    def current_index(self) -> int:
        """Return the index of the visible page."""
        return self._stack.currentIndex()

    def focus_search(self) -> None:
        """Focus the search box and select its text."""
        self._search.setFocus()
        self._search.selectAll()

    def _on_row_changed(self, index: int) -> None:
        if index < 0:
            return
        self._stack.setCurrentIndex(index)
        self._title.setText(self._pages[index].title)

    def on_search(self, text: str) -> None:
        """Filter pages and rows by `text`."""
        query = text.strip()
        first_visible = -1
        for index, page in enumerate(self._pages):
            count = page.filter(query)
            hidden = bool(query) and count == 0
            self._list.item(index).setHidden(hidden)
            if not hidden and first_visible < 0:
                first_visible = index

        has_match = first_visible >= 0
        self._title.setHidden(not has_match)
        self._stack.setHidden(not has_match)
        self._empty_label.setHidden(has_match)
        current = self._list.currentRow()
        if has_match and (current < 0 or self._list.item(current).isHidden()):
            self.set_index(first_visible)

    def _update_icons(self) -> None:
        """Re-color sidebar icons after a theme change."""
        for index, icon in enumerate(self._icons):
            if icon:
                self._list.item(index).setIcon(hp.make_qta_icon(icon))
