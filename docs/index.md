# qtextra

A bunch of *extra* widgets and components for PyQt/PySide

Here, you will find a bunch of extra widgets and components that you can use in your PySide/PyQt (using qtpy) applications.
The goal is to provide a set of widgets that are not available in the standard PyQt/PySide libraries, or that are not easy to use.

Components are tested on:

- macOS, Windows & Linux
- Python 3.9 and above
- PyQt5 (5.11 and above) & PyQt6
- Pyside2 (5.11 and above) & PySide6


This repository is fairly similar in scope to [superqt](https://github.com/pyapp-kit/superqt) which aims to provide a number of useful 
widgets (in fact we use a couple of them in this library). The main difference is that we aimed to provide a more opinionated 
style (with stylesheets available in the [assets](src/qtextra/assets/stylesheets) directory) and focus on providing a wider
range of widgets.

## Installation

```bash
pip install qtextra
```

```bash
conda install -c conda-forge qtextra
```

## Usage

See the [Widgets](./widgets/index.md) and [Dialogs](./dialogs/index.md) pages for features offered by superqt.
