# ruff: noqa: INP001
"""Capture screenshots for dialog examples referenced by docs/dialogs pages."""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS_DIALOGS = ROOT / "docs" / "dialogs"
OUTPUT_DIR = ROOT / "docs" / "assets"
BUILD_HOME = ROOT / "docs" / "_build_home"
SOURCE_PATTERN = re.compile(r"Source:\s*`examples/([^`]+\.py)`")


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--docs-dir",
        type=Path,
        default=DOCS_DIALOGS,
        help=f"Directory containing dialog markdown pages. Default: {DOCS_DIALOGS.relative_to(ROOT)}",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=OUTPUT_DIR,
        help=f"Directory where screenshots will be written. Default: {OUTPUT_DIR.relative_to(ROOT)}",
    )
    parser.add_argument(
        "--suffix",
        default=".jpg",
        help="Image suffix for captured screenshots. Default: .jpg",
    )
    return parser.parse_args()


def find_dialog_examples(docs_dir: Path) -> list[str]:
    """Return example filenames referenced by dialog docs pages."""
    examples: list[str] = []
    for page in sorted(docs_dir.glob("*.md")):
        if page.name == "index.md":
            continue
        text = page.read_text(encoding="utf-8")
        match = SOURCE_PATTERN.search(text)
        if match:
            examples.append(match.group(1))
    return examples


def capture_example(example_name: str, output_path: Path) -> None:
    """Run the docs capture helper for a single example in an isolated process."""
    env = os.environ.copy()
    env.setdefault("QT_QPA_PLATFORM", "offscreen")
    env["HOME"] = str(BUILD_HOME)
    env["XDG_CACHE_HOME"] = str(BUILD_HOME / ".cache")
    env["MPLCONFIGDIR"] = str(BUILD_HOME / ".matplotlib")

    code = """
import os
from pathlib import Path
from docs._macros import _capture_source

root = Path.cwd()
example = root / "examples" / os.environ["EXAMPLE_NAME"]
dest = Path(os.environ["OUTPUT_PATH"])
dest.parent.mkdir(parents=True, exist_ok=True)
_capture_source(dest, example.read_text(encoding="utf-8"), 760)
print(dest)
"""
    subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(ROOT),
        env={**env, "EXAMPLE_NAME": example_name, "OUTPUT_PATH": str(output_path)},
        check=True,
        text=True,
    )


def main() -> int:
    """Capture all dialog screenshots referenced by docs pages."""
    args = parse_args()
    docs_dir = args.docs_dir if args.docs_dir.is_absolute() else ROOT / args.docs_dir
    output_dir = args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir
    suffix = args.suffix if args.suffix.startswith(".") else f".{args.suffix}"

    BUILD_HOME.mkdir(parents=True, exist_ok=True)
    examples = find_dialog_examples(docs_dir)
    if not examples:
        print(f"No dialog examples found in {docs_dir}")
        return 0

    for example_name in examples:
        output_path = output_dir / f"{Path(example_name).stem}{suffix}"
        capture_example(example_name, output_path)
        print(f"Captured examples/{example_name} -> {output_path.relative_to(ROOT)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
