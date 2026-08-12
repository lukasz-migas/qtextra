"""QtWelcomeDialog example."""

from pathlib import Path

from qtpy.QtWidgets import QApplication

from qtextra.config import THEMES
from qtextra.dialogs.qt_welcome import QtWelcomeDialog, WelcomeListItem, WelcomePage

image_path = Path(__file__).resolve().parents[1] / "tests" / "_test_data" / "qtextra.png"
pages = [
    WelcomePage(
        title="Let's set up your project",
        description="A few quick pages introduce the tools available in your new workspace.",
        image_path=str(image_path),
        action_text="Start tour",
        items=[
            WelcomeListItem(
                title="Reusable widgets",
                description="Build the interface from qtextra's themed components.",
                icon="template",
            ),
            WelcomeListItem(
                title="Application styling",
                description="Follow the active qtextra theme automatically.",
                icon="paint_palette",
            ),
            WelcomeListItem(
                title="Helpful examples",
                description="Use the example gallery as a starting point.",
                icon="tutorial",
            ),
        ],
    ),
    WelcomePage(
        title="Everything stays consistent",
        description="The welcome dialog works with light and dark qtextra themes.",
        items=[
            WelcomeListItem(title="Theme-aware icons", icon="star"),
            WelcomeListItem(title="Keyboard navigation", icon="shortcut"),
            WelcomeListItem(title="Scrollable content", icon="list"),
        ],
    ),
    WelcomePage(
        title="You're ready",
        description="Open your project and start building.",
        items=[WelcomeListItem(title="Create something useful", icon="run")],
    ),
]

app = QApplication([])
dialog = QtWelcomeDialog(pages, title="Welcome to qtextra")
THEMES.apply(dialog)
dialog.exec_()
