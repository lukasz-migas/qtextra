"""PyCharm-style static What's New dialog."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from pydantic import BaseModel, Field, model_validator
from qtpy.QtCore import QSize, Qt
from qtpy.QtGui import QPixmap, QResizeEvent
from qtpy.QtWidgets import QFrame, QGridLayout, QScrollArea, QSizePolicy, QVBoxLayout, QWidget

import qtextra.helpers as hp
from qtextra.config import QtStyler
from qtextra.widgets.qt_dialog import QtDialog


class WhatsNewVideo(BaseModel):
    """Data for the optional video tour section.

    Parameters
    ----------
    image_path : str
        Path to the preview image shown in the video section.
    url : str | None
        Optional link opened when the preview image or watch button is clicked.
    title : str
        Heading shown next to the preview image.
    button_text : str
        Text for the video action button.
    """

    image_path: str
    url: str | None = None
    title: str = "Take a video tour"
    button_text: str = "Watch"


class WhatsNewHighlight(BaseModel):
    """Data for a single highlight tile.

    Parameters
    ----------
    title : str
        Highlight title.
    subtitle : str
        Wrapped subtitle text. Basic rich text is supported.
    image_path : str
        Path to the highlight image.
    """

    title: str
    subtitle: str
    image_path: str


class WhatsNewStaticContent(BaseModel):
    """Content model for the static What's New layout.

    Parameters
    ----------
    app_name : str
        Application name used in the dialog title.
    highlights : list[WhatsNewHighlight]
        Highlight tiles to render.
    version : str | None
        Optional version suffix for the dialog title.
    video : WhatsNewVideo | None
        Optional video tour section.
    cta_label : str | None
        Optional bottom button label.
    cta_url : str | None
        Optional bottom button URL.
    """

    app_name: str
    highlights: list[WhatsNewHighlight] = Field(default_factory=list)
    version: str | None = None
    video: WhatsNewVideo | None = None
    cta_label: str | None = None
    cta_url: str | None = None

    @model_validator(mode="after")
    def _validate_highlights(self) -> WhatsNewStaticContent:
        """Validate that the content contains at least one highlight."""
        if not self.highlights:
            raise ValueError("At least one highlight is required.")
        return self


class _ScaledImageLabel(QWidget):
    """Image container that displays a fixed pre-scaled pixmap."""

    def __init__(
        self,
        image_path: str,
        parent: QWidget | None = None,
        *,
        minimum_size: QSize | None = None,
        clickable: bool = False,
    ) -> None:
        super().__init__(parent)
        if minimum_size is None:
            minimum_size = QSize(320, 180)
        self._target_size = minimum_size
        self._click_callback: Callable[[], None] | None = None
        self._label = hp.make_label(
            self,
            "Preview image unavailable",
            alignment=Qt.AlignmentFlag.AlignCenter,
            wrap=True,
        )
        self._label.setMinimumSize(minimum_size)
        self._label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        if clickable:
            self._label.setCursor(Qt.CursorShape.PointingHandCursor)
        hp.make_v_layout(self._label, margin=0, parent=self)
        self.setFixedSize(minimum_size)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._load_image(image_path)

    def set_click_callback(self, callback: Callable[[], None] | None) -> None:
        """Set the callback invoked when the image is clicked."""
        self._click_callback = callback
        if callback is not None and hasattr(self._label, "evt_clicked"):
            self._label.evt_clicked.connect(callback)

    def _load_image(self, image_path: str) -> None:
        """Load image from disk and show a placeholder when it fails."""
        path = Path(image_path)
        if not path.exists():
            self._label.setText(f"Image not found:\n{path}")
            return

        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            self._label.setText(f"Could not load image:\n{path}")
            return

        scaled = pixmap.scaled(
            self._target_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._label.setPixmap(scaled)
        self._label.setText("")


class _HighlightTile(QFrame):
    """Tile showing one highlight image and text."""

    def __init__(self, highlight: WhatsNewHighlight, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("whatsNewHighlightTile")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)

        image = _ScaledImageLabel(highlight.image_path, self, minimum_size=QSize(360, 205))
        title = hp.make_label(
            self, highlight.title, bold=True, wrap=True, font_size=14, object_name="whatsNewTileTitle"
        )
        subtitle = hp.make_label(
            self, highlight.subtitle, enable_url=True, wrap=True, object_name="whatsNewTileSubtitle"
        )
        subtitle.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        layout = hp.make_v_layout(margin=(14, 14, 14, 14), spacing=10, parent=self)
        layout.addWidget(image)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addStretch(1)


class QtWhatsNewStaticWidget(QWidget):
    """Embeddable static What's New widget."""

    TWO_COLUMN_MIN_WIDTH = 840

    def __init__(self, content: WhatsNewStaticContent, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.content = content
        self._tiles: list[_HighlightTile] = []
        self._column_count = 0
        self._build()

    def column_count(self) -> int:
        """Return the current number of columns used by the highlight grid."""
        return self._column_count

    def _build(self) -> None:
        """Build the scrollable content layout."""
        root = hp.make_v_layout(margin=0, spacing=0, parent=self)

        self._scroll = QScrollArea(self)
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setObjectName("whatsNewStaticScroll")
        self._scroll.viewport().setObjectName("whatsNewStaticViewport")

        self._body = QWidget(self._scroll)
        self._body.setObjectName("whatsNewStaticBody")
        self._body_layout = hp.make_v_layout(margin=(20, 20, 20, 20), spacing=24, parent=self._body)

        if self.content.video is not None:
            self._body_layout.addWidget(self._make_video_section(self.content.video))

        self._body_layout.addWidget(hp.make_label(self._body, "Highlights", bold=True, font_size=22))

        self._grid_widget = QWidget(self._body)
        self._grid_layout = QGridLayout(self._grid_widget)
        self._grid_layout.setContentsMargins(0, 0, 0, 0)
        self._grid_layout.setHorizontalSpacing(28)
        self._grid_layout.setVerticalSpacing(28)
        for highlight in self.content.highlights:
            tile = _HighlightTile(highlight, self._grid_widget)
            self._tiles.append(tile)
        self._body_layout.addWidget(self._grid_widget)

        if self.content.cta_label and self.content.cta_url:
            cta_btn = hp.make_btn(
                self._body,
                self.content.cta_label,
                func=self._open_cta_url,
                object_name="success_btn",
            )
            self._body_layout.addLayout(hp.make_h_layout(cta_btn, margin=0, stretch_before=True, stretch_after=True))

        self._body_layout.addStretch(1)
        self._scroll.setWidget(self._body)
        root.addWidget(self._scroll)
        self._apply_style()
        self._relayout_tiles()

    def _make_video_section(self, video: WhatsNewVideo) -> QWidget:
        """Build the optional video tour section."""
        section = QFrame(self._body)
        section.setObjectName("whatsNewVideoSection")
        layout = hp.make_h_layout(margin=0, spacing=24, parent=section)

        text_layout = hp.make_v_layout(margin=0, spacing=16)
        title = hp.make_label(section, video.title, bold=True, wrap=True, font_size=34)
        text_layout.addWidget(title)
        if video.url:
            self.video_button = hp.make_btn(
                section, video.button_text, func=self._open_video_url, object_name="success_btn"
            )
            text_layout.addWidget(self.video_button, 0, Qt.AlignmentFlag.AlignLeft)
        text_layout.addStretch(1)

        image = _ScaledImageLabel(video.image_path, section, minimum_size=QSize(520, 240), clickable=bool(video.url))
        if video.url:
            image.set_click_callback(self._open_video_url)

        layout.addLayout(text_layout, 3)
        layout.addWidget(image, 4)
        return section

    def _apply_style(self) -> None:
        """Apply local theme-aware styling."""
        background = QtStyler.background().name()
        foreground = QtStyler.foreground().name()
        text = QtStyler.text().name()
        muted_text = QtStyler.text_muted().name()
        self.setStyleSheet(
            f"""
            QScrollArea#whatsNewStaticScroll,
            QWidget#whatsNewStaticViewport,
            QWidget#whatsNewStaticBody {{
                background-color: {background};
            }}
            QFrame#whatsNewVideoSection {{
                background: transparent;
            }}
            QFrame#whatsNewHighlightTile {{
                background-color: {foreground};
                border-radius: 6px;
            }}
            QLabel#whatsNewTileTitle {{
                color: {text};
                background: transparent;
            }}
            QLabel#whatsNewTileSubtitle {{
                color: {muted_text};
                background: transparent;
            }}
            """,
        )

    def resizeEvent(self, event: QResizeEvent) -> None:
        """Update the tile grid when the available width changes."""
        self._relayout_tiles()
        super().resizeEvent(event)

    def _relayout_tiles(self) -> None:
        """Arrange highlight tiles in one or two columns."""
        width = self.width()
        if hasattr(self, "_scroll"):
            width = max(width, self._scroll.width(), self._scroll.viewport().width())
        columns = 2 if width >= self.TWO_COLUMN_MIN_WIDTH else 1
        if columns == self._column_count and self._grid_layout.count() == len(self._tiles):
            return

        while self._grid_layout.count():
            item = self._grid_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(self._grid_widget)

        for index, tile in enumerate(self._tiles):
            row, column = divmod(index, columns)
            self._grid_layout.addWidget(tile, row, column)
        for column in range(2):
            self._grid_layout.setColumnStretch(column, 1 if column < columns else 0)
        self._column_count = columns

    def _open_video_url(self) -> None:
        """Open the configured video URL."""
        if self.content.video and self.content.video.url:
            hp.open_link(self.content.video.url)

    def _open_cta_url(self) -> None:
        """Open the configured CTA URL."""
        if self.content.cta_url:
            hp.open_link(self.content.cta_url)


class QtWhatsNewStaticDialog(QtDialog):
    """Dialog wrapper for :class:`QtWhatsNewStaticWidget`."""

    def __init__(self, content: WhatsNewStaticContent, parent: QWidget | None = None) -> None:
        self.content = content
        title = f"What's New in {content.app_name}"
        if content.version:
            title += f" {content.version}"
        super().__init__(parent, title=title)
        self.resize(1100, 760)
        self.setMinimumSize(860, 560)

    def make_panel(self) -> QVBoxLayout:
        """Build and return the dialog layout."""
        self.content_widget = QtWhatsNewStaticWidget(self.content, self)
        return hp.make_v_layout(self.content_widget, margin=0, spacing=0)


WhatsNewStaticDialog = QtWhatsNewStaticDialog
