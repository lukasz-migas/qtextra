"""Qt command palette."""

from __future__ import annotations

import typing as ty
from weakref import ref

from qt_command_palette import get_palette
from qt_command_palette._api import CommandPalette
from qtpy.QtWidgets import QAction, QMainWindow, QMenu


class QtCommandPalette:
    """Palette."""

    def __init__(self, parent: QMainWindow, name: str = "Commandpalette"):
        self._ref_parent = ref(parent)
        self._name = name
        self._palette = self.install_command()

    def install_command(self) -> CommandPalette:
        """Install command."""
        palette = get_palette(self._name, alignment="parent")
        palette.set_max_rows(50)

        parent = self._ref_parent()
        breakpoint()
        for child in parent.menuBar().children():
            if not isinstance(child, QMenu):
                continue
            group_name = child.title().replace("&", "")
            if group_name == "":
                continue
            group = palette.add_group(child.title().replace("&", ""))
            for action, context in iter_action(child):
                group.register(
                    make_command(action),
                    desc=" > ".join([*context, action.text()]).replace("&", ""),
                    tooltip=action.toolTip(),
                )

        palette.install(self._ref_parent(), keys="Ctrl+Shift+P")
        return palette

    def show_command_palette(self):
        """Show command palette."""
        self._palette.show_widget(self._ref_parent())


def iter_action(menu: QMenu, cur=None) -> ty.Iterator[tuple[QAction, list[str]]]:
    """Iterate over menu actions."""
    cur = cur or []
    for ac in menu.actions():
        parent = ac.parent()
        if parent is menu:
            continue
        if isinstance(parent, QMenu):
            yield from iter_action(ac.parent(), cur=[*cur, ac.text()])
        else:
            yield ac, cur


def make_command(action: QAction) -> callable:
    """Make command."""
    return lambda: action.trigger()
