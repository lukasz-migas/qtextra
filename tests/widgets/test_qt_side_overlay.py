"""Tests for the modal side overlay widget."""

from __future__ import annotations

from pathlib import Path

from qtpy.QtCore import QBuffer, QByteArray, QIODevice, QObject, QPoint, Qt, Signal
from qtpy.QtGui import QImage, QPixmap
from qtpy.QtWidgets import QApplication, QDialog, QWidget

from qtextra.widgets.qt_side_overlay import (
    QtSideOverlay,
    SideOverlayImage,
    SideOverlaySeparator,
    SideOverlaySubtitle,
    SideOverlayText,
    SideOverlayTitle,
    _SideOverlayImageLabel,
)


class _FakeReply(QObject):
    """Minimal reply object for deterministic remote-image tests."""

    finished = Signal()

    def __init__(self, data: QByteArray, error: int = 0) -> None:
        super().__init__()
        self._data = data
        self._error = error
        self.aborted = False

    def error(self) -> int:
        """Return the configured network error value."""
        return self._error

    def readAll(self) -> QByteArray:
        """Return the configured response body."""
        return self._data

    def abort(self) -> None:
        """Record an aborted request."""
        self.aborted = True


class _FakeNetworkManager(QObject):
    """Network manager returning a prepared reply."""

    def __init__(self, reply: _FakeReply) -> None:
        super().__init__()
        self.reply = reply

    def get(self, _request) -> _FakeReply:
        """Return the prepared reply without using the network."""
        return self.reply


def _host(qtbot, width: int = 640) -> QWidget:
    host = QWidget()
    host.resize(width, 420)
    qtbot.addWidget(host)
    host.show()
    qtbot.waitExposed(host)
    return host


def _open(qtbot, overlay: QtSideOverlay) -> None:
    with qtbot.waitSignal(overlay.evt_opened, timeout=500):
        overlay.open()


def _image_bytes() -> QByteArray:
    image = QImage(80, 40, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.red)
    data = QByteArray()
    buffer = QBuffer(data)
    assert buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    assert image.save(buffer, "PNG")
    return data


def test_side_overlay_opens_on_right_and_clamps_width(qtbot) -> None:
    host = _host(qtbot, width=320)
    overlay = QtSideOverlay(host, header_title="July 14", blocks=[SideOverlayText("Body")], animation_duration=0)
    qtbot.addWidget(overlay)

    _open(qtbot, overlay)

    assert overlay.parentWidget() is host
    assert overlay.geometry() == host.rect()
    assert overlay._panel.width() == host.width()
    assert overlay._panel.x() == 0
    assert overlay.header_title_label.text() == "July 14"


def test_side_overlay_supports_left_placement_and_host_resize(qtbot) -> None:
    host = _host(qtbot)
    overlay = QtSideOverlay(host, side="left", width=280, animation_duration=0)
    qtbot.addWidget(overlay)

    _open(qtbot, overlay)
    host.resize(720, 500)
    qtbot.waitUntil(lambda: overlay.geometry() == host.rect())

    assert overlay._panel.x() == 0
    assert overlay._panel.width() == 280
    assert overlay._panel.height() == host.height()


def test_side_overlay_close_button_and_escape_dismiss(qtbot) -> None:
    host = _host(qtbot)
    overlay = QtSideOverlay(host, animation_duration=0)
    qtbot.addWidget(overlay)

    _open(qtbot, overlay)
    with qtbot.waitSignal(overlay.evt_closed, timeout=500):
        qtbot.mouseClick(overlay.close_button, Qt.MouseButton.LeftButton)
    assert overlay.isVisible() is False

    _open(qtbot, overlay)
    with qtbot.waitSignal(overlay.evt_closed, timeout=500):
        qtbot.keyClick(overlay, Qt.Key.Key_Escape)
    assert overlay.isVisible() is False


def test_side_overlay_covers_dialog_and_consumes_the_scrim(qtbot) -> None:
    dialog = QDialog()
    dialog.resize(420, 280)
    qtbot.addWidget(dialog)
    dialog.show()
    qtbot.waitExposed(dialog)
    overlay = QtSideOverlay(dialog, width=220, animation_duration=0)
    qtbot.addWidget(overlay)

    _open(qtbot, overlay)

    assert overlay.parentWidget() is dialog
    assert overlay.geometry() == dialog.rect()
    assert overlay.childAt(QPoint(10, 10)) is None
    assert QApplication.widgetAt(dialog.mapToGlobal(QPoint(10, 10))) is overlay


def test_side_overlay_renders_ordered_content_and_images(qtbot, tmp_path: Path) -> None:
    host = _host(qtbot)
    local_path = tmp_path / "local.png"
    image = QImage(120, 60, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.blue)
    assert image.save(str(local_path))
    pixmap = QPixmap.fromImage(image)
    blocks = [
        SideOverlayTitle("Introducing Tabs"),
        SideOverlaySubtitle("A better workflow"),
        SideOverlayText("First paragraph."),
        SideOverlaySeparator(),
        SideOverlayImage(local_path),
        SideOverlayImage(pixmap),
        SideOverlayImage(image),
        SideOverlayText("Last paragraph."),
    ]
    overlay = QtSideOverlay(host, blocks=blocks, animation_duration=0)
    qtbot.addWidget(overlay)

    assert overlay.blocks() == tuple(blocks)
    assert len(overlay.findChildren(_SideOverlayImageLabel)) == 3
    assert overlay.findChild(QWidget, "qtSideOverlayTitle") is not None
    assert overlay.findChild(QWidget, "qtSideOverlaySubtitle") is not None
    assert overlay.findChild(QWidget, "qtSideOverlaySeparator") is not None
    assert all(not label._source_pixmap.isNull() for label in overlay.findChildren(_SideOverlayImageLabel))


def test_side_overlay_invalid_images_are_removed_and_reported(qtbot, tmp_path: Path) -> None:
    host = _host(qtbot)
    invalid_path = tmp_path / "missing.png"
    overlay = QtSideOverlay(host, animation_duration=0)
    qtbot.addWidget(overlay)

    with qtbot.waitSignal(overlay.evt_image_failed, timeout=500) as signal:
        overlay.set_blocks([SideOverlayImage(invalid_path)])

    assert signal.args == [str(invalid_path)]
    assert overlay.findChildren(_SideOverlayImageLabel) == []


def test_side_overlay_decodes_remote_images_and_reports_failures(qtbot) -> None:
    host = _host(qtbot)
    overlay = QtSideOverlay(host, animation_duration=0)
    qtbot.addWidget(overlay)

    success_reply = _FakeReply(_image_bytes())
    overlay._network_manager = _FakeNetworkManager(success_reply)
    overlay.set_blocks([SideOverlayImage("https://example.com/image.png")])
    _open(qtbot, overlay)
    success_reply.finished.emit()
    qtbot.wait(20)
    image_label = overlay.findChild(_SideOverlayImageLabel)
    assert image_label is not None
    assert image_label._source_pixmap.isNull() is False
    for width in (520, 720, 480, 640):
        host.resize(width, 420)
        qtbot.wait(5)

    failure_reply = _FakeReply(QByteArray(b"not an image"))
    overlay._network_manager = _FakeNetworkManager(failure_reply)
    with qtbot.waitSignal(overlay.evt_image_failed, timeout=500) as signal:
        overlay.set_blocks([SideOverlayImage("https://example.com/bad.png")])
        failure_reply.finished.emit()

    assert signal.args == ["https://example.com/bad.png"]
    assert overlay.findChildren(_SideOverlayImageLabel) == []


def test_side_overlay_scrolls_long_content_and_validates_public_inputs(qtbot) -> None:
    host = _host(qtbot)
    overlay = QtSideOverlay(host, blocks=[SideOverlayText("Long text") for _ in range(60)], animation_duration=0)
    qtbot.addWidget(overlay)

    _open(qtbot, overlay)

    assert overlay.scroll_area.verticalScrollBar().maximum() > 0
    with __import__("pytest").raises(ValueError, match="side"):
        QtSideOverlay(host, side="top")
    with __import__("pytest").raises(TypeError, match="Unsupported"):
        overlay.set_blocks([SideOverlayText("Valid"), object()])
