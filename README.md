# qtextra

[![License](https://img.shields.io/pypi/l/qtextra.svg?color=green)](https://github.com/lukasz-migas/qtextra/raw/main/LICENSE)
[![PyPI](https://img.shields.io/pypi/v/qtextra.svg?color=green)](https://pypi.org/project/qtextra)
[![Python Version](https://img.shields.io/pypi/pyversions/qtextra.svg?color=green)](https://python.org)
[![Test](https://github.com/lukasz-migas/qtextra/actions/workflows/test_and_deploy.yml/badge.svg?branch=main)](https://github.com/lukasz-migas/qtextra/actions/workflows/test_and_deploy.yml)
[![codecov](https://codecov.io/gh/lukasz-migas/qtextra/branch/main/graph/badge.svg)](https://codecov.io/gh/lukasz-migas/qtextra)

### A bunch of *extra* widgets and components for PyQt/PySide

Here, you will find a bunch of extra widgets and components that you can use in your PySide/PyQt (using qtpy) applications.
The goal is to provide a set of widgets that are not available in the standard PyQt/PySide libraries, or that are not easy to use.

Components are tested on:

- macOS, Windows & Linux
- Python 3.9 and above
- PyQt5 (5.11 and above) & PyQt6
- Pyside2 (5.11 and above) & PySide6


This repository is fairly similar in scope to [superqt](https://github.com/pyapp-kit/superqt) which aims to provide a number of useful 
widgets (in fact, we use a couple of them in this library). The main difference is that we aim to provide a more opinionated 
style (with stylesheets available in the [assets](src/qtextra/assets/stylesheets) directory) and focus on providing a wider
range of widgets.

## Contributing

Contributions are always welcome. Please feel free to submit PRs with new features, bug fixes, or documentation improvements.

```bash
git clone https://github.com/lukasz-migas/qtextra.git

pip install -e .[dev]
```


## Release information

1. Test code and make sure it works.
2. Reinstall all dependencies and build app and test that it works.
3. Update git tag and push it.
4. Reinstall and build app.
5. Upload to Dropbox.
6. Update the latest.json file in Dropbox.
7. Create release with changelog on GitHub (autoims-docs).
