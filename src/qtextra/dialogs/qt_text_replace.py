"""Dialog enabling text replacement."""

from qtpy.QtWidgets import QLayout, QWidget

import qtextra.helpers as hp
from qtextra.utils.table_config import TableConfig
from qtextra.widgets.qt_button_tag import QtTagButton
from qtextra.widgets.qt_dialog import QtDialog
from qtextra.widgets.qt_layout_scroll import QtScrollableHLayoutWidget
from qtextra.widgets.qt_table_view_check import QtCheckableTableView

SEPARATOR = " → "


class QtTextReplace(QtDialog):
    """Text replace dialog."""

    TABLE_CONFIG = (
        TableConfig()  # type: ignore
        .add("original text", "old", "int", 300, sizing="stretch")
        .add("new text", "new", "str", 300, sizing="stretch")
        # .add("changed", "changed", "str", 50, sizing="stretch")
    )

    def __init__(
        self,
        parent: QWidget,
        texts: list[str],
        message: str = "",
    ):
        self.message = message
        self.original_texts = texts
        self.search_and_replace_map: dict[str, str] = {}
        self.search_for_text = ""
        self.replace_with_text = ""
        super().__init__(parent)
        self.setMinimumWidth(600)
        self.search_edit.setFocus()
        self.populate()

    def populate(self) -> None:
        """Populate table."""
        for text in self.original_texts:
            self.table.add_row([text, text])

    def on_preview(self) -> None:
        """Preview text."""
        texts = self.table.get_col_data(self.TABLE_CONFIG.old)
        self.search_for_text = self.search_edit.text()
        self.replace_with_text = self.replace_edit.text()
        for row, current in enumerate(texts):
            changed, new_text = self.process_text(current)
            self.table.set_value(self.TABLE_CONFIG.new, row, new_text)
            # self.table.set_value(self.TABLE_CONFIG.changed, row, "True" if changed else "False")

    def on_add(self) -> None:
        """Add replacement text."""
        search_for = self.search_edit.text()
        replace_with = self.replace_edit.text()
        self.add(search_for, replace_with)

    def add(self, search_for: str, replace_with: str) -> None:
        """Add text replacement."""
        if search_for in self.search_and_replace_map and self.search_and_replace_map[search_for] == replace_with:
            return
        if search_for == replace_with:
            return

        self.search_and_replace_map[search_for] = replace_with
        self.search_edit.setText("")
        self.replace_edit.setText("")

        button = QtTagButton(
            f"{search_for}{SEPARATOR}{replace_with}",
            f"{search_for}{SEPARATOR}{replace_with}",
            allow_selected=False,
            action_type="delete",
            action_icon="cross",
        )
        button.evt_action.connect(self.on_remove)
        self.search_replace_layout.insertWidget(0, button)
        self.on_preview()

    def on_remove(self, hash_id: str) -> None:
        """Remove filter."""
        hash_ids = [
            self.search_replace_layout.get_widget(index).text for index in range(self.search_replace_layout.count() - 1)
        ]
        index = hash_ids.index(hash_id)
        search_for, replace_with = hash_id.split(SEPARATOR)
        del self.search_and_replace_map[search_for]
        self.search_replace_layout.removeWidgetOrLayout(index)
        self.on_preview()

    def process_text(self, current: str) -> tuple[bool, str]:
        """Process single text item."""
        new_text = current
        for search, replace in self.search_and_replace_map.items():
            new_text = new_text.replace(search, replace)
        new_text = new_text.replace(self.search_for_text, self.replace_with_text)
        return new_text != current, new_text

    @property
    def new_texts(self) -> list[str]:
        """Text that was entered."""
        new_texts = []
        for current in self.original_texts:
            _, new_text = self.process_text(current)
            new_texts.append(new_text)
        return new_texts

    # noinspection PyAttributeOutsideInit
    def make_panel(self) -> QLayout:
        """Make panel."""
        self.table = QtCheckableTableView(self, config=self.TABLE_CONFIG, sortable=True, checkable=False)
        self.table.setCornerButtonEnabled(False)
        hp.set_font(self.table, 10)
        self.table.setup_model(
            self.TABLE_CONFIG.header, self.TABLE_CONFIG.no_sort_columns, self.TABLE_CONFIG.hidden_columns
        )

        self.search_edit = hp.make_line_edit(
            self,
            "",
            tooltip="Text that will be searched for in the document to replace.",
            placeholder="Text to search for...",
            func_changed=self.on_preview,
        )
        self.replace_edit = hp.make_line_edit(
            self,
            "",
            tooltip="Text that will be used to replace the searched text.",
            placeholder="Text t o replace with...",
            func_changed=self.on_preview,
        )

        self.search_replace_layout = QtScrollableHLayoutWidget(self)
        self.search_replace_layout.set_min_height(self.search_edit.height())

        layout = hp.make_form_layout()
        layout.addRow("Search text:", self.search_edit)
        layout.addRow("Replace text:", self.replace_edit)
        layout.addRow(hp.make_btn(self, "Add", func=self.on_add))
        layout.addRow(self.search_replace_layout)
        layout.addRow(self.table)
        layout.addRow(
            hp.make_h_layout(
                hp.make_btn(self, "OK", func=self.accept),
                hp.make_btn(self, "Cancel", func=self.reject),
            )
        )
        return layout


if __name__ == "__main__":  # pragma: no cover

    def _main():  # type: ignore[no-untyped-def]
        import sys

        from qtextra.utils.dev import apply_style, qapplication

        _ = qapplication()  # analysis:ignore
        dlg = QtTextReplace(
            None,
            [
                "This is a test.",
                "This is a test test.",
                "This is a test test test.",
                "Replace me with something else.",
                "Replace me with something else.",
            ],
        )
        apply_style(dlg)
        dlg.show()
        sys.exit(dlg.exec_())  # type: ignore[attr-defined]

    _main()  # type: ignore[no-untyped-call]
