from pathlib import Path

from qtpy.QtWidgets import QApplication

from qtextra.config import THEMES
from qtextra.dialogs.qt_whats_new_static import (
    QtWhatsNewStaticDialog,
    WhatsNewHighlight,
    WhatsNewStaticContent,
    WhatsNewVideo,
)

ASSET = str(Path(__file__).resolve().parents[1] / "docs" / "assets" / "dialog_whats_new.jpg")

CONTENT = WhatsNewStaticContent(
    app_name="MyApp",
    version="2026.1",
    video=WhatsNewVideo(
        image_path=ASSET,
        url="https://example.com",
    ),
    highlights=[
        WhatsNewHighlight(
            title="Faster debugging",
            subtitle="Attach to local and remote processes with a cleaner configuration flow.",
            image_path=ASSET,
        ),
        WhatsNewHighlight(
            title="Remote environments",
            subtitle="Manage remote interpreters and package workflows from the same release notes surface.",
            image_path=ASSET,
        ),
        WhatsNewHighlight(
            title="Bring your own tools",
            subtitle="Show users the integrations that matter most in a concise visual tile.",
            image_path=ASSET,
        ),
        WhatsNewHighlight(
            title="Web tooling",
            subtitle="Use basic rich text in subtitles, including <b>emphasis</b> and links.",
            image_path=ASSET,
        ),
    ],
    cta_label="Read release notes",
    cta_url="https://example.com/release-notes",
)

app = QApplication([])
dlg = QtWhatsNewStaticDialog(CONTENT)
THEMES.apply(dlg)
dlg.show()

app.exec_()
