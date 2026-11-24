from qtpy import API_NAME, PYQT_VERSION, PYSIDE_VERSION

from qtextra.utils.qt import qt_might_be_rich_text
from qtextra.utils.utilities import get_system_info


def test_system_info_includes_binding_version() -> None:
    version = PYSIDE_VERSION if API_NAME == "PySide6" else PYQT_VERSION
    assert version
    assert f"{API_NAME}: {version}" in get_system_info()


def test_rich_text_detection() -> None:
    assert qt_might_be_rich_text("<b>text</b>")
    assert not qt_might_be_rich_text("plain text")
