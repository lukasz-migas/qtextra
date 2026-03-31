# qtextra

`qtextra` provides higher-level widgets, dialogs, and helpers for Qt
applications built with PyQt or PySide through `qtpy`.

The library focuses on application-facing components that are either missing
from the standard Qt bindings or awkward to assemble repeatedly in product
code. It also ships optional styling assets so the widgets are easier to adopt
consistently across a larger UI.

## Highlights

- Reusable widgets for input, progress, status, and selection flows
- Dialog helpers for confirmations, console output, changelogs, and more
- Theme-aware icons and stylesheet assets
- A live theme editor for tuning palettes, font sizes, and console styles
- Examples and targeted widget docs for common integration patterns

Components are tested on:

- macOS, Windows & Linux
- Python 3.10 and above
- PyQt5 (5.11 and above) & PyQt6
- PySide2 (5.11 and above) & PySide6

The project has some overlap with [superqt](https://github.com/pyapp-kit/superqt),
but `qtextra` is more opinionated about application ergonomics and bundled
styles.

## Installation

```bash
pip install qtextra
```

```bash
conda install -c conda-forge qtextra
```

## Usage

Start with the [Widgets](./widgets/index.md) and [Dialogs](./dialogs/index.md)
pages, then browse the runnable examples in [`examples/`](../examples).

The widget pages now pull code directly from those example scripts and include
generated screenshots so the docs stay aligned with the runnable examples.

## Utilities

- [Mixins](./mixins.md): reusable behavior blocks for dialogs and widgets
- [Automatic widget generation](./auto.md): schema-driven helpers in
  `qtextra.auto` for building forms and synchronizing values
