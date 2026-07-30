"""Panel toolbar widgets with toggle buttons and a linked stacked panel."""

from __future__ import annotations

import typing as ty
from functools import partial

from loguru import logger
from qtpy.QtCore import QEvent, QObject, Qt, QTimer, Slot  # type: ignore[attr-defined]
from qtpy.QtWidgets import (  # type: ignore[attr-defined]
    QAction,
    QButtonGroup,
    QHBoxLayout,
    QMenu,
    QSizePolicy,
    QStackedLayout,
    QStackedWidget,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

import qtextra.helpers as hp
from qtextra.widgets.qt_button_icon import QtLabelledToolbarPushButton, QtToolbarPushButton


class QtAboutWidget(QWidget):
    """About widget."""

    def __init__(self, title: str, description: str, docs_link: str | None = None, parent: QWidget | None = None):
        super().__init__(parent)

        self.title_label = hp.make_label(self, title, bold=True, wrap=True)
        self.description_label = hp.make_label(self, description, enable_url=True, wrap=True)
        self.docs_label = hp.make_label(self, docs_link or "", enable_url=True, wrap=True)
        if docs_link is None:
            self.docs_label.setVisible(False)

        self._layout = QVBoxLayout(self)
        self._layout.addWidget(self.title_label)
        self._layout.addWidget(
            self.description_label,
            stretch=True,
            alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft,
        )
        self._layout.addWidget(self.docs_label)

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    @classmethod
    def make_widget(cls, title: str, description: str, docs: str, parent: QWidget | None = None) -> QtAboutWidget:
        """Make widget."""
        return QtAboutWidget(title, description, docs, parent=parent)


class QtPanelWidget(QWidget):
    """A vertical toolbar paired with a stacked panel area.

    The toolbar manages a set of `QtToolbarPushButton` or
    `QtLabelledToolbarPushButton` instances and keeps them synchronized with
    the panel stack. Buttons can either trigger a callback directly or toggle
    a panel widget in the adjacent `QStackedWidget`.
    """

    def __init__(
        self,
        parent: QWidget | None = None,
        position: ty.Literal["left", "right"] = "left",
        label_hidden: bool = True,
        auto_hide: bool = True,
    ):
        if position not in {"left", "right"}:
            raise ValueError("`position` must be either 'left' or 'right'.")
        super().__init__(parent)
        self._label_hidden = label_hidden
        self._auto_hide = auto_hide
        self._updating_overflow = False
        self._overflow_timer = QTimer(self)
        self._overflow_timer.setSingleShot(True)
        self._overflow_timer.timeout.connect(self._run_scheduled_overflow_update)

        self._about_stack = QWidget(self)
        self._about_stack.setMinimumWidth(0)
        self._about_stack.setMaximumWidth(0)
        self._about_layout = QStackedLayout()
        self._about_stack.setLayout(self._about_layout)
        self._about_stack.setVisible(False)

        self._stack = QStackedWidget(self)
        self._stack.setContentsMargins(0, 0, 0, 0)

        self._buttons = QToolBar(self)
        self._buttons.setContentsMargins(0, 0, 0, 0)
        self._buttons.setOrientation(Qt.Orientation.Vertical)

        self._overflow_menu = QMenu(self)
        self._overflow_menu.aboutToShow.connect(self._sync_overflow_menu)
        self._overflow_button = hp.make_toolbar_btn(self, "more", tooltip="More toolbar actions", size_preset="large")
        self._overflow_button.clicked.connect(self._show_overflow_menu)
        self._overflow_button.setObjectName("toolbar_overflow")
        self._overflow_action = self._buttons.addWidget(self._overflow_button)
        self._overflow_action.setVisible(False)

        spacer = hp.make_spacer_widget()
        self._spacer = self._buttons.addWidget(spacer)

        self._group = QButtonGroup(self)
        self._button_dict: dict[QtToolbarPushButton | QtLabelledToolbarPushButton, QAction] = {}
        self._hidden_dict: dict[QtToolbarPushButton | QtLabelledToolbarPushButton, QAction] = {}
        self._top_buttons: list[QtToolbarPushButton | QtLabelledToolbarPushButton] = []
        self._overflow_hidden: set[QtToolbarPushButton | QtLabelledToolbarPushButton] = set()
        self._overflow_enabled: dict[QtToolbarPushButton | QtLabelledToolbarPushButton, bool] = {}
        self._overflow_menu_actions: dict[QtToolbarPushButton | QtLabelledToolbarPushButton, QAction] = {}
        self._overflow_labels: dict[QtToolbarPushButton | QtLabelledToolbarPushButton, str] = {}

        # Widget setup
        self._group.setExclusive(True)
        self._group.buttonToggled.connect(self._toggle_widget)

        self._layout = QHBoxLayout()
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)
        self._layout.addWidget(self._buttons)
        if position == "left":
            self._layout.addWidget(self._about_stack)
        else:
            self._layout.insertWidget(0, self._about_stack)

        self._about_stack.setContentsMargins(0, 0, 0, 0)

        self.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self._layout)
        self._buttons.installEventFilter(self)

    @property
    def auto_hide(self) -> bool:
        """Return whether top buttons automatically collapse into the overflow menu."""
        return self._auto_hide

    @auto_hide.setter
    def auto_hide(self, value: bool) -> None:
        self._auto_hide = value
        self._update_overflow()

    @property
    def label_hidden(self) -> bool:
        """Get label hidden state."""
        return self._label_hidden

    @label_hidden.setter
    def label_hidden(self, value: bool) -> None:
        self._label_hidden = value
        for button in self._button_dict:
            if hasattr(button, "label_hidden"):
                button.label_hidden = value
        self._sync_button_widths()
        self._update_overflow()

    @property
    def stack_widget(self) -> QStackedWidget:
        """Get stack widget."""
        return self._stack

    def get_widget(self, name: str) -> QtToolbarPushButton | QtLabelledToolbarPushButton | None:
        """Get widget."""
        for button in self._button_dict:
            if button.objectName() == name:
                return button
        return None

    def get_index(self, button: QtToolbarPushButton | QtLabelledToolbarPushButton) -> int:
        """Get index."""
        for i, btn in enumerate(self._button_dict):
            if btn == button:
                return i
        return -1

    def widget_iter(self) -> ty.Iterator[QtToolbarPushButton | QtLabelledToolbarPushButton]:
        """Iterate over widgets."""
        yield from self._button_dict

    def add_widget(
        self,
        name: str,
        tooltip: str = "",
        widget: QWidget | None = None,
        location: str = "top",
        title: str | None = None,
        elide: bool = True,
        func: ty.Callable | None = None,
    ) -> QtToolbarPushButton | QtLabelledToolbarPushButton:
        """Add a toolbar button and optionally bind it to a panel widget.

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
        title : str, optional
            Title to be given to the button.
        elide : bool, optional
            Whether labAelled toolbar buttons should elide their text to stay compact.
        func : Optional[Callable]
            function that will be connected to the button click event
        """
        if location not in {"top", "bottom"}:
            raise ValueError("Incorrect location provided - use `top` or `bottom`.")
        if self.get_widget(name):
            raise ValueError(f"Button with name '{name}' already exists.")

        button: QtToolbarPushButton | QtLabelledToolbarPushButton = hp.make_toolbar_btn(
            self,
            name,
            checkable=widget is not None,
            size_preset="large",
            title=title,
            elide=elide,
        )
        if hasattr(button, "label_hidden"):
            button.label_hidden = self._label_hidden
        button.setObjectName(name)
        button.setToolTip(tooltip)

        # get action button
        self._button_dict[button] = self._add_before(button) if location == "top" else self._add_after(button)
        if location == "top":
            self._top_buttons.append(button)
            self._add_overflow_menu_action(button, title or tooltip or name.replace("_", " ").title())
        if isinstance(button, QtLabelledToolbarPushButton):
            self._group.addButton(button.image_btn)
        else:
            self._group.addButton(button)
        self._sync_button_widths()
        if widget:
            self.connect_widget(name, widget, tooltip)
        elif func:
            button.evt_click.connect(func)
        self._update_overflow()
        return button

    def connect_widget(self, name: str, widget: QWidget, tooltip: str | None = None) -> None:
        """Bind a panel widget to an existing toolbar button."""
        button = self.get_widget(name)
        if not button:
            logger.warning(f"Button with name '{name}' not found")
            return
        button.setCheckable(True)
        index = self.get_index(button)

        # create a custom tooltip if it's possible
        if hasattr(widget, "_make_rich_tooltip") and hasattr(button, "setRichToolTip"):
            title, content = widget._make_rich_tooltip()
            button.setRichToolTip(title, content)
        else:
            if not tooltip and hasattr(widget, "_make_html_description"):
                tooltip = widget._make_html_description()
            button.setToolTip(tooltip or "")

        button.panel_widget = widget
        if hasattr(widget, "toggle_button"):
            widget.toggle_button = button
        if hasattr(widget, "evt_indicate"):
            hp.connect(widget.evt_indicate, button.set_indicator)
        if hasattr(widget, "evt_indicate_about"):
            hp.connect(widget.evt_indicate_about, button.set_indicator)
        self._stack.insertWidget(index, widget)
        if self._stack.count() == 1:
            self._toggle_widget(button, True)
        button.evt_click.connect(partial(self._toggle_widget_from_click, button))

    def _add_before(self, button: QtToolbarPushButton | QtLabelledToolbarPushButton) -> QAction:
        """Insert a top button immediately before the overflow control."""
        return self._buttons.insertWidget(self._overflow_action, button)  # type: ignore[return-value]

    def _add_after(self, button: QtToolbarPushButton | QtLabelledToolbarPushButton) -> QAction:
        """Append a toolbar button after the spacer."""
        return self._buttons.addWidget(button)  # type: ignore[return-value]

    def _add_overflow_menu_action(
        self,
        button: QtToolbarPushButton | QtLabelledToolbarPushButton,
        label: str,
    ) -> None:
        """Create the menu action representing a top toolbar button."""
        source = button.image_btn if isinstance(button, QtLabelledToolbarPushButton) else button
        action = QAction(source.icon(), label, self._overflow_menu)
        action.setVisible(False)
        action.triggered.connect(partial(self._activate_overflow_button, button))
        self._overflow_menu.addAction(action)
        self._overflow_menu_actions[button] = action
        self._overflow_labels[button] = label

    def _activate_overflow_button(
        self,
        button: QtToolbarPushButton | QtLabelledToolbarPushButton,
        _: bool = False,
    ) -> None:
        """Invoke a hidden button with the same signals as a pointer click."""
        source = button.image_btn if isinstance(button, QtLabelledToolbarPushButton) else button
        source.on_click()
        if source.isCheckable() and not source.isChecked():
            source.setChecked(True)
        self._sync_overflow_menu()

    def _show_overflow_menu(self) -> None:
        """Show the overflow menu."""
        hp.show_menu(self._overflow_menu)

    def _sync_overflow_menu(self) -> None:
        """Synchronize overflow menu actions with their toolbar buttons."""
        for button in self._top_buttons:
            source = button.image_btn if isinstance(button, QtLabelledToolbarPushButton) else button
            action = self._overflow_menu_actions[button]
            action.setText(self._overflow_labels[button])
            action.setIcon(source.icon())
            action.setCheckable(source.isCheckable())
            action.setChecked(source.isChecked())
            action.setEnabled(self._overflow_enabled.get(button, source.isEnabled()))
            action.setVisible(button in self._overflow_hidden and button not in self._hidden_dict)

    def _schedule_overflow_update(self) -> None:
        """Queue one overflow update after Qt finishes the current layout pass."""
        if not self._overflow_timer.isActive():
            self._overflow_timer.start(0)

    def _run_scheduled_overflow_update(self) -> None:
        """Run a previously queued overflow update."""
        self._update_overflow()

    def _update_overflow(self) -> None:
        """Collapse trailing top buttons until the toolbar fits its height."""
        if self._updating_overflow:
            return

        self._updating_overflow = True
        try:
            self._overflow_hidden.clear()
            self._overflow_enabled.clear()
            self._overflow_action.setVisible(False)
            for button in self._top_buttons:
                self._button_dict[button].setVisible(button not in self._hidden_dict)

            if self._auto_hide and self._buttons.isVisible() and self._buttons.height() > 0:
                available_height = self._buttons.height()
                if self._buttons.sizeHint().height() > available_height:
                    self._overflow_action.setVisible(True)
                    candidates = [button for button in self._top_buttons if button not in self._hidden_dict]
                    for button in reversed(candidates):
                        if self._buttons.sizeHint().height() <= available_height:
                            break
                        self._overflow_hidden.add(button)
                        source = button.image_btn if isinstance(button, QtLabelledToolbarPushButton) else button
                        self._overflow_enabled[button] = source.isEnabled()
                        self._button_dict[button].setVisible(False)

                    if not self._overflow_hidden:
                        self._overflow_action.setVisible(False)

            self._sync_overflow_menu()
            self._sync_button_widths()
        finally:
            self._updating_overflow = False

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """Recalculate overflow after the internal toolbar is shown or resized."""
        if watched is self._buttons and event.type() in {QEvent.Type.Resize, QEvent.Type.Show}:
            self._schedule_overflow_update()
        return super().eventFilter(watched, event)

    def _sync_button_widths(self) -> None:
        """Keep visible toolbar widgets centered when one button widens."""
        if not self._button_dict:
            return

        visible_buttons = [button for button, action in self._button_dict.items() if action.isVisible()]
        buttons = visible_buttons or list(self._button_dict)
        target_width = max(button.sizeHint().width() for button in buttons)
        for button in self._button_dict:
            button.setFixedWidth(target_width)
        self._overflow_button.setFixedWidth(target_width)

    def add_separator_before(self, button: QtToolbarPushButton | QtLabelledToolbarPushButton) -> None:
        """Add separator before button."""
        self._buttons.insertSeparator(button)

    def add_separator_after(self, button: QtToolbarPushButton | QtLabelledToolbarPushButton) -> None:
        """Add separator."""
        self._buttons.addSeparator()

    def _show_another(self, button: QtToolbarPushButton | QtLabelledToolbarPushButton) -> None:
        """Activate another visible button when the current one cannot stay active."""
        for btn in self._button_dict:
            if btn != button and btn not in self._hidden_dict:
                btn.setChecked(True)
                break
        else:
            with hp.qt_signals_blocked(button):
                button.setChecked(False)
            self._stack.setVisible(False)

    def _toggle_widget(self, button: QtToolbarPushButton | QtLabelledToolbarPushButton, value: bool) -> None:
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

    def _toggle_widget_from_click(
        self,
        button: QtToolbarPushButton | QtLabelledToolbarPushButton,
        *_: ty.Any,
    ) -> None:
        """Activate a panel while ignoring binding-specific signal payloads."""
        self._toggle_widget(button, True)

    def enable_widget(self, button: QtToolbarPushButton | QtLabelledToolbarPushButton) -> None:
        """Enable widget."""
        if button in self._hidden_dict:
            self._hidden_dict.pop(button, None)
            self._update_overflow()

    def disable_widget(self, button: QtToolbarPushButton | QtLabelledToolbarPushButton) -> None:
        """Disable widget."""
        if button in self._hidden_dict:
            return
        action = self._button_dict[button]
        self._hidden_dict[button] = action
        action.setVisible(False)
        self._overflow_hidden.discard(button)
        self._update_overflow()
        if button.isChecked():
            self._show_another(button)

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
    """Toolbar wrapper around :class:`QtPanelWidget`.

    This exposes the most common panel-widget methods directly on the toolbar
    instance so it can be used like a normal `QToolBar` in applications.
    """

    def __init__(
        self,
        parent: QWidget | None = None,
        position: ty.Literal["left", "right"] = "left",
        label_hidden: bool = True,
        auto_hide: bool = True,
    ):
        super().__init__(parent=parent)
        self._widget = QtPanelWidget(self, position=position, label_hidden=label_hidden, auto_hide=auto_hide)

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

    @property
    def label_hidden(self) -> bool:
        """Get label hidden state."""
        return self._widget._label_hidden

    @label_hidden.setter
    def label_hidden(self, value: bool) -> None:
        self._widget.label_hidden = value

    @property
    def auto_hide(self) -> bool:
        """Return whether top buttons automatically collapse into an overflow menu."""
        return self._widget.auto_hide

    @auto_hide.setter
    def auto_hide(self, value: bool) -> None:
        self._widget.auto_hide = value

    def set_disabled(self, button: QtToolbarPushButton | QtLabelledToolbarPushButton, disable: bool) -> None:
        """Set the widget as disabled."""
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
        from qtextra.utils.dev import qdev, qmain, theme_toggle_btn
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
                _description: ty.ClassVar[dict[str, str]] = {
                    "title": choice(
                        ["dimensionality reduction", "machine learning", "spatial", "spectral", "highlights"],
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

        ha.addWidget(qdev(frame))
        ha.addWidget(theme_toggle_btn(frame))

        btn2 = make_btn(frame, "Click me to add widget", func=_add_button)
        ha.addWidget(btn2)
        btn2 = make_btn(frame, "Click me to add panel", func=_add_widget)
        ha.addWidget(btn2)
        btn2 = make_btn(frame, "Enable button", func=_enable_btn)
        ha.addWidget(btn2)
        btn2 = make_btn(frame, "Disable button", func=_disable_btn)
        ha.addWidget(btn2)

        frame.show()
        sys.exit(app.exec_())

    _main()
