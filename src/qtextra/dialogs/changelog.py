"""Changelog dialog."""

from __future__ import annotations

import typing as ty
from contextlib import suppress
from pathlib import Path
from urllib import request

from koyo.compression import unzip_directory
from koyo.typing import PathLike
from qtpy.QtWidgets import QFormLayout, QLabel, QProgressBar, QPushButton, QTextEdit, QWidget
from superqt.utils import create_worker, ensure_main_thread, qthrottled
from tqdm import tqdm

import qtextra.helpers as hp
from qtextra.config import THEMES
from qtextra.widgets.qt_code_widget import Codelighter
from qtextra.widgets.qt_dialog import QtFramelessTool


class ChangelogDialog(QtFramelessTool):
    """Changelog."""

    HIDE_WHEN_CLOSE = False

    def __init__(
        self,
        parent: ty.Optional[QWidget],
        text: str,
        language: str = "markdown",
        download_url: ty.Optional[str] = None,
        download_info: ty.Optional[str] = None,
        path_to_file: ty.Optional[PathLike] = None,
    ) -> None:
        self.text = text
        self.language = language
        self.download_url = download_url
        self.download_info = download_info or ""
        self.path_to_file = path_to_file
        self.path_to_out = get_path(path_to_file) if path_to_file else None

        super().__init__(parent)
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)

    # noinspection PyAttributeOutsideInit
    def make_panel(self) -> QFormLayout:
        """Make panel."""
        self.text_edit = QTextEdit()
        self._highlight = Codelighter(self.text_edit.document(), THEMES.syntax_style, self.language)
        self.text_edit.setText(self.text)
        self.text_edit.setReadOnly(True)
        self.download_label = hp.make_label(self, self.download_info, enable_url=True)
        self.download_btn = QPushButton("Download")
        self.download_btn.clicked.connect(self.on_download)
        self.progress_bar = QProgressBar()
        self.progress_bar.hide()
        self.progress_label = hp.make_label(self, enable_url=True)
        self.progress_label.hide()
        if self.download_url is None:
            self.download_label.hide()
            self.download_btn.hide()
        if self.path_to_out is not None and self.path_to_out.exists():
            self.progress_label.setText(
                f"<a href='{self.path_to_out.as_uri()}'>Open {self.path_to_out} - it's been previously downloaded.</a>"
            )
            self.progress_label.show()
            self.download_btn.hide()

        layout = hp.make_form_layout(parent=self)
        layout.addRow(self._make_close_handle("Changelog")[1])
        layout.addRow(self.text_edit)
        layout.addRow(self.download_label)
        layout.addRow(self.download_btn)
        layout.addRow(self.progress_bar)
        layout.addRow(self.progress_label)
        layout.addRow(self.progress_label)
        return layout

    # @ensure_main_thread()
    def on_download(self, *_args: ty.Any) -> None:
        """Download."""
        if self.download_url is None:
            return

        pbar = tqdm(unit="B", unit_scale=True, unit_divisor=1024, desc="Downloading...", mininterval=1)
        reporthook = report_hook(self.progress_bar, self.progress_label, pbar)
        create_worker(
            download_file,
            self.download_url,
            # self.progress_bar,
            # self.progress_label,
            self.path_to_file,
            reporthook,
            pbar,
            _start_thread=True,
            _connect={
                "returned": self._on_download_finished,
                "yielded": self._on_download_yielded,
                "started": self._on_download_started,
            },
        )

    @ensure_main_thread()
    def _on_download_yielded(self, text: str) -> None:
        self.progress_label.setText(text)
        self.progress_label.show()

    @ensure_main_thread()
    def _on_download_started(self) -> None:
        """Download start."""
        self.progress_bar.show()
        self.progress_label.show()
        self.download_btn.hide()

    @ensure_main_thread()
    def _on_download_finished(self, res: tuple[tqdm, str]) -> None:
        """Download finished."""
        pbar, text = res
        pbar.close()
        self.progress_bar.hide()
        self.download_btn.hide()
        self.progress_label.setText(text)
        self.progress_label.show()


def get_path(path_to_file: PathLike) -> Path:
    """Get formatted path."""
    path_to_file = Path(path_to_file)
    if path_to_file.suffix == ".zip":
        return path_to_file.parent / path_to_file.stem
    return path_to_file


def report_hook(
    progress_bar: QProgressBar, label: QLabel, pbar: tqdm
) -> ty.Callable[[int, int, ty.Optional[int]], None]:
    """Download progress."""
    last_b = [0]

    @ensure_main_thread()
    @qthrottled(timeout=500)
    def update_to(b: int = 1, bsize: int = 1, tot_size: ty.Optional[int] = None) -> None:
        """Update progress.

        b  : int, optional
            Number of blocks transferred so far [default: 1].
        bsize  : int, optional
            Size of each block (in tqdm units) [default: 1].
        tot_size  : int, optional
            Total size (in tqdm units). If [default: None] remains unchanged.
        """
        with suppress(RuntimeError):
            if tot_size is not None:
                progress_bar.setMaximum(tot_size)
                progress_bar.setValue(0)
                pbar.total = tot_size
            pbar.update((b - last_b[0]) * bsize)
            progress_bar.setValue(pbar.n)
            text = f"{pbar.n / 1024**2:.2f} / {pbar.total / 1024**2:.2f} MB"
            label.setText(text)
        last_b[0] = b

    return update_to  # type: ignore[return-value]


def download_file(
    url: str, path_to_file: PathLike, reporthook: ty.Callable, pbar: tqdm
) -> ty.Generator[str, None, None] | tuple[tqdm, str]:
    """Download data."""
    path_to_file = Path(path_to_file)
    if not path_to_file.exists():
        # create report hook
        temp_file = path_to_file.parent / (path_to_file.name + ".temp")
        _, _ = request.urlretrieve(url, temp_file, reporthook=reporthook)
        temp_file.rename(path_to_file)
    if path_to_file.suffix == ".zip":
        yield "Unzipping..."
        path_to_out = get_path(path_to_file)
        unzip_directory(path_to_file, path_to_out, remove_archive=True)
        yield "Unzipped"
    else:
        path_to_out = path_to_file
    return pbar, f"<a href='{path_to_out.as_uri()}' style='color: blue;'>Open {path_to_out}</a>"
