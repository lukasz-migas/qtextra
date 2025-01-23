"""HTML viewer."""

import os
import typing as ty

from qtpy.QtCore import QStandardPaths
from qtpy.QtWidgets import QWidget

try:
    from qtpy.QtWebEngineWidgets import QWebEngineView  # type: ignore[attr-defined]

    QWebView = None
except ImportError:
    QWebEngineView = None
    try:
        from qtpy.QtNetwork import QNetworkDiskCache
        from qtpy.QtWebKitWidgets import QWebView  # type: ignore[no-redef]

    except ImportError:
        QWebView = None


def make_html_viewer(parent: QWidget) -> ty.Any:
    """Make viewier."""
    if QWebEngineView is not None:
        panel_help = QWebEngineView(parent)
    elif QWebView is not None:
        panel_help = QWebView(parent)
        manager = panel_help.page().networkAccessManager()
        cache = QNetworkDiskCache()
        cache_dir = os.path.join(
            QStandardPaths.writableLocation(QStandardPaths.StandardLocation.CacheLocation), "help", "help-view-cache"
        )
        cache.setCacheDirectory(cache_dir)
        manager.setCache(cache)
    else:
        panel_help = None
    return panel_help
