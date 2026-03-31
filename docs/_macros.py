from __future__ import annotations

import os
import re
import sys
from contextlib import contextmanager
from enum import EnumMeta
from importlib import import_module
from pathlib import Path
from textwrap import dedent
from typing import TYPE_CHECKING

from jinja2 import pass_context
from qtpy.QtCore import QObject, Signal

if TYPE_CHECKING:
    from mkdocs_macros.plugin import MacrosPlugin

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
EXAMPLES = ROOT / "examples"
IMAGES = DOCS / "_auto_images"
IMAGES.mkdir(exist_ok=True, parents=True)
BUILD_HOME = DOCS / "_build_home"
BUILD_HOME.mkdir(exist_ok=True, parents=True)


def define_env(env: MacrosPlugin):
    @env.macro
    @pass_context
    def show_widget(context, width: int = 500) -> list[Path]:
        page = context["page"]
        dest = IMAGES / f"{_slugify(page.title)}.png"
        codeblocks = [block[6:].strip() for block in page.markdown.split("```") if block.startswith("python")]
        if codeblocks and _should_build_images():
            print("Building widget image:", dest)
            dest.unlink(missing_ok=True)
            _capture_source(dest, codeblocks[0], width=width)
            print("Grabbed widget image:", dest)
        return _image_markdown(page, dest, width=width, alt=page.title)

    @env.macro
    def include_example(path: str) -> str:
        src = _read_example(path)
        return f"```python\n{src.rstrip()}\n```\n"

    @env.macro
    @pass_context
    def show_example(context, path: str, width: int = 500) -> str:
        page = context["page"]
        example = _resolve_example(path)
        dest = IMAGES / f"{example.stem}.png"
        if _should_build_images():
            print("Building example image:", example)
            dest.unlink(missing_ok=True)
            _capture_source(dest, _read_example(example), width=width)
            print("Grabbed example image:", dest)
        return _image_markdown(page, dest, width=width, alt=example.stem.replace("_", " "))

    @env.macro
    def show_members(cls: str):
        # import class
        module, name = cls.rsplit(".", 1)
        _cls = getattr(import_module(module), name)

        first_q = next(
            (b.__name__ for b in _cls.__mro__ if issubclass(b, QObject) and ".Qt" in b.__module__),
            None,
        )

        inherited_members = set()
        for base in _cls.__mro__:
            if issubclass(base, QObject) and ".Qt" in base.__module__:
                inherited_members.update({k for k in dir(base) if not k.startswith("_")})

        new_signals = {k for k, v in vars(_cls).items() if not k.startswith("_") and isinstance(v, Signal)}

        self_members = {k for k in dir(_cls) if not k.startswith("_") and k not in inherited_members | new_signals}

        enums = []
        for m in list(self_members):
            if isinstance(getattr(_cls, m), EnumMeta):
                self_members.remove(m)
                enums.append(m)

        out = ""
        if first_q:
            url = f"https://doc.qt.io/qt-6/{first_q.lower()}.html"
            out += f"## Qt Class\n\n<a href='{url}'>`{first_q}`</a>\n\n"

        out += ""

        if new_signals:
            out += "## Signals\n\n"
            for sig in new_signals:
                out += f"### `{sig}`\n\n"

        if enums:
            out += "## Enums\n\n"
            for e in enums:
                out += f"### `{_cls.__name__}.{e}`\n\n"
                for m in getattr(_cls, e):
                    out += f"- `{m.name}`\n\n"

        if self_members:
            out += dedent(
                f"""
            ## Methods

            ::: {cls}
                options:
                  heading_level: 3
                  show_source: False
                  show_inherited_members: false
                  show_signature_annotations: True
                  members: {sorted(self_members)}
                  docstring_style: numpy
                  show_bases: False
                  show_root_toc_entry: False
                  show_root_heading: False
            """,
            )

        return out


def _should_build_images() -> bool:
    return any(arg in {"build", "serve"} for arg in sys.argv)


def _slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _resolve_example(path: str | Path) -> Path:
    example = Path(path)
    if not example.is_absolute():
        if example.parts and example.parts[0] == "examples":
            example = ROOT / example
        else:
            example = EXAMPLES / example
    example = example.resolve()
    if EXAMPLES not in example.parents:
        raise ValueError(f"Example path must live under {EXAMPLES}: {path}")
    return example


def _read_example(path: str | Path) -> str:
    example = _resolve_example(path)
    return example.read_text(encoding="utf-8")


def _image_markdown(page, dest: Path, width: int, alt: str) -> str:
    page_dir = Path(page.file.src_uri).parent
    relative = Path(os.path.relpath(dest, DOCS / page_dir))
    return f"![{alt}]({relative.as_posix()}){{ loading=lazy; width={width} }}\n\n"


def _prepare_source(src: str) -> str:
    src = src.replace("QApplication([])", "QApplication.instance() or QApplication([])")
    src = re.sub(r"(?<!\w)(\w+)\.exec_\(\)", r"\1.processEvents()", src)
    src = re.sub(r"(?<!\w)(\w+)\.exec\(\)", r"\1.processEvents()", src)
    return src


def _capture_source(dest: str | Path, src: str, width: int) -> None:
    namespace = {"__name__": "__main__", "__file__": str(dest)}
    with _build_environment():
        exec(_prepare_source(src), namespace)
        _grab(dest, width)


@contextmanager
def _build_environment():
    previous = os.environ.get("HOME")
    os.environ["HOME"] = str(BUILD_HOME)
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop("HOME", None)
        else:
            os.environ["HOME"] = previous


def _grab(dest: str | Path, width: int) -> list[Path]:
    """Grab the visible top-level widgets of the application."""
    from qtpy.QtGui import QColor, QImage, QPainter
    from qtpy.QtTest import QTest
    from qtpy.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        raise RuntimeError("No QApplication instance was created by the example.")

    app.processEvents()
    QTest.qWait(150)
    app.processEvents()

    widgets = [
        widget
        for widget in QApplication.topLevelWidgets()
        if widget.isVisible() and widget.width() > 0 and widget.height() > 0
    ]
    if not widgets:
        raise RuntimeError("No visible top-level widgets were available to grab.")

    images = []
    for widget in widgets:
        widget.activateWindow()
        widget.raise_()
        app.processEvents()
        QTest.qWait(100)
        pixmap = widget.grab()
        images.append(_normalize_capture(pixmap))

    padding = 16
    spacing = 20
    max_width = max(image.width() for image in images)
    total_height = sum(image.height() for image in images) + spacing * (len(images) - 1)

    background = app.palette().color(app.activeWindow().backgroundRole()) if app.activeWindow() else QColor("white")
    canvas = QImage(max_width + padding * 2, total_height + padding * 2, QImage.Format.Format_ARGB32)
    canvas.fill(background)

    painter = QPainter(canvas)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
    y = padding
    for image in images:
        x = padding + (max_width - image.width()) // 2
        painter.drawImage(x, y, image)
        y += image.height() + spacing
    painter.end()
    canvas.save(str(dest))

    for widget in widgets:
        widget.close()
        widget.deleteLater()
    app.processEvents()
    return [Path(dest)]


def _normalize_capture(pixmap: QPixmap) -> QImage:
    """Return a 1x QImage with the pixmap content expanded to pixel dimensions."""
    from qtpy.QtGui import QImage

    image = pixmap.toImage().convertToFormat(QImage.Format.Format_ARGB32)
    dpr = pixmap.devicePixelRatio()
    if dpr <= 1:
        return image
    image.setDevicePixelRatio(1.0)
    return image
