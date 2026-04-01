"""Color button."""

from __future__ import annotations

import typing as ty

import numpy as np
from koyo.color import ColorType, rgbs_to_hex
from koyo.color import transform_color as _transform_color
from qtpy.QtCore import QEvent, QRectF, QSize, Qt, Signal, Slot
from qtpy.QtGui import QBrush, QColor, QPainter, QPen
from qtpy.QtWidgets import QAbstractButton, QColorDialog, QFrame, QPushButton, QWidget

BASE_COLOR = "#FFFFFF"
AnyColorType = ty.Union[ColorType, QColor]
TRANSPARENT = np.array([0, 0, 0, 0], np.float32)


FILL_QSS = """
    QPushButton#color_btn {
        border: none;
        margin: 0px;
        padding: 0px;
        background-color: COLOR;
    }
"""
EMPTY_QSS = FILL_QSS.replace("COLOR", "transparent")
HOVER_QSS = """
    QPushButton#color_btn:hover {
        border: 2px solid black;
    }
"""


class QtColorButton(QPushButton):
    """
    Custom widget to allow selection of color.

    Left-clicking the button shows the color-chooser, while
    right-clicking resets the color to None (no-color).

    Modified from: https://www.mfitzp.com/article/QtColorButton-a-color-selector-tool-for-pyqt/
    """

    # new color
    evt_color_changed: Signal = Signal(str)

    def __init__(self, *args, color=None, size: ty.Tuple[int, int] = (16, 16), **kwargs):
        """
        Parameters
        ----------
        color : str
            valid color
        size : tuple
            size of the button
        *args
            Args to pass to QPushButton
        **kwargs
            Extra kwargs to pass to QPushButton
        """
        self._color = color

        super().__init__(*args, **kwargs)

        self.setFixedSize(QSize(*size))
        self.setObjectName("color_btn")
        self.pressed.connect(self.onColorPicker)

        if self._color is not None:
            self.setColor(self._color)

    @property
    def color(self):
        """Returns the color."""
        return self._color

    def setColor(self, color):
        """Set color."""
        if not hasattr(self, "_color"):
            return

        if color != self._color:
            self._color = color
            self.evt_color_changed.emit(color)

        if self._color:
            self.setStyleSheet(FILL_QSS.replace("COLOR", self._color) + HOVER_QSS)
        else:
            self.setStyleSheet(EMPTY_QSS + HOVER_QSS)

    def onColorPicker(self):
        """Show color-picker dialog to select color.

        Using native dialog by default
        """
        color = QColor(self._color) if self._color is not None else None
        dlg = QColorDialog(color, parent=self)
        if dlg.exec_():
            self.setColor(dlg.currentColor().name())

    def mousePressEvent(self, e):
        """On mouse press."""
        if e.button() == Qt.MouseButton.RightButton:
            self.setColor(None)

        return super().mousePressEvent(e)


class QtColorSwatch(QFrame):
    """A QFrame that displays a color and can be clicked to show a QColorPopup.

    Parameters
    ----------
    parent : QWidget, optional
        parent widget, by default None
    tooltip : Optional[str], optional
        Tooltip when hovering on swatch,
        by default 'click to set color'
    initial_color : ColorType, optional
        initial color, by default will be transparent
    add_frame : bool
        add black frame around the swatch to make it stand out

    Signals
    -------
    evt_color_changed : str
        Emits the new color when the current color changes.
    """

    evt_color_changed = Signal(np.ndarray)

    def __init__(
        self,
        parent: QWidget | None = None,
        tooltip: str | None = None,
        initial_color: ColorType | None = None,
        add_frame: bool = True,
    ):
        super().__init__(parent)
        self.setObjectName("colorSwatch")
        self.setToolTip(tooltip or "Click to set color")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._initial_color = initial_color
        self._color: np.ndarray = TRANSPARENT
        self.evt_color_changed.connect(self._update_swatch_style)
        if initial_color is not None:
            self.set_color(initial_color)
        if add_frame:
            self.setFrameShape(QFrame.Shape.Box)
            self.setLineWidth(2)

    def setEnabled(self, enabled: bool) -> None:
        """Set the enabled state of the widget."""
        super().setEnabled(enabled)
        self.setCursor(Qt.CursorShape.PointingHandCursor if enabled else Qt.CursorShape.ArrowCursor)

    @property
    def color(self) -> np.ndarray:
        """Return the current color."""
        return self._color

    @property
    def hex_color(self) -> str:
        """Return color in HEX code."""
        return rgbs_to_hex(self._color)[0]

    @Slot(np.ndarray)
    def _update_swatch_style(self, _color: ColorType) -> None:
        """Update appearance."""
        rgb = [int(x * 255) for x in self._color[:3]]
        alpha = int(self._color[3] * 255) if len(self._color) > 3 else 255
        rgba = f"rgba({rgb[0]}, {rgb[1]}, {rgb[2]}, {alpha})"
        brightness = (0.299 * rgb[0]) + (0.587 * rgb[1]) + (0.114 * rgb[2])
        border = "rgba(20, 20, 20, 160)" if brightness > 186 else "rgba(255, 255, 255, 180)"
        self.setStyleSheet(
            f"#colorSwatch {{background-color: {rgba};border: 1px solid {border};border-radius: 3px;}}",
        )

    def mouseReleaseEvent(self, event: QEvent):
        """Show QColorPopup picker when the user clicks on the swatch."""
        if event.button() == Qt.MouseButton.LeftButton:
            from qtextra.helpers import get_color

            initial = QColor(*(255 * self._color).astype("int"))
            color = get_color(self, initial, False)
            if color is not None:
                self.set_color(color)

    def set_color(self, color: AnyColorType, force: bool = False) -> None:
        """Set the color of the swatch.

        Parameters
        ----------
        color : AnyColorType
            Can be any ColorType recognized by our
            utils.colormaps.standardize_color.transform_color function.
        force : bool
            If True, will emit the color_changed event even if the color
        """
        if isinstance(color, QColor):
            _color = (np.array(color.getRgb()) / 255).astype(np.float32)
        else:
            try:
                from napari.utils.colormaps.standardize_color import transform_color

                _color = transform_color(color)[0]
            except ValueError:
                return self.evt_color_changed.emit(self._color)
            except ImportError:
                try:
                    _color = _transform_color(color)[0]
                except ValueError:
                    return self.evt_color_changed.emit(self._color)

        emit = np.any(self._color != _color)
        self._color = _color
        if emit or np.all(_color == TRANSPARENT):
            self.evt_color_changed.emit(_color)
        if force:
            self._update_swatch_style(_color)
            return None
        return None

    # Alias methods to offer Qt-like interface
    hexColor = hex_color
    setColor = set_color


class ColorCircleButton(QAbstractButton):
    """Circular push-button that opens a QColorDialog on click.

    Signals
    -------
    colorChanged(QColor)
        Emitted whenever the user picks a new color and confirms it.
    """

    colorChanged = Signal(QColor)

    def __init__(
        self,
        color: QColor | str = "#4db8ff",
        diameter: int = 32,
        selected: bool = False,
        parent=None,
    ):
        super().__init__(parent)
        self._color = QColor(color)
        self._diameter = diameter
        self._selected = selected
        self._hovered = False

        self.setCheckable(False)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(self.sizeHint())

        # Track hover manually so we can repaint
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def color(self) -> QColor:
        """Return the current color."""
        return QColor(self._color)

    def set_color(self, color: QColor | str) -> None:
        """Set the current color."""
        self._color = QColor(color)
        self.update()

    @property
    def selected(self) -> bool:
        """Return whether the button is selected."""
        return self._selected

    def set_selected(self, value: bool) -> None:
        """Set the selected state."""
        self._selected = value
        self.update()

    # ------------------------------------------------------------------
    # Qt overrides
    # ------------------------------------------------------------------

    def sizeHint(self) -> QSize:
        """Return the preferred size for the color button."""
        # Extra 4 px padding so the ring/shadow isn't clipped
        pad = 6
        s = self._diameter + pad * 2
        return QSize(s, s)

    def paintEvent(self, _event):
        """Paint the circular swatch."""
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2
        r = self._diameter / 2  # circle radius

        # --- selected ring (white circle slightly larger than fill) ---
        if self._selected:
            ring_r = r + 3
            p.setPen(QPen(QColor("white"), 2.5, Qt.PenStyle.SolidLine))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QRectF(cx - ring_r, cy - ring_r, ring_r * 2, ring_r * 2))

        # --- hover: lighten the fill color slightly ---
        fill = QColor(self._color)
        if self._hovered:
            fill = fill.lighter(115)

        # --- main filled circle ---
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(fill))
        p.drawEllipse(QRectF(cx - r, cy - r, r * 2, r * 2))

        p.end()

    def mousePressEvent(self, event):
        """Open the color dialog on left click."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._open_color_dialog()
        super().mousePressEvent(event)

    def _open_color_dialog(self):
        new_color = QColorDialog.getColor(
            self._color,
            self,
            "Pick a color",
            QColorDialog.ShowAlphaChannel,
        )
        if new_color.isValid():
            self._color = new_color
            self.update()
            self.colorChanged.emit(QColor(self._color))

    # hover tracking
    def enterEvent(self, event):
        """Track hover entry for repainting."""
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Track hover exit for repainting."""
        self._hovered = False
        self.update()
        super().leaveEvent(event)


if __name__ == "__main__":  # pragma: no cover
    import sys

    from qtextra.utils.dev import qframe

    app, frame, ha = qframe(False)
    frame.setLayout(ha)
    frame.setMinimumSize(400, 400)

    w = QtColorButton(size=(64, 64), color="#FF00FF")
    ha.addWidget(w)
    ww = QtColorSwatch(initial_color="#FF0000")
    ha.addWidget(ww)
    ww = QtColorSwatch(initial_color="#FFFF00")
    ha.addWidget(ww)
    ww = QtColorSwatch(initial_color=(255, 123, 32))
    ha.addWidget(ww)

    buttons: list[ColorCircleButton] = []

    def _on_color_changed(btn: ColorCircleButton, color: QColor):
        # Mark the clicked button as selected, deselect others
        for b in buttons:
            b.set_selected(b is btn)
        print(f"Color picked: {color.name(QColor.HexArgb)}")

    def _make_color_changed_handler(btn: ColorCircleButton):
        def _handle_color_changed(color: QColor) -> None:
            _on_color_changed(btn, color)

        return _handle_color_changed

    for i, hex_color in enumerate(["#4db8ff", "#4db8ff", "#4db8ff", "#2a6ebb", "#22264b", "#b3a0d6"]):
        btn = ColorCircleButton(color=hex_color, diameter=32)
        btn.set_selected(i == 1)  # second button selected by default
        btn.colorChanged.connect(_make_color_changed_handler(btn))
        ha.addWidget(btn)
        buttons.append(btn)

    frame.show()
    sys.exit(app.exec_())
