"""Widget with indicators."""

import typing as ty

from loguru import logger
from qtpy.QtCore import Qt, QTimer, Slot
from qtpy.QtWidgets import (
    QAction,
    QButtonGroup,
    QHBoxLayout,
    QSizePolicy,
    QStackedLayout,
    QStackedWidget,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

import qtextra.helpers as hp
from qtextra.widgets.qt_image_button import QtToolbarPushButton


class QtAboutWidget(QWidget):
    """About widget."""

    def __init__(self, title: str, description: str, docs_link: str = None, parent=None):
        super().__init__(parent)

        self.title_label = hp.make_label(self, title, bold=True, wrap=True)
        self.description_label = hp.make_label(self, description, enable_url=True, wrap=True)
        self.docs_label = hp.make_label(self, docs_link if docs_link else "", enable_url=True, wrap=True)
        if docs_link is None:
            self.docs_label.setVisible(False)

        self._layout = QVBoxLayout(self)
        self._layout.addWidget(self.title_label)
        self._layout.addWidget(self.description_label, stretch=True, alignment=Qt.AlignTop | Qt.AlignLeft)
        self._layout.addWidget(self.docs_label)

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    @classmethod
    def make_widget(cls, title: str, description: str, docs: str, parent=None):
        """Make widget."""
        return QtAboutWidget(title, description, docs, parent=parent)


# class QtAboutPopup(QtTransparentPopup):
#     """About popup."""
#
#     def __init__(self, text: str, parent: ty.Optional[QWidget] = None):
#         super().__init__(parent=parent)
#         self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
#
#         self.label = hp.make_label(self, text)
#         layout = QVBoxLayout(self.frame)
#         layout.setContentsMargins(5, 5, 5, 5)
#         layout.addWidget(self.label)
#
#     def on_show(self, state: bool):
#         """Show popup."""
#         self.show() if state else self.hide()


class QtPanelWidget(QWidget):
    """Stacked panel widget."""

    def __init__(self, parent: QWidget = None, position: str = "left"):
        super().__init__(parent)

        self._about_stack = QWidget(self)
        self._about_stack.setMinimumWidth(0)
        self._about_stack.setMaximumWidth(0)
        self._about_layout = QStackedLayout()
        self._about_stack.setLayout(self._about_layout)
        self._about_stack.setVisible(False)

        self._stack = QStackedWidget(parent)
        self._buttons = QToolBar(self)

        spacer = hp.make_spacer_widget()
        self._spacer = self._buttons.addWidget(spacer)

        self._group = QButtonGroup(self)
        self._button_dict: ty.Dict[QtToolbarPushButton, QAction] = {}
        self._hidden_dict: ty.Dict[QtToolbarPushButton, QAction] = {}

        # Widget setup
        self._buttons.setOrientation(Qt.Vertical)
        self._group.setExclusive(True)
        self._group.buttonToggled.connect(self._toggle_widget)

        self._layout = QHBoxLayout()
        self._layout.addWidget(self._buttons)
        if position == "left":
            self._layout.addWidget(self._about_stack)
        else:
            self._layout.addWidget(self._about_stack)

        self._buttons.setContentsMargins(0, 0, 0, 0)
        self._about_stack.setContentsMargins(0, 0, 0, 0)
        self._stack.setContentsMargins(0, 0, 0, 0)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)

        self.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self._layout)

    @property
    def stack_widget(self):
        """Get stack widget."""
        return self._stack

    def add_widget(
        self, name: str, tooltip: ty.Optional[str] = None, widget: ty.Optional[QWidget] = None, location: str = "top"
    ):
        """Add widget to the stack.

        Parameters
        ----------
        name : str
            name of the object that will be used to select the icon
        tooltip : Optional[str]
            text that will be used to generate the tooltip information - it will be overwritten if the `widget`
            implements the `_make_html_description` method which auto-generates tooltip information in html-rich format
        widget : Optional[QWidget]
            widget that will be inserted into the stack
        location : str
            location of the button - allowed values include `top` and `bottom`. Typically, buttons that go to the
            `bottom` will be simple click-buttons without widgets associated with them.
        """
        assert location in ["top", "bottom"], "Incorrect location provided - use `top` or `bottom`"
        button: QtToolbarPushButton = hp.make_tool_btn(
            self,
            name,
            checkable=widget is not None,
            flat=True,
            medium=True,
            # icon_kwargs=dict(color_active=THEMES.get_hex_color("success")),
        )

        # create custom tooltip if it's possible
        if hasattr(widget, "_make_html_description"):
            tooltip = widget._make_html_description()

        # about_widget = None
        # if hasattr(widget, "_make_html_metadata"):
        #     about_widget = QtAboutWidget.make_widget(*widget._make_html_metadata(), parent=self._about_stack)
        # elif hasattr(widget, "_make_html_description"):
        #     tooltip = widget._make_html_description()
        button.setToolTip(tooltip)
        button._widget = widget
        if widget:
            widget._button = button

        # about_widget = QtAboutPopup("TEST MESSAGE", button)
        # button._about = about_widget
        # button.evt_hover.connect(about_widget.on_show)

        # if about_widget:
        #     button._about_widget = about_widget
        #     self._about_layout.addWidget(about_widget)

        if hasattr(widget, "evt_indicate"):
            widget.evt_indicate.connect(button.set_indicator)
        if hasattr(widget, "evt_indicate_about"):
            widget.evt_indicate_about.connect(button.set_indicator)

        # get action button
        action = self._add_before(button) if location == "top" else self._add_after(button)
        self._button_dict[button] = action
        self._group.addButton(button)
        self._buttons.setVisible(True)
        if widget:
            widget._toggle = button
            self._stack.addWidget(widget)
            if self._stack.count() == 1:
                self._toggle_widget(button, True)
        return button

    def _add_before(self, button) -> QAction:
        """Add button after."""
        return self._buttons.insertWidget(self._spacer, button)

    def _add_after(self, button) -> QAction:
        return self._buttons.addWidget(button)

    def _show_another(self, button: QtToolbarPushButton):
        """Show another widget if current button is disabled or hidden."""
        for btn in self._button_dict:
            if btn != button:
                btn.setChecked(True)
                break

    def _toggle_widget(self, button: QtToolbarPushButton, value: bool):
        """Toggle widget and show appropriate widget."""
        if button in self._hidden_dict:
            self._show_another(button)
            return

        for btn in self._button_dict:
            if btn != button:
                with hp.qt_signals_blocked(btn):
                    btn.setChecked(False)

        button.setChecked(value)
        button.repaint()
        button.set_indicator("")
        widget = button._widget
        if value and widget:
            self._stack.setCurrentWidget(widget)
        if hasattr(button, "_about_widget") and button._about_widget:
            self._about_layout.setCurrentWidget(button._about_widget)
        self._stack.setVisible(value)

        # This is a bit of a hack but it's required to force-update vispy canvas after changing to view the panel
        if value and hasattr(widget, "_update_after_activate"):
            timer = QTimer(self)
            timer.singleShot(50, widget._update_after_activate)

    def enable_widget(self, button: QtToolbarPushButton):
        """Enable widget."""
        if button in self._hidden_dict:
            action = self._hidden_dict.pop(button, None)
            action.setVisible(True)

    def disable_widget(self, button: QtToolbarPushButton):
        """Disable widget."""
        if button in self._hidden_dict:
            logger.debug("Button is already hidden")
            return
        action = self._button_dict[button]
        self._hidden_dict[button] = action
        action.setVisible(False)

    def add_home_button(self):
        """Add home button."""
        button = self.add_widget("menu", "Show/hide information about the widgets.")
        button.evt_click.connect(self.show_about_stack)

    def show_about_stack(self, _):
        """Show about stack."""
        if self._about_stack.maximumWidth() == 0:
            start, end = 0, 250
        else:
            start, end = 250, 0
        hp.expand_animation(self._about_stack, start, end)


class QtPanelToolbar(QToolBar):
    """Toolbar."""

    def __init__(self, parent=None, position: str = "left"):
        super().__init__(parent=parent)

        self._widget = QtPanelWidget(self, position=position)

        self.setWindowTitle("Toolbar")
        self.setMovable(False)
        self.setAllowedAreas(Qt.LeftToolBarArea | Qt.RightToolBarArea)
        self.setObjectName(position)
        self.addWidget(self._widget)
        self.setContentsMargins(0, 0, 0, 0)

    @property
    def stack_widget(self):
        """Get instance of the stack widget."""
        return self._widget._stack

    # noinspection PyMissingOrEmptyDocstring
    def add_widget(self, name, tooltip: str = None, widget: QWidget = None, location="top") -> QtToolbarPushButton:
        return self._widget.add_widget(name, tooltip, widget, location=location)

    add_widget.__doc__ = QtPanelWidget.__doc__

    def set_disabled(self, button: QtToolbarPushButton, disable: bool):
        """Set widget as disabled."""
        if disable:
            self.disable_widget(button)
        else:
            self.enable_widget(button)

    def enable_widget(self, button: QtToolbarPushButton):
        """Enable widget."""
        self._widget.enable_widget(button)

    def disable_widget(self, button: QtToolbarPushButton):
        """Disable widget."""
        self._widget.disable_widget(button)

    @Slot()
    def deactivate_all(self):
        """Deactivate all indicators."""
        for btn in self._widget._button_dict:
            btn.set_indicator("")
            btn.repaint()


if __name__ == "__main__":  # pragma: no cover

    def _main():
        import sys
        from random import choice

        from qtextra.config import THEMES
        from qtextra.helpers import make_btn
        from qtextra.utils.dev import qmain
        from qtextra.widgets.qt_dialog import QtTab

        def _add_button():
            name = choice(["help", "filter", "open", "edit", "mask"])
            pos = choice(["top", "bottom"])
            tooltip = "<p style='white-space:pre'><h1>This is a much longer line than the first</h1></p>"
            # """<p style''white-space:pre'><h2><b>MyList</b></h2></p>"""
            button = toolbar.add_widget(name, tooltip, QWidget() if pos == "top" else None, pos)
            button.set_indicator(choice(["warning", "", "success", "active"]))

        def _add_widget():
            class Test(QtTab):
                _description = {
                    "title": choice(
                        ["dimensionality reduction", "machine learning", "spatial", "spectral", "highlights"]
                    ),
                    "description": "ABOUT THE PANEL",
                }

                def make_panel(self):
                    """Panel."""
                    return QHBoxLayout()

            panel = Test(frame)
            name = choice(["help", "filter", "open", "edit", "mask"])
            toolbar.add_widget(name, widget=panel)

        def _toggle_theme():
            THEMES.theme = choice(THEMES.available_themes())
            THEMES.set_theme_stylesheet(frame)

        def _disable_btn():
            button = choice(list(toolbar._widget._button_dict.keys()))
            toolbar._widget.disable_widget(button)

        def _enable_btn():
            button = choice(list(toolbar._widget._hidden_dict.keys()))
            toolbar._widget.enable_widget(button)

        app, frame, ha = qmain(False)
        frame.setMinimumSize(600, 600)

        toolbar = QtPanelToolbar(frame)
        frame.addToolBar(Qt.LeftToolBarArea, toolbar)

        btn2 = make_btn(frame, "Click me to add widget")
        btn2.clicked.connect(_add_button)
        ha.addWidget(btn2)

        btn2 = make_btn(frame, "Click me to add panel")
        btn2.clicked.connect(_add_widget)
        ha.addWidget(btn2)

        btn2 = make_btn(frame, "Click me to toggle theme")
        btn2.clicked.connect(_toggle_theme)
        ha.addWidget(btn2)

        btn2 = make_btn(frame, "Enable button")
        btn2.clicked.connect(_enable_btn)
        ha.addWidget(btn2)

        btn2 = make_btn(frame, "Disable button")
        btn2.clicked.connect(_disable_btn)
        ha.addWidget(btn2)

        frame.show()
        sys.exit(app.exec_())

    _main()
