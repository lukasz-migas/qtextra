"""Toggle group."""

from __future__ import annotations

import typing as ty

from qtpy.QtCore import Signal
from qtpy.QtWidgets import QFrame, QWidget

from qtextra.typing import OptionalCallback


class QtToggleGroup(QFrame):
    """Widget for toggle group."""

    _old_value: ty.Any = None

    evt_changed = Signal(object)

    def __init__(
        self,
        parent: QWidget | None,
        options: list[str],
        value: str = "",
        tooltip: str = "",
        orientation: str = "horizontal",
        exclusive: bool = True,
        multiline: bool = False,
    ):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.Box)
        self.setLineWidth(1)
        self.setMinimumHeight(26)

        import qtextra.helpers as hp

        layout, self.button_group = hp.make_toggle_group(
            self,
            *options,
            checked_label=value,
            tooltip=tooltip,
            func=self._on_changed,
            orientation=orientation,
            exclusive=exclusive,
            multiline=multiline,
        )
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(1)
        self.setLayout(layout)

    def _on_changed(self, _: ty.Any) -> None:
        if self._old_value != self.value:
            self._old_value = self.value
            self.evt_changed.emit(self.value)

    @property
    def buttons(self) -> list[QWidget]:
        """Buttons."""
        return self.button_group.buttons()

    @property
    def checked_buttons(self) -> ty.Any:
        """Button."""
        value = []
        for button in self.button_group.buttons():
            if button.isChecked():
                value.append(button)
        return value

    @property
    def value(self) -> str | list[str] | None:
        """Get value."""
        buttons = self.checked_buttons
        value = [button.text() for button in buttons]
        if self.button_group.exclusive():
            return value[0] if value else None
        return value

    @value.setter
    def value(self, value: str | list[str]) -> None:
        """Set value."""
        if not isinstance(value, list):
            value = [value]
        for button in self.button_group.buttons():
            button.setChecked(button.text() in value)

    @classmethod
    def from_schema(
        cls: type[QtToggleGroup],
        parent: QWidget | None,
        options: list[str] | None = None,
        value: str | list[str] | None = None,
        tooltip: str = "",
        orientation: str = "horizontal",
        default: str | list[str] = "",
        description: str = "",
        items: dict[str, ty.Any] | None = None,
        func: OptionalCallback = None,
        exclusive: bool = True,
        multiline: bool = False,
        **kwargs: dict,
    ) -> QtToggleGroup:
        """From schema."""
        import qtextra.helpers as hp

        if default:
            value = default
        if value is None:
            value = default
        if description and not tooltip:
            tooltip = description
        if items and "enum" in items:
            options = items["enum"]
        if "enum" in kwargs:
            options = kwargs["enum"]
        widget = cls(
            parent,
            options=options,
            value=value,
            tooltip=tooltip,
            orientation=orientation,
            exclusive=exclusive,
            multiline=multiline,
        )
        if func:
            [widget.evt_changed.connect(func_) for func_ in hp._validate_func(func)]
        return widget


if __name__ == "__main__":  # pragma: no cover
    import sys

    from qtextra.utils.dev import qframe

    app, frame, ha = qframe(False)
    frame.setLayout(ha)

    wdg = QtToggleGroup.from_schema(None, [str(i) for i in range(15)], "1", func=print)
    ha.addWidget(wdg)

    wdg = QtToggleGroup.from_schema(None, [str(i) for i in range(15)], ["1", "5"], exclusive=False, func=print)
    ha.addWidget(wdg)

    wdg = QtToggleGroup.from_schema(
        None, [str(i) for i in range(15)], ["1", "5"], exclusive=False, func=print, orientation="flow"
    )
    ha.addWidget(wdg)

    wdg = QtToggleGroup.from_schema(None, [str(i) for i in range(15)], "1", func=print)
    wdg.setObjectName("error")
    ha.addWidget(wdg)

    wdg = QtToggleGroup.from_schema(None, [str(i) for i in range(15)], "1", func=print)
    wdg.setObjectName("warning")
    ha.addWidget(wdg)

    frame.show()
    sys.exit(app.exec_())
