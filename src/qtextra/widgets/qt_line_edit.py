from __future__ import annotations

import operator
from decimal import Decimal

from qtpy import QtCore, QtGui
from qtpy import QtWidgets as QtW
from qtpy.QtCore import Qt


class QIntOrNoneValidator(QtGui.QIntValidator):
    """Validator that accepts '' as None, and otherwise behaves as QIntValidator."""

    def validate(self, a0: str | None, a1: int) -> tuple[QtGui.QValidator.State, str, int]:
        """Validate a string using the configured child validator."""
        if a0 == "":
            return QtGui.QValidator.State.Acceptable, "", a1
        return super().validate(a0, a1)


class QDoubleOrNoneValidator(QtGui.QDoubleValidator):
    """Validator that accepts '' as None, and otherwise behaves as QDoubleValidator."""

    def validate(self, a0: str | None, a1: int) -> tuple[QtGui.QValidator.State, str, int]:
        """Validate a string using the configured child validator."""
        if a0 == "":
            return QtGui.QValidator.State.Acceptable, "", a1
        return super().validate(a0, a1)


class QCommaSeparatedValidator(QtGui.QValidator):
    """Base validator for comma-separated values using a child validator."""

    _ChildValidator: QtGui.QValidator

    def validate(self, a0: str | None, a1: int) -> tuple[QtGui.QValidator.State, str, int]:
        """Validate a comma-separated string using the configured child validator."""
        if a0 == "" or a0 is None:
            return QtGui.QValidator.State.Acceptable, "", a1
        if a0.strip().endswith(","):
            if a0.strip().endswith(",,"):
                return QtGui.QValidator.State.Invalid, a0, a1
            return QtGui.QValidator.State.Intermediate, a0, a1
        state_list = [self._ChildValidator.validate(part.strip(), 0)[0] for part in a0.split(",")]
        is_valid = all(state == QtGui.QValidator.State.Acceptable for state in state_list)
        is_intermediate = all(state != QtGui.QValidator.State.Invalid for state in state_list)
        if is_valid:
            return QtGui.QValidator.State.Acceptable, a0, a1
        if is_intermediate:
            return QtGui.QValidator.State.Intermediate, a0, a1
        return QtGui.QValidator.State.Invalid, a0, a1


class QCommaSeparatedIntValidator(QCommaSeparatedValidator):
    """Validator for comma-separated integer values."""

    _ChildValidator = QtGui.QIntValidator()


class QCommaSeparatedDoubleValidator(QCommaSeparatedValidator):
    """Validator for comma-separated floating-point values."""

    _ChildValidator = QtGui.QDoubleValidator()


class QValuedLineEdit(QtW.QLineEdit):
    """Base line edit that emits validated values and supports stepping."""

    _validator_class: type[QIntOrNoneValidator | QDoubleOrNoneValidator]
    valueChanged = QtCore.Signal(str)

    def __init__(self, *args, **kwargs):
        """Initialize the line edit with its validator and value-change wiring."""
        super().__init__(*args, **kwargs)
        self.setValidator(self._validator_class(self))
        self.textChanged.connect(self._on_text_changed)

    def _on_text_changed(self, text: str):
        """Emit the normalized value when the current text is acceptable."""
        validate_result = self.validator().validate(text, 0)
        if validate_result[0] == QtGui.QValidator.State.Acceptable:
            self.valueChanged.emit(validate_result[1])

    def sizeHint(self) -> QtCore.QSize:
        """Return a compact size hint suitable for numeric editing."""
        hint = super().sizeHint()
        hint.setWidth(100)  # numerical values do not need to be too wide
        return hint

    def stepUp(self, large: bool = False):
        """Step up."""
        raise NotImplementedError

    def stepDown(self, large: bool = False):
        """Step down."""
        raise NotImplementedError

    def wheelEvent(self, a0: QtGui.QWheelEvent | None) -> None:
        """Handle mouse-wheel stepping."""
        if a0 is not None:
            if a0.angleDelta().y() > 0:
                self.stepUp()
                a0.accept()
            elif a0.angleDelta().y() < 0:
                self.stepDown()
                a0.accept()
        return super().wheelEvent(a0)

    def keyPressEvent(self, a0: QtGui.QKeyEvent | None) -> None:
        """Handle keyboard-based stepping shortcuts."""
        if a0.modifiers() == Qt.KeyboardModifier.NoModifier:
            if a0.key() == Qt.Key.Key_Up:
                self.stepUp()
                return None
            if a0.key() == Qt.Key.Key_PageUp:
                self.stepUp(large=True)
                return None
            if a0.key() == Qt.Key.Key_Down:
                self.stepDown()
                return None
            if a0.key() == Qt.Key.Key_PageDown:
                self.stepDown(large=True)
                return None
            return super().keyPressEvent(a0)
        return super().keyPressEvent(a0)

    def minimum(self):
        """Return the validator minimum."""
        return self.validator().bottom()

    def setMinimum(self, min_):
        """Set the validator minimum."""
        self.validator().setBottom(min_)

    def maximum(self):
        """Return the validator maximum."""
        return self.validator().top()

    def setMaximum(self, max_):
        """Set the validator maximum."""
        self.validator().setTop(max_)

    def validator(self) -> QIntOrNoneValidator | QDoubleOrNoneValidator:
        """Return the typed validator instance."""
        return super().validator()


class QIntLineEdit(QValuedLineEdit):
    """Integer line edit."""

    _validator_class = QIntOrNoneValidator

    def stepUp(self, large: bool = False):
        """Step up."""
        text = self.text()
        if text == "":
            return
        val = int(text)
        diff: int = 100 if large else 1
        self.setText(str(min(val + diff, self.validator().top())))

    def stepDown(self, large: bool = False):
        """Step down."""
        text = self.text()
        if text == "":
            return
        val = int(text)
        diff: int = 100 if large else 1
        self.setText(str(max(val - diff, self.validator().bottom())))


class QDoubleLineEdit(QValuedLineEdit):
    """QLineEdit for double values."""

    _validator_class = QDoubleOrNoneValidator

    def stepUp(self, large: bool = False):
        """Step up."""
        return self._step_up_or_down(large, operator.add)

    def stepDown(self, large: bool = False):
        """Step down."""
        return self._step_up_or_down(large, operator.sub)

    def _step_up_or_down(self, large: bool, op):
        """Apply a step operation to the current decimal value."""
        text = self.text()
        if text == "":
            return
        if "e" in text:
            val_text, exp_text = text.split("e")
            if large:
                exp_dec = Decimal(exp_text)
                diff = self._calc_diff(exp_dec, False)
                exp_ = op(exp_dec, diff)
                if (
                    Decimal(val_text) * 10**exp_ > self.validator().top()
                    or Decimal(val_text) * 10**exp_ < self.validator().bottom()
                ):
                    return
                self.setText(val_text + "e" + str(exp_))
            else:
                val_min = self.validator().bottom() / 10 ** int(exp_text)
                val_max = self.validator().top() / 10 ** int(exp_text)
                val_dec = Decimal(val_text)
                diff = self._calc_diff(val_dec, False)
                val = op(val_dec, diff)
                val = max(min(val, val_max), val_min)
                self.setText(str(val) + "e" + exp_text)
        else:
            dec = Decimal(text)
            diff = self._calc_diff(dec, large)
            val = op(dec, diff)
            val = max(min(val, self.validator().top()), self.validator().bottom())
            self.setText(str(val))

    def _calc_diff(self, dec: Decimal, large: bool):
        """Calculate the step size from the current decimal precision."""
        exponent = dec.as_tuple().exponent
        if not isinstance(exponent, int):
            return None
        ten = Decimal(10)
        return ten ** (exponent + 2) if large else ten**exponent


class QCommaSeparatedIntLineEdit(QtW.QLineEdit):
    """QLineEdit for comma separated integer values."""

    def __init__(self, *args, **kwargs):
        """Initialize the line edit with the integer-list validator."""
        super().__init__(*args, **kwargs)
        self.setValidator(QCommaSeparatedIntValidator(self))


class QCommaSeparatedDoubleLineEdit(QtW.QLineEdit):
    """QLineEdit for comma separated double values."""

    def __init__(self, *args, **kwargs):
        """Initialize the line edit with the floating-point-list validator."""
        super().__init__(*args, **kwargs)
        self.setValidator(QCommaSeparatedDoubleValidator(self))


if __name__ == "__main__":  # pragma: no cover

    def _main():  # type: ignore[no-untyped-def]
        import sys

        from qtextra.utils.dev import qframe

        app, frame, ha = qframe(False)
        frame.setMinimumSize(600, 600)

        ha.addWidget(QIntLineEdit(parent=frame))
        ha.addWidget(QDoubleLineEdit(parent=frame))
        ha.addWidget(QCommaSeparatedIntLineEdit(parent=frame))
        ha.addWidget(QCommaSeparatedDoubleLineEdit(parent=frame))

        frame.show()
        sys.exit(app.exec_())

    _main()
