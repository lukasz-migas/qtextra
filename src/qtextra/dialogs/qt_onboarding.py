"""Onboarding / what's-new dialog."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel
from qtpy.QtCore import Qt, Signal
from qtpy.QtGui import QKeyEvent, QPainter, QPaintEvent, QPen, QPixmap, QResizeEvent
from qtpy.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

import qtextra.helpers as hp
from qtextra.config import QtStyler
from qtextra.widgets.qt_dialog import QtDialog


class WhatsNewPage(BaseModel):
    """Data for a single onboarding page.

    Parameters
    ----------
    title : str
        Page heading.
    body_html : str
        Rich text body shown on the left side.
    image_path : str | None
        Optional image path rendered on the right side.
    """

    title: str
    body_html: str
    image_path: str | None = None


class _DotIndicator(QWidget):
    """Lightweight page indicator."""

    def __init__(self, count: int = 0, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._count = max(0, count)
        self._current = 0
        self.setMinimumHeight(20)
        self.setMinimumWidth(max(24, count * 18))

    def set_count(self, count: int) -> None:
        """Update the number of visible dots."""
        self._count = max(0, count)
        self._current = min(self._current, max(0, self._count - 1))
        self.updateGeometry()
        self.update()

    def set_current_index(self, index: int) -> None:
        """Update the active dot."""
        if self._count == 0:
            self._current = 0
        else:
            self._current = max(0, min(index, self._count - 1))
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        """Paint indicator dots."""
        if self._count == 0:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        spacing = 18
        inactive_radius = 4
        active_radius = 6
        total_width = (self._count - 1) * spacing + active_radius * 2
        origin_x = (self.width() - total_width) // 2 + active_radius
        center_y = self.height() // 2

        for i in range(self._count):
            center_x = origin_x + i * spacing
            if i == self._current:
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.setPen(QPen(QtStyler.highlight(), 2))
                painter.drawEllipse(center_x - active_radius, center_y - active_radius, 12, 12)
            else:
                painter.setBrush(QtStyler.foreground())
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawEllipse(center_x - inactive_radius, center_y - inactive_radius, 8, 8)

        super().paintEvent(event)


class _OnboardingPageWidget(QWidget):
    """Single page view for the onboarding dialog."""

    def __init__(self, page: WhatsNewPage, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.page = page
        self._original_pixmap: QPixmap | None = None
        self._build()
        self._load_image()

    def _build(self) -> None:
        """Create the page layout."""
        root = hp.make_h_layout(margin=(24, 24, 24, 24), spacing=24, parent=self)

        text_container = QWidget(self)
        text_layout = hp.make_v_layout(margin=0, spacing=12, parent=text_container)

        title = hp.make_label(self, self.page.title, wrap=True, bold=True, font_size=22)
        title.setTextFormat(Qt.TextFormat.PlainText)

        body = hp.make_label(self, self.page.body_html, wrap=True, enable_url=True)
        body.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        body.setOpenExternalLinks(True)
        body.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        text_layout.addWidget(title)
        text_layout.addWidget(body)
        text_layout.addStretch(1)

        self.image_frame = QFrame(self)
        self.image_frame.setObjectName("onboardingImageFrame")
        self.image_frame.setMinimumWidth(320)
        self.image_frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        image_layout = hp.make_v_layout(margin=(16, 16, 16, 16), parent=self.image_frame)
        self.image_label = hp.make_label(
            self.image_frame,
            "No preview image",
            alignment=Qt.AlignmentFlag.AlignCenter,
            wrap=True,
        )
        self.image_label.setMinimumSize(280, 220)
        image_layout.addWidget(self.image_label, 1)

        root.addWidget(text_container, 3)
        root.addWidget(self.image_frame, 4)

        self.setStyleSheet(
            """
            QFrame#onboardingImageFrame {
                border: 1px solid palette(mid);
                border-radius: 12px;
                background: palette(base);
            }
            """,
        )

    def _load_image(self) -> None:
        """Load the configured image if available."""
        image_path = self.page.image_path
        if not image_path:
            self._original_pixmap = None
            return

        path = Path(image_path)
        if not path.exists():
            self.image_label.setText(f"Image not found:\n{path}")
            self._original_pixmap = None
            return

        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            self.image_label.setText(f"Could not load image:\n{path}")
            self._original_pixmap = None
            return

        self._original_pixmap = pixmap
        self._update_pixmap()

    def resizeEvent(self, event: QResizeEvent) -> None:
        """Keep the preview image scaled to the available space."""
        self._update_pixmap()
        super().resizeEvent(event)

    def _update_pixmap(self) -> None:
        """Scale the image to the current preview area."""
        if self._original_pixmap is None:
            return

        scaled = self._original_pixmap.scaled(
            self.image_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.image_label.setPixmap(scaled)
        self.image_label.setText("")


class OnboardingDialog(QtDialog):
    """Dialog for onboarding or release-note walkthroughs."""

    skipped = Signal()
    finished_viewing = Signal()
    dont_show_again_changed = Signal(bool)

    def __init__(
        self,
        pages: list[WhatsNewPage],
        parent: QWidget | None = None,
        *,
        app_name: str = "Application",
        version: str | None = None,
        show_dont_show_again: bool = True,
    ) -> None:
        if not pages:
            raise ValueError("At least one page is required.")

        self.pages = list(pages)
        self.app_name = app_name
        self.version = version
        self.show_dont_show_again = show_dont_show_again
        self._dont_show_again = False
        super().__init__(parent, title=f"What's New in {app_name}")
        self.setMinimumSize(900, 620)
        self.resize(1040, 720)
        self._update_ui()

    # noinspection PyAttributeOutsideInit
    def make_panel(self) -> QVBoxLayout:
        """Build the onboarding layout."""
        root = hp.make_v_layout(margin=(16, 16, 16, 16), spacing=12)

        title_text = f"What's New in {self.app_name}"
        if self.version:
            title_text += f" {self.version}"

        header_layout = hp.make_h_layout(spacing=12)
        header_text_layout = hp.make_v_layout(margin=0, spacing=2)
        header_text_layout.addWidget(hp.make_label(self, title_text, bold=True, font_size=24))
        header_text_layout.addWidget(
            hp.make_label(self, "Discover the latest features and improvements.", object_name="subheader"),
        )
        header_layout.addLayout(header_text_layout)
        root.addLayout(header_layout)
        root.addWidget(hp.make_h_line(self))

        self.stack = QStackedWidget(self)
        self.stack.setObjectName("onboardingStack")
        for page in self.pages:
            self.stack.addWidget(_OnboardingPageWidget(page, self))
        root.addWidget(self.stack, 1)

        self.skip_button = hp.make_btn(self, "Skip", func=self._on_skip, object_name="cancel_btn")
        self.dont_show_again_checkbox = QCheckBox("Don't show this again", self)
        self.dont_show_again_checkbox.setVisible(self.show_dont_show_again)
        self.dont_show_again_checkbox.toggled.connect(self._on_dont_show_again_toggled)

        self.dots = _DotIndicator(len(self.pages), self)
        self.back_button = hp.make_btn(self, "‹ Previous", func=self.previous_page, bold=True)
        self.next_button = hp.make_btn(self, "Next ›", func=self.next_page, object_name="success_btn")

        left_layout = hp.make_h_layout(self.skip_button, margin=0, stretch_after=True)
        right_layout = hp.make_h_layout(self.back_button, self.next_button, margin=0, spacing=8, stretch_before=True)

        bottom_layout = QHBoxLayout()
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(0)
        bottom_layout.addLayout(left_layout, 1)
        bottom_layout.addWidget(self.dots, 0, Qt.AlignmentFlag.AlignVCenter)
        bottom_layout.addLayout(right_layout, 1)

        root.addWidget(hp.make_h_line(self))
        root.addLayout(bottom_layout)
        root.addWidget(self.dont_show_again_checkbox, 0, Qt.AlignmentFlag.AlignLeft)
        return root

    def current_index(self) -> int:
        """Return the current page index."""
        return self.stack.currentIndex()

    def set_current_index(self, index: int) -> None:
        """Set the current page index."""
        index = max(0, min(index, self.stack.count() - 1))
        self.stack.setCurrentIndex(index)
        self._update_ui()

    def next_page(self) -> None:
        """Advance to the next page or finish on the last page."""
        current = self.current_index()
        if current < self.stack.count() - 1:
            self.set_current_index(current + 1)
        else:
            self._on_done()

    def previous_page(self) -> None:
        """Navigate to the previous page."""
        current = self.current_index()
        if current > 0:
            self.set_current_index(current - 1)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Support arrow-key navigation through the onboarding pages."""
        if event.key() in (Qt.Key.Key_Right, Qt.Key.Key_Down, Qt.Key.Key_PageDown):
            self.next_page()
            return
        if event.key() in (Qt.Key.Key_Left, Qt.Key.Key_Up, Qt.Key.Key_PageUp):
            self.previous_page()
            return
        super().keyPressEvent(event)

    def _update_ui(self) -> None:
        """Refresh button and indicator state."""
        idx = self.current_index()
        last = self.stack.count() - 1

        self.back_button.setEnabled(idx > 0)
        self.dots.set_current_index(idx)
        is_last = idx == last
        self.next_button.setText("Done" if is_last else "Next ›")

    def _on_skip(self) -> None:
        """Skip the onboarding flow."""
        self.skipped.emit()
        self.reject()

    def _on_done(self) -> None:
        """Finish the onboarding flow."""
        self.finished_viewing.emit()
        self.accept()

    def _on_dont_show_again_toggled(self, state: bool) -> None:
        """Mirror the checkbox state so it is still available after teardown."""
        self._dont_show_again = bool(state)
        self.dont_show_again_changed.emit(self._dont_show_again)

    def dont_show_again(self) -> bool:
        """Return whether the user opted out of future onboarding prompts."""
        try:
            return self.dont_show_again_checkbox.isChecked()
        except RuntimeError:
            return self._dont_show_again


if __name__ == "__main__":
    import sys

    from qtpy.QtWidgets import QApplication

    from qtextra.utils.dev import apply_style

    pages = [
        WhatsNewPage(
            title="Work faster with the new dashboard",
            body_html="""
            <p>
                The new dashboard gives you a clearer overview of your projects,
                recent files, and activity.
            </p>
            <ul>
                <li>Faster access to recent work</li>
                <li>Cleaner layout and improved navigation</li>
                <li>Better support for large screens</li>
            </ul>
            """,
            image_path="/path-to-an-image.png",
        ),
        WhatsNewPage(
            title="Review feature highlights",
            body_html="""
            <p>
                Each release can now include rich HTML content, screenshots,
                and guided feature summaries.
            </p>
            <p>
                You can use <b>basic HTML</b> here, including lists, links,
                emphasis, and headings.
            </p>
            <p>
                <a href="https://example.com">Learn more</a>
            </p>
            """,
            image_path="/path-to-an-image.png",
        ),
        WhatsNewPage(
            title="Stay in control",
            body_html="""
            <p>
                Users can move backward and forward through the release notes,
                or skip them entirely.
            </p>
            <p>
                You can also persist the <i>Don’t show again</i> setting using
                QSettings.
            </p>
            """,
            image_path=None,
        ),
    ]
    app = QApplication(sys.argv)
    dlg = OnboardingDialog(
        pages,
        app_name="MyApp",
        version="v2.1",
        show_dont_show_again=True,
    )
    apply_style(dlg, theme_name="dark")

    if dlg.exec():
        print("Finished viewing")
    else:
        print("Skipped/closed")
    print("Don't show again:", dlg.dont_show_again())
    sys.exit(0)
