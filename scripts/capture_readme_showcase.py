# ruff: noqa: INP001
"""Capture the README showcase example as a PNG."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from docs._macros import _capture_source  # noqa: E402

DEFAULT_SOURCE = ROOT / "examples" / "qt_readme_showcase.py"
DEFAULT_DEST = ROOT / "docs" / "assets" / "readme_showcase.png"


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        type=Path,
        default=DEFAULT_SOURCE,
        help=f"Example file to capture. Default: {DEFAULT_SOURCE.relative_to(ROOT)}",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_DEST,
        help=f"PNG output path. Default: {DEFAULT_DEST.relative_to(ROOT)}",
    )
    parser.add_argument(
        "--width",
        type=int,
        default=1100,
        help="Rendered image width in pixels.",
    )
    return parser.parse_args()


def main() -> int:
    """Capture the showcase example image."""
    args = parse_args()
    source = args.source if args.source.is_absolute() else ROOT / args.source
    output = args.output if args.output.is_absolute() else ROOT / args.output

    src = source.read_text(encoding="utf-8")
    output.parent.mkdir(parents=True, exist_ok=True)
    _capture_source(output, src, args.width)

    print(f"Captured {source.relative_to(ROOT)} -> {output.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
