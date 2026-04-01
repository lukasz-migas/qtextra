# ruff: noqa: INP001,TRY004
"""Capture the README showcase tabs as a composite PNG."""

from __future__ import annotations

import argparse
import importlib.util
import math
import os
import sys
from pathlib import Path

import appdirs
from qtpy.QtCore import Qt
from qtpy.QtGui import QColor, QImage, QPainter, QPixmap
from qtpy.QtTest import QTest
from qtpy.QtWidgets import QApplication, QTabWidget, QWidget

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
BUILD_HOME = ROOT / "docs" / "_build_home"
BUILD_HOME.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("HOME", str(BUILD_HOME))
os.environ.setdefault("XDG_CACHE_HOME", str(BUILD_HOME / ".cache"))
os.environ.setdefault("MPLCONFIGDIR", str(BUILD_HOME / ".matplotlib"))


def _appdirs_path(kind: str, appname: str = "", *_args) -> str:
    """Return a repo-local appdirs path for napari/theme caches."""
    name = appname or "app"
    path = BUILD_HOME / kind / name
    path.mkdir(parents=True, exist_ok=True)
    return str(path)


appdirs.user_cache_dir = lambda appname="", *args: _appdirs_path("cache", appname, *args)
appdirs.user_config_dir = lambda appname="", *args: _appdirs_path("config", appname, *args)
appdirs.user_data_dir = lambda appname="", *args: _appdirs_path("data", appname, *args)
appdirs.user_state_dir = lambda appname="", *args: _appdirs_path("state", appname, *args)
appdirs.user_log_dir = lambda appname="", *args: _appdirs_path("log", appname, *args)


DEFAULT_SOURCE = ROOT / "examples" / "showcase.py"
DEFAULT_DEST = ROOT / "docs" / "assets" / "readme_showcase.jpg"


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        type=Path,
        default=DEFAULT_SOURCE,
        help=f"Showcase example file. Default: {DEFAULT_SOURCE.relative_to(ROOT)}",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_DEST,
        help=f"JPG output path. Default: {DEFAULT_DEST.relative_to(ROOT)}",
    )
    parser.add_argument(
        "--width",
        type=int,
        default=1500,
        help="Maximum composite image width in pixels.",
    )
    parser.add_argument(
        "--columns",
        type=int,
        default=2,
        help="Number of columns in the composite grid.",
    )
    parser.add_argument(
        "--suffix",
        default=".jpg",
        help="Image suffix for captured screenshots. Default: .jpg",
    )
    return parser.parse_args()


def _load_showcase_module(source: Path):
    spec = importlib.util.spec_from_file_location("qtextra_readme_showcase", source)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not import showcase module from {source}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _normalize_capture(pixmap: QPixmap) -> QImage:
    """Return a device-pixel-normalized image."""
    image = pixmap.toImage().convertToFormat(QImage.Format.Format_ARGB32)
    dpr = pixmap.devicePixelRatio()
    if dpr <= 1:
        return image
    image.setDevicePixelRatio(1.0)
    return image


def _capture_widget(widget: QWidget) -> QImage:
    """Capture a widget after processing the event queue."""
    app = QApplication.instance()
    if app is None:
        raise RuntimeError("QApplication instance is required")
    app.processEvents()
    QTest.qWait(120)
    app.processEvents()
    return _normalize_capture(widget.grab())


def _build_composite(images: list[QImage], width: int, columns: int, background: QColor) -> QImage:
    """Arrange captured images in a scaled grid."""
    padding = 18
    columns = max(1, columns)
    cell_width = max(1, (width - padding * (columns + 1)) // columns)

    scaled_images: list[QImage] = []
    row_heights: list[int] = []
    current_row_height = 0
    for index, image in enumerate(images):
        scaled = image.scaledToWidth(cell_width, Qt.TransformationMode.SmoothTransformation)
        scaled_images.append(scaled)
        current_row_height = max(current_row_height, scaled.height())
        if index % columns == columns - 1 or index == len(images) - 1:
            row_heights.append(current_row_height)
            current_row_height = 0

    rows = math.ceil(len(scaled_images) / columns)
    canvas_height = padding * (rows + 1) + sum(row_heights)
    canvas = QImage(width, canvas_height, QImage.Format.Format_ARGB32)
    canvas.fill(background)

    painter = QPainter(canvas)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

    y = padding
    image_index = 0
    for row in range(rows):
        x = padding
        row_height = row_heights[row]
        for _column in range(columns):
            if image_index >= len(scaled_images):
                break
            image = scaled_images[image_index]
            painter.drawImage(x, y, image)
            x += cell_width + padding
            image_index += 1
        y += row_height + padding

    painter.end()
    return canvas


def main() -> int:
    """Capture the showcase tabs into a composite image."""
    args = parse_args()
    source = args.source if args.source.is_absolute() else ROOT / args.source
    output = args.output if args.output.is_absolute() else ROOT / args.output
    output = output.with_suffix(args.suffix)

    module = _load_showcase_module(source)
    if not hasattr(module, "build_showcase"):
        raise RuntimeError(f"{source} must define build_showcase()")

    app = QApplication.instance() or QApplication([])
    window = module.build_showcase()
    window.show()
    app.processEvents()
    QTest.qWait(180)

    tabs = getattr(window, "_showcase_tabs", None)
    if not isinstance(tabs, QTabWidget):
        raise RuntimeError("Showcase window must expose a QTabWidget as _showcase_tabs")

    captures: list[QImage] = []
    for index in range(tabs.count()):
        tabs.setCurrentIndex(index)
        app.processEvents()
        QTest.qWait(120)
        captures.append(_capture_widget(window))

    background = app.palette().color(window.backgroundRole())
    composite = _build_composite(captures, width=args.width, columns=args.columns, background=background)

    output.parent.mkdir(parents=True, exist_ok=True)
    composite.save(str(output))

    for dialog in getattr(window, "_showcase_dialogs", []):
        dialog.close()
        dialog.deleteLater()
    window.close()
    window.deleteLater()
    app.processEvents()

    print(f"Captured {source.relative_to(ROOT)} -> {output.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
