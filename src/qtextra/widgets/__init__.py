"""Widgets."""


if __name__ == "__main__":  # pragma: no cover
    import sys

    from qtextra.utils.dev import qframe
    from qtextra.widgets.qt_tutorial import _popover

    app, frame, ha = qframe()
    _popover(frame, frame)

    frame.show()
    frame.setMaximumHeight(400)
    sys.exit(app.exec_())
