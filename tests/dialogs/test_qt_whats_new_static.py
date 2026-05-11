from __future__ import annotations

from pathlib import Path

import pytest
from qtpy.QtCore import QSize

from qtextra.dialogs.qt_whats_new_static import (
    QtWhatsNewStaticDialog,
    QtWhatsNewStaticWidget,
    WhatsNewHighlight,
    WhatsNewStaticContent,
    WhatsNewVideo,
    _ScaledImageLabel,
)


@pytest.fixture
def image_path() -> str:
    return str(Path(__file__).resolve().parents[1] / "_test_data" / "qtextra.png")


@pytest.fixture
def highlights(image_path: str) -> list[WhatsNewHighlight]:
    return [
        WhatsNewHighlight(title="Debugger updates", subtitle="Better process attach support.", image_path=image_path),
        WhatsNewHighlight(
            title="Remote workflows", subtitle="Improved support for remote environments.", image_path=image_path
        ),
        WhatsNewHighlight(title="AI tools", subtitle="Bring your own coding tools.", image_path=image_path),
    ]


def test_whats_new_static_content_defaults(highlights: list[WhatsNewHighlight]) -> None:
    content = WhatsNewStaticContent(app_name="App", highlights=highlights)
    dumped = content.model_dump()

    assert dumped["app_name"] == "App"
    assert dumped["version"] is None
    assert dumped["video"] is None
    assert dumped["cta_label"] is None
    assert dumped["cta_url"] is None
    assert len(dumped["highlights"]) == 3


def test_whats_new_static_content_requires_highlights() -> None:
    with pytest.raises(ValueError, match="At least one highlight is required"):
        WhatsNewStaticContent(app_name="App", highlights=[])


def test_whats_new_static_dialog_builds_with_highlights_only(
    qtbot,
    highlights: list[WhatsNewHighlight],
) -> None:
    content = WhatsNewStaticContent(app_name="App", version="1.2.3", highlights=highlights)
    dialog = QtWhatsNewStaticDialog(content)
    qtbot.addWidget(dialog)
    dialog.show()

    assert dialog.windowTitle() == "What's New in App 1.2.3"
    assert dialog.content_widget.column_count() in (1, 2)


def test_whats_new_static_dialog_builds_with_video_and_cta(
    qtbot,
    image_path: str,
    highlights: list[WhatsNewHighlight],
) -> None:
    content = WhatsNewStaticContent(
        app_name="App",
        highlights=highlights,
        video=WhatsNewVideo(image_path=image_path, url="https://example.com/video"),
        cta_label="Learn more",
        cta_url="https://example.com",
    )
    dialog = QtWhatsNewStaticDialog(content)
    qtbot.addWidget(dialog)
    dialog.show()

    assert dialog.content_widget.content.video is not None
    assert dialog.content_widget.content.cta_url == "https://example.com"


def test_whats_new_static_invalid_image_does_not_crash(qtbot) -> None:
    content = WhatsNewStaticContent(
        app_name="App",
        highlights=[
            WhatsNewHighlight(
                title="Missing image",
                subtitle="The widget should show a placeholder.",
                image_path="/missing/image.png",
            ),
        ],
    )
    widget = QtWhatsNewStaticWidget(content)
    qtbot.addWidget(widget)
    widget.show()

    assert widget.column_count() in (1, 2)


def test_whats_new_static_image_is_not_rescaled_on_resize(qtbot, image_path: str) -> None:
    image = _ScaledImageLabel(image_path, minimum_size=QSize(240, 120))
    qtbot.addWidget(image)
    image.show()

    pixmap = image._label.pixmap()
    assert pixmap is not None
    initial_size = pixmap.size()

    image.resize(480, 240)
    qtbot.wait(10)

    pixmap = image._label.pixmap()
    assert pixmap is not None
    assert pixmap.size() == initial_size


def test_whats_new_static_style_sets_body_and_tile_contrast(qtbot, highlights: list[WhatsNewHighlight]) -> None:
    content = WhatsNewStaticContent(app_name="App", highlights=highlights)
    widget = QtWhatsNewStaticWidget(content)
    qtbot.addWidget(widget)

    style = widget.styleSheet()
    assert "QWidget#whatsNewStaticBody" in style
    assert "QFrame#whatsNewHighlightTile" in style
    assert "QLabel#whatsNewTileTitle" in style
    assert "QLabel#whatsNewTileSubtitle" in style
    assert "palette(window)" not in style


def test_whats_new_static_links_open_with_helper(
    qtbot,
    monkeypatch: pytest.MonkeyPatch,
    image_path: str,
    highlights: list[WhatsNewHighlight],
) -> None:
    opened: list[str] = []
    monkeypatch.setattr("qtextra.dialogs.qt_whats_new_static.hp.open_link", opened.append)
    content = WhatsNewStaticContent(
        app_name="App",
        highlights=highlights,
        video=WhatsNewVideo(image_path=image_path, url="https://example.com/video"),
        cta_label="Learn more",
        cta_url="https://example.com",
    )
    widget = QtWhatsNewStaticWidget(content)
    qtbot.addWidget(widget)

    widget._open_video_url()
    widget._open_cta_url()

    assert opened == ["https://example.com/video", "https://example.com"]


def test_whats_new_static_responsive_columns(qtbot, highlights: list[WhatsNewHighlight]) -> None:
    content = WhatsNewStaticContent(app_name="App", highlights=highlights)
    widget = QtWhatsNewStaticWidget(content)
    qtbot.addWidget(widget)

    widget._scroll.resize(900, 600)
    widget._relayout_tiles()
    assert widget.column_count() == 2

    widget._scroll.resize(500, 600)
    widget._relayout_tiles()
    assert widget.column_count() == 1
