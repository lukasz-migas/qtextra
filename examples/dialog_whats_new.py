from qtpy.QtWidgets import QApplication

from qtextra.config import THEMES
from qtextra.dialogs.qt_whats_new import WhatsNewDialog, WhatsNewPage

DEMO_PAGES = [
    WhatsNewPage(
        title="Welcome to version 3.0!",
        html=(
            "Applications on your computer can send whatever information they "
            "want to wherever they want. Most often they do that for good reason, "
            "at your explicit request.<br><br>"
            "<b>But sometimes they don't!</b>"
        ),
        icon_char="🔒",
        gradient_start="#C9DFF5",
        gradient_end="#F9C5A7",
    ),
    WhatsNewPage(
        title="Network Monitor",
        html=(
            "The <b>Network Monitor</b> is a powerful tool for viewing, analyzing "
            "and controlling your app's network activity on a per-process basis."
        ),
        bullets=[
            "The connection list shows successful and blocked connections for all running processes.",
            "The traffic diagram provides a detailed history of each process for in-depth traffic analysis.",
        ],
        icon_char="📡",
        gradient_start="#FFFFFF",
        gradient_end="#EAF3FB",
    ),
    WhatsNewPage(
        title="Smarter Filtering",
        html=(
            "New <b>domain-based rules</b> let you block or allow entire hostnames "
            "with a single click.  Rules sync across your devices automatically."
        ),
        bullets=[
            "One-click wildcard rules cover all subdomains instantly.",
            "Import & export your rule sets as a simple JSON file.",
        ],
        icon_char="🛡️",
        gradient_start="#E8F5E9",
        gradient_end="#FFF9C4",
    ),
    WhatsNewPage(
        title="Live Statistics",
        html=(
            "A redesigned <b>statistics panel</b> shows bandwidth, request counts, "
            "and latency broken down by process, domain, and protocol — all in "
            "real time."
        ),
        icon_char="📊",
        gradient_start="#F3E5F5",
        gradient_end="#FCE4EC",
    ),
]

app = QApplication([])
dlg = WhatsNewDialog(DEMO_PAGES, version="3.0")
THEMES.apply(dlg)
dlg.show()

app.exec_()
