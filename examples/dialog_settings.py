"""Searchable settings dialog with an icon sidebar."""

from qtpy.QtWidgets import QApplication

import qtextra.helpers as hp
from qtextra.config import THEMES
from qtextra.dialogs.qt_settings import QtSettingsDialog


class DemoSettingsDialog(QtSettingsDialog):
    """Small settings dialog with two pages."""

    def make_pages(self) -> None:
        """Create pages."""
        page = self.add_page("Appearance", "mdi6.palette-outline")
        page.add_section("Theme")
        page.add_row("Theme", hp.make_combobox(page, ["light", "dark"]))
        page.add_row("Synchronize with local time", hp.make_checkbox(page))
        page.add_section("Text")
        page.add_row("Font size", hp.make_int_spin_box(page, 6, 32, value=10), tooltip="Application font size.")

        page = self.add_page("Experimental", "mdi6.flask-outline")
        page.add_row(
            "Fast renderer",
            hp.make_h_layout(
                hp.make_checkbox(page),
                hp.make_warning_label(page, "Changes take effect after restarting the application."),
                stretch_after=True,
            ),
            keywords="gpu opengl",
        )


app = QApplication([])
dlg = DemoSettingsDialog(None, title="Settings")
dlg.resize(800, 500)
THEMES.apply(dlg)
dlg.show()
app.exec_()
