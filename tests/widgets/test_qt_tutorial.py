"""Tests for the tutorial spotlight overlay."""

from __future__ import annotations

from pytestqt.qtbot import QtBot
from qtpy.QtCore import QPoint, QRect, Qt
from qtpy.QtWidgets import QPushButton, QWidget

from qtextra.widgets.qt_tutorial import QtTutorial, TutorialStep


def _tutorial_host(qtbot: QtBot) -> tuple[QWidget, QWidget, QPushButton, QPushButton]:
    host = QWidget()
    host.resize(480, 300)

    container = QWidget(host)
    container.setGeometry(40, 35, 300, 180)
    first = QPushButton("First", container)
    first.setGeometry(20, 25, 100, 40)
    second = QPushButton("Second", container)
    second.setGeometry(160, 100, 110, 45)

    qtbot.addWidget(host)
    host.show()
    qtbot.waitExposed(host)
    return host, container, first, second


def _make_tutorial(
    qtbot: QtBot,
    host: QWidget,
    targets: tuple[QPushButton, ...],
    *,
    show_overlay: bool = True,
) -> QtTutorial:
    tutorial = QtTutorial(host, show_overlay=show_overlay)
    qtbot.addWidget(tutorial)
    tutorial.set_steps([TutorialStep(message=target.text(), widget=target) for target in targets])
    tutorial.show()
    return tutorial


def _target_rect(overlay: QWidget, target: QWidget) -> QRect:
    top_left = overlay.mapFromGlobal(target.mapToGlobal(QPoint(0, 0)))
    return QRect(top_left, target.size())


def test_tutorial_overlay_covers_window_and_highlights_nested_target(qtbot: QtBot) -> None:
    host, _container, first, _second = _tutorial_host(qtbot)
    tutorial = _make_tutorial(qtbot, host, (first,))
    overlay = tutorial._overlay

    assert overlay is not None
    assert overlay.parentWidget() is host
    assert overlay.geometry() == host.rect()
    assert overlay._spotlight == _target_rect(overlay, first)
    assert overlay.testAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
    assert overlay.isVisible()


def test_tutorial_overlay_follows_current_step(qtbot: QtBot) -> None:
    host, _container, first, second = _tutorial_host(qtbot)
    tutorial = _make_tutorial(qtbot, host, (first, second))
    overlay = tutorial._overlay
    assert overlay is not None

    tutorial.set_step(1)

    assert overlay._spotlight == _target_rect(overlay, second)


def test_tutorial_overlay_tracks_host_and_target_ancestors(qtbot: QtBot) -> None:
    host, container, first, _second = _tutorial_host(qtbot)
    tutorial = _make_tutorial(qtbot, host, (first,))
    overlay = tutorial._overlay
    assert overlay is not None

    host.resize(560, 340)
    container.move(75, 60)

    qtbot.waitUntil(lambda: overlay.geometry() == host.rect())
    qtbot.waitUntil(lambda: overlay._spotlight == _target_rect(overlay, first))


def test_tutorial_overlay_tracks_target_visibility(qtbot: QtBot) -> None:
    host, _container, first, _second = _tutorial_host(qtbot)
    tutorial = _make_tutorial(qtbot, host, (first,))
    overlay = tutorial._overlay
    assert overlay is not None

    first.hide()
    qtbot.waitUntil(lambda: not overlay.isVisible())

    first.show()
    qtbot.waitUntil(overlay.isVisible)


def test_tutorial_overlay_can_be_disabled(qtbot: QtBot) -> None:
    host, _container, first, _second = _tutorial_host(qtbot)
    tutorial = _make_tutorial(qtbot, host, (first,), show_overlay=False)

    assert tutorial._overlay is None


def test_tutorial_close_removes_overlay(qtbot: QtBot) -> None:
    host, _container, first, _second = _tutorial_host(qtbot)
    tutorial = _make_tutorial(qtbot, host, (first,))
    overlay = tutorial._overlay
    assert overlay is not None

    tutorial.close()

    assert tutorial._overlay is None
    assert not overlay.isVisible()
