"""Widget with indicators."""

from __future__ import annotations

import typing as ty
from functools import partial

from loguru import logger
from qtpy.QtCore import Qt, Slot  # type: ignore[attr-defined]
from qtpy.QtWidgets import (  # type: ignore[attr-defined]
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
from qtextra.utils.utilities import connect
from qtextra.widgets.qt_button_icon import QtToolbarPushButton


class QtAboutWidget(QWidget):
    """About widget."""

    def __init__(self, title: str, description: str, docs_link: str | None = None, parent: QWidget | None = None):
        super().__init__(parent)

        self.title_label = hp.make_label(self, title, bold=True, wrap=True)
        self.description_label = hp.make_label(self, description, enable_url=True, wrap=True)
        self.docs_label = hp.make_label(self, docs_link if docs_link else "", enable_url=True, wrap=True)
        if docs_link is None:
            self.docs_label.setVisible(False)

        self._layout = QVBoxLayout(self)
        self._layout.addWidget(self.title_label)
        self._layout.addWidget(
            self.description_label, stretch=True, alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft
        )
        self._layout.addWidget(self.docs_label)

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    @classmethod
    def make_widget(cls, title: str, description: str, docs: str, parent: QWidget | None = None) -> QtAboutWidget:
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

    def __init__(self, parent: QWidget | None = None, position: str = "left"):
        super().__init__(parent)

        self._about_stack = QWidget(self)
        self._about_stack.setMinimumWidth(0)
        self._about_stack.setMaximumWidth(0)
        self._about_layout = QStackedLayout()
        self._about_stack.setLayout(self._about_layout)
        self._about_stack.setVisible(False)

        self._stack = QStackedWidget(parent)
        self._stack.setContentsMargins(0, 0, 0, 0)

        self._buttons = QToolBar(self)
        self._buttons.setContentsMargins(0, 0, 0, 0)

        spacer = hp.make_spacer_widget()
        self._spacer = self._buttons.addWidget(spacer)

        self._group = QButtonGroup(self)
        self._button_dict: ty.Dict[QtToolbarPushButton, QAction] = {}
        self._hidden_dict: ty.Dict[QtToolbarPushButton, QAction] = {}

        # Widget setup
        self._buttons.setOrientation(Qt.Orientation.Vertical)
        self._group.setExclusive(True)
        self._group.buttonToggled.connect(self._toggle_widget)

        self._layout = QHBoxLayout()
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)
        self._layout.addWidget(self._buttons)
        if position == "left":
            self._layout.addWidget(self._about_stack)
        else:
            self._layout.addWidget(self._about_stack)

        self._about_stack.setContentsMargins(0, 0, 0, 0)

        self.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self._layout)

    @property
    def stack_widget(self) -> QStackedWidget:
        """Get stack widget."""
        return self._stack

    def get_widget(self, name: str) -> QtToolbarPushButton | None:
        """Get widget."""
        for button in self._button_dict:
            if button.objectName() == name:
                return button
        return None

    def get_index(self, button: QtToolbarPushButton) -> int:
        """Get index."""
        for i, btn in enumerate(self._button_dict):
            if btn == button:
                return i
        return -1

    def widget_iter(self) -> ty.Iterator[QtToolbarPushButton]:
        """Iterate over widgets."""
        yield from self._button_dict

    def add_widget(
        self,
        name: str,
        tooltip: str | None = None,
        widget: QWidget | None = None,
        location: str = "top",
        func: ty.Callable | None = None,
    ) -> QtToolbarPushButton:
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
        func : Optional[Callable]
            function that will be connected to the button click event
        """
        assert location in ["top", "bottom"], "Incorrect location provided - use `top` or `bottom`"
        if self.get_widget(name):
            logger.warning(f"Button with name '{name}' already exists")

        button: QtToolbarPushButton = hp.make_toolbar_btn(
            self,
            name,
            checkable=widget is not None,
            large=True,
            # icon_kwargs=dict(color_active=THEMES.get_hex_color("success")),
        )
        button.setObjectName(name)
        if tooltip:
            button.setToolTip(tooltip)

        # get action button
        self._button_dict[button] = self._add_before(button) if location == "top" else self._add_after(button)
        self._group.addButton(button)
        if widget:
            self.connect_widget(name, widget, tooltip)
        elif func:
            button.evt_click.connect(func)
        return button

    def connect_widget(self, name: str, widget: QWidget, tooltip: str | None = None) -> None:
        """Connect widget."""
        button = self.get_widget(name)
        if not button:
            logger.warning(f"Button with name '{name}' not found")
            return
        button.setCheckable(True)
        index = self.get_index(button)

        # create custom tooltip if it's possible
        if hasattr(widget, "_make_html_description"):
            tooltip = widget._make_html_description()  # type: ignore[union-attr]

        # about_widget = None
        # if hasattr(widget, "_make_html_metadata"):
        #     about_widget = QtAboutWidget.make_widget(*widget._make_html_metadata(), parent=self._about_stack)
        # elif hasattr(widget, "_make_html_description"):
        #     tooltip = widget._make_html_description()
        if tooltip:
            button.setToolTip(tooltip)
        button.panel_widget = widget
        if hasattr(widget, "toggle_button"):
            widget.toggle_button = button
        if hasattr(widget, "evt_indicate"):
            connect(widget.evt_indicate, button.set_indicator)
        if hasattr(widget, "evt_indicate_about"):
            connect(widget.evt_indicate_about, button.set_indicator)
        self._stack.insertWidget(index, widget)
        if self._stack.count() == 1:
            self._toggle_widget(button, True)
        button.evt_click.connect(partial(self._toggle_widget, button, True))

    def _add_before(self, button: QtToolbarPushButton) -> QAction:
        """Add button after."""
        return self._buttons.insertWidget(self._spacer, button)  # type: ignore[return-value]

    def _add_after(self, button: QtToolbarPushButton) -> QAction:
        return self._buttons.addWidget(button)  # type: ignore[return-value]

    def add_separator_before(self, button: QtToolbarPushButton) -> None:
        """Add separator before button."""
        self._buttons.insertSeparator(button)

    def add_separator_after(self, button: QtToolbarPushButton) -> None:
        """Add separator."""
        self._buttons.addSeparator()

    def _show_another(self, button: QtToolbarPushButton) -> None:
        """Show another widget if current button is disabled or hidden."""
        for btn in self._button_dict:
            if btn != button:
                btn.setChecked(True)
                break

    def _toggle_widget(self, button: QtToolbarPushButton, value: bool) -> None:
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

        widget = button.panel_widget
        if value and widget:
            self._stack.setCurrentWidget(widget)
        if hasattr(button, "about_widget") and button.about_widget:
            self._about_layout.setCurrentWidget(button.about_widget)
        self._stack.setVisible(value)

        # This is a bit of a hack but it's required to force-update vispy canvas after changing to view the panel
        if value and widget and hasattr(widget, "update_after_activation"):
            hp.call_later(self, widget.update_after_activation, 50)

    def enable_widget(self, button: QtToolbarPushButton) -> None:
        """Enable widget."""
        if button in self._hidden_dict:
            action = self._hidden_dict.pop(button, None)
            if action:
                action.setVisible(True)

    def disable_widget(self, button: QtToolbarPushButton) -> None:
        """Disable widget."""
        if button in self._hidden_dict:
            logger.debug("Button is already hidden")
            return
        action = self._button_dict[button]
        self._hidden_dict[button] = action
        action.setVisible(False)

    def add_home_button(self) -> None:
        """Add home button."""
        button = self.add_widget("menu", "Show/hide information about the widgets.")
        button.evt_click.connect(self.show_about_stack)

    def show_about_stack(self, _: ty.Any) -> None:
        """Show about stack."""
        if self._about_stack.maximumWidth() == 0:
            start, end = 0, 250
        else:
            start, end = 250, 0
        hp.expand_animation(self._about_stack, start, end)


class QtPanelToolbar(QToolBar):
    """Toolbar."""

    def __init__(self, parent: QWidget | None = None, position: str = "left"):
        super().__init__(parent=parent)

        self._widget = QtPanelWidget(self, position=position)
        # Get methods from the internal widget
        self.widget_iter = self._widget.widget_iter
        self.add_widget = self._widget.add_widget
        self.add_separator_after = self._widget.add_separator_after
        self.add_separator_before = self._widget.add_separator_before
        self.connect_widget = self._widget.connect_widget
        self.enable_widget = self._widget.enable_widget
        self.disable_widget = self._widget.disable_widget
        self.get_widget = self._widget.get_widget
        self.get_index = self._widget.get_index

        self.setWindowTitle("Toolbar")
        self.setMovable(False)
        self.setAllowedAreas(Qt.ToolBarArea.LeftToolBarArea | Qt.ToolBarArea.RightToolBarArea)
        self.setObjectName(position)
        self.addWidget(self._widget)
        self.setContentsMargins(0, 0, 0, 0)

    @property
    def stack_widget(self) -> QStackedWidget:
        """Get an instance of the stack widget."""
        return self._widget._stack

    def set_disabled(self, button: QtToolbarPushButton, disable: bool) -> None:
        """Set widget as disabled."""
        if disable:
            self.disable_widget(button)
        else:
            self.enable_widget(button)

    @Slot()  # type: ignore[misc]
    def deactivate_all(self) -> None:
        """Deactivate all indicators."""
        for btn in self._widget._button_dict:
            btn.set_indicator("")
            btn.repaint()


if __name__ == "__main__":  # pragma: no cover fmt: off

    def _main():  # type: ignore[no-untyped-def]
        import sys
        from random import choice

        from qtextra.assets import QTA_MAPPING
        from qtextra.helpers import make_btn
        from qtextra.utils.dev import qmain, theme_toggle_btn
        from qtextra.widgets.qt_dialog import QtTab

        def _add_button() -> None:
            name = choice(list(QTA_MAPPING.keys()))
            indicator_type = choice(["warning", "", "success", "active"])
            pos = choice(["top", "bottom"])
            tooltip = "<p style='white-space:pre'><h1>This is a much longer line than the first</h1></p>"
            # """<p style''white-space:pre'><h2><b>MyList</b></h2></p>"""
            button = toolbar.add_widget(name, tooltip, QWidget() if pos == "top" else None, pos)
            button.set_indicator(indicator_type)

        def _add_widget() -> None:
            class Test(QtTab):
                _description: ty.ClassVar[dict] = {
                    "title": choice(
                        ["dimensionality reduction", "machine learning", "spatial", "spectral", "highlights"]
                    ),
                    "description": "ABOUT THE PANEL",
                }

                def make_panel(self):
                    """Panel."""
                    return QHBoxLayout()

            panel = Test(frame)
            name = choice(list(QTA_MAPPING.keys()))
            toolbar.add_widget(name, widget=panel)

        def _disable_btn():
            button = choice(list(toolbar._widget._button_dict.keys()))
            toolbar._widget.disable_widget(button)

        def _enable_btn():
            button = choice(list(toolbar._widget._hidden_dict.keys()))
            toolbar._widget.enable_widget(button)

        app, frame, ha = qmain(False)
        frame.setMinimumSize(600, 600)

        toolbar = QtPanelToolbar(frame)
        frame.addToolBar(Qt.ToolBarArea.LeftToolBarArea, toolbar)

        btn2 = make_btn(frame, "Click me to add widget")
        btn2.clicked.connect(_add_button)
        ha.addWidget(btn2)

        btn2 = make_btn(frame, "Click me to add panel")
        btn2.clicked.connect(_add_widget)
        ha.addWidget(btn2)

        ha.addWidget(theme_toggle_btn(frame))

        btn2 = make_btn(frame, "Enable button")
        btn2.clicked.connect(_enable_btn)
        ha.addWidget(btn2)

        btn2 = make_btn(frame, "Disable button")
        btn2.clicked.connect(_disable_btn)
        ha.addWidget(btn2)

        frame.show()
        sys.exit(app.exec_())

    _main()
