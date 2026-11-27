"""Tests for the lazy command palette and its popup."""

from __future__ import annotations

from pytestqt.qtbot import QtBot
from qtpy.QtCore import QCoreApplication, QEvent, Qt
from qtpy.QtGui import QKeySequence, QShortcut
from qtpy.QtWidgets import QLabel, QLineEdit, QListWidget, QMainWindow, QWidget

from qtextra.widgets.qt_command_palette import QtCommandPalette


def _search(palette: QtCommandPalette) -> QLineEdit:
    return palette.findChild(QLineEdit, "command_palette_search")


def _results(palette: QtCommandPalette) -> QListWidget:
    return palette.findChild(QListWidget, "command_palette_results")


def _labels(palette: QtCommandPalette) -> list[str]:
    results = _results(palette)
    return [results.item(row).toolTip() for row in range(results.count())]


def test_install_defers_creation_and_uses_a_window_shortcut(qtbot: QtBot) -> None:
    window = QMainWindow()
    qtbot.addWidget(window)
    controller = QtCommandPalette.install(window, shortcut="Ctrl+K")
    controller.add_command("Reset view", lambda: None)

    assert window.findChild(QtCommandPalette) is None
    assert window.menuWidget() is None
    shortcut = window.findChild(QShortcut)
    assert shortcut.key() == QKeySequence("Ctrl+K")
    assert shortcut.context() == Qt.ShortcutContext.WindowShortcut

    # Activate the binding directly so this also works on headless Qt platforms.
    window.show()
    shortcut.activated.emit()
    palette = window.findChild(QtCommandPalette)
    assert palette.isVisible()
    assert _search(palette).hasFocus()
    assert _labels(palette) == ["Reset view"]
    assert window.menuWidget() is None
    palette.hide()
    controller.open()
    assert window.findChild(QtCommandPalette) is palette


def test_menu_discovery_refreshes_and_uses_original_actions(qtbot: QtBot) -> None:
    window = QMainWindow()
    qtbot.addWidget(window)
    controller = QtCommandPalette.install(window, shortcut=None)
    assert window.findChild(QShortcut) is None

    file = window.menuBar().addMenu("&File")
    export = file.addMenu("E&xport")
    export.addSeparator()
    action = export.addAction("C&SV && TSV")
    action.setCheckable(True)
    action.setShortcut("Ctrl+Shift+E")
    export.addAction("Hidden").setVisible(False)
    export.addAction("Disabled").setEnabled(False)
    file.addMenu("Unavailable").setEnabled(False)
    window.menuBar().addMenu("Other").addAction(action)

    window.show()
    controller.open()
    palette = window.findChild(QtCommandPalette)
    assert _labels(palette) == ["File \u203a Export: CSV & TSV"]
    keys = palette.findChild(QLabel, "command_palette_keys")
    assert keys.text() == action.shortcut().toString(QKeySequence.SequenceFormat.NativeText)

    with qtbot.waitSignal(action.triggered) as triggered:
        qtbot.keyClick(_search(palette), Qt.Key.Key_Return)
    assert triggered.args == [True]
    assert action.isChecked()
    assert not palette.isVisible()

    action.setVisible(False)
    json_action = export.addAction("JSON")
    controller.open()
    assert _labels(palette) == ["File \u203a Export: JSON"]
    results = _results(palette)
    with qtbot.waitSignal(json_action.triggered):
        qtbot.mouseClick(
            results.viewport(), Qt.MouseButton.LeftButton, pos=results.visualItemRect(results.item(0)).center()
        )
    assert not palette.isVisible()


def test_registrations_override_menu_metadata_and_can_be_removed(qtbot: QtBot) -> None:
    window = QMainWindow()
    qtbot.addWidget(window)
    action = window.menuBar().addMenu("Tools").addAction("Run")
    controller = QtCommandPalette.install(window, shortcut=None)
    manual_action = controller.add_action(action, category="Statistics", keywords=("ANOVA",))
    invoked: list[str] = []

    def run_report() -> None:
        invoked.append("report")

    report = controller.add_command("Run", run_report, category="Reports")
    window.show()
    controller.open()
    palette = window.findChild(QtCommandPalette)
    assert _labels(palette) == ["Statistics: Run", "Reports: Run"]
    _search(palette).setText("ANOVA")
    assert _labels(palette) == ["Statistics: Run"]

    controller.remove_command(manual_action)
    assert _labels(palette) == []
    _search(palette).clear()
    assert _labels(palette) == ["Tools: Run", "Reports: Run"]
    qtbot.keyClick(_search(palette), Qt.Key.Key_Down)
    qtbot.keyClick(_search(palette), Qt.Key.Key_Return)
    assert invoked == ["report"]

    controller.remove_command(report)
    controller.open()
    assert _labels(palette) == ["Tools: Run"]


def test_fuzzy_search_ranks_and_highlights_only_the_top_ten(qtbot: QtBot) -> None:
    window = QWidget()
    qtbot.addWidget(window)
    palette = QtCommandPalette(window)
    for index in range(14):
        palette.add_command(f"Extended dataset statistics {index}", lambda: None)
    palette.add_command("Export statistics", lambda: None, category="Plugin")
    palette.add_command("exst", lambda: None)

    window.show()
    palette.open()
    assert _labels(palette) == [f"Extended dataset statistics {index}" for index in range(10)]
    search = _search(palette)
    qtbot.keyClicks(search, "EXST")
    labels = _labels(palette)
    assert len(labels) == 10
    assert labels[:2] == ["exst", "Plugin: Export statistics"]
    results = _results(palette)
    export_row = results.itemWidget(results.item(labels.index("Plugin: Export statistics")))
    markup = next(label.text() for label in export_row.findChildren(QLabel) if "<u>" in label.text())
    for letter in "Exst":
        assert f"<u>{letter}</u>" in markup

    search.setText("plugin")
    assert _labels(palette) == ["Plugin: Export statistics"]
    search.setText("unmatched")
    assert _labels(palette) == []
    assert palette.findChild(QLabel, "command_palette_empty").isVisible()
    qtbot.keyClick(search, Qt.Key.Key_Escape)
    assert not palette.isVisible()


def test_popup_height_follows_result_count(qtbot: QtBot) -> None:
    window = QWidget()
    qtbot.addWidget(window)
    window.resize(700, 500)
    palette = QtCommandPalette(window)
    for index in range(8):
        palette.add_command(f"Report {index}", lambda: None)
    palette.add_command("Mask creator", lambda: None)
    palette.add_command("Mask editor", lambda: None)

    window.show()
    palette.open()
    search = _search(palette)
    results = _results(palette)
    full_height = palette.height()
    row_height = results.sizeHintForRow(0)
    search_geometry = search.geometry()
    position = palette.pos()

    search.setText("mask")
    assert results.count() == 2
    assert palette.height() == full_height - 8 * row_height
    assert search.geometry() == search_geometry
    assert palette.pos() == position

    search.setText("unmatched")
    assert palette.height() < full_height - 8 * row_height
    assert search.geometry() == search_geometry
    assert palette.pos() == position

    search.clear()
    assert palette.height() == full_height
    assert search.geometry() == search_geometry
    assert palette.pos() == position


def test_deleted_actions_cannot_be_run_from_stale_results(qtbot: QtBot) -> None:
    window = QMainWindow()
    qtbot.addWidget(window)
    action = window.menuBar().addMenu("Tools").addAction("Remove me")
    controller = QtCommandPalette.install(window, shortcut=None)
    controller.add_action(action)
    window.show()
    controller.open()
    palette = window.findChild(QtCommandPalette)
    assert _labels(palette) == ["Tools: Remove me"]
    action.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    qtbot.keyClick(_search(palette), Qt.Key.Key_Return)
    assert _labels(palette) == []
    assert palette.isVisible()
