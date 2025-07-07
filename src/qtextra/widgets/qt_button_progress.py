"""Button with progress bar."""

from __future__ import annotations

from qtpy.QtWidgets import QHBoxLayout, QProgressBar, QVBoxLayout, QWidget


class QtActiveProgressBarButton(QWidget):
    """Button with progress bar in a layout."""

    def __init__(self, parent: QWidget | None, text: str = "", which: str = "infinity"):
        super().__init__(parent=parent)

        import qtextra.helpers as hp

        self.active_btn = hp.make_active_btn(self, text, which=which)
        self.evt_clicked = self.active_btn.clicked
        self.setText = self.active_btn.setText

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setObjectName("progress_timer")
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setMaximumHeight(10)
        hp.set_sizer_policy(self.progress_bar, h_stretch=True, v_stretch=False)
        hp.set_retain_hidden_size_policy(self.progress_bar)

        self.cancel_btn = hp.make_qta_btn(self, "cancel", average=True)
        self.cancel_btn.setVisible(False)
        self.evt_cancel = self.cancel_btn.clicked

        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(2)
        button_layout.addWidget(self.active_btn, stretch=True)
        button_layout.addWidget(self.cancel_btn)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addLayout(button_layout)
        layout.addWidget(self.progress_bar)
        # layout.addStretch(True)
        self.active = False

    @property
    def active(self) -> bool:
        """Update the state of the loading label."""
        return self.active_btn.active

    @active.setter
    def active(self, value: bool) -> None:
        self.active_btn.active = value
        self.cancel_btn.setVisible(value)
        self.progress_bar.setValue(0)
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(value)

    @property
    def step(self) -> int:
        """Set current step."""
        return self.progress_bar.value()

    @step.setter
    def step(self, value: int) -> None:
        self.progress_bar.setValue(value)
        self.progress_bar.setToolTip(f"Step {value} of {self.progress_bar.maximum()}")

    def setMaximum(self, max_val: int) -> None:
        """Set maximum."""
        self.progress_bar.setMaximum(max_val)
        self.progress_bar.setToolTip(f"Step {self.progress_bar.value()} of {max_val}")

    def setMinimum(self, min_val: int) -> None:
        """Set minimum."""
        self.progress_bar.setMinimum(min_val)
        self.progress_bar.setToolTip(f"Step {self.progress_bar.value()} of {self.progress_bar.maximum()}")

    def setValue(self, value: int) -> None:
        """Set value."""
        self.progress_bar.setValue(value)
        self.progress_bar.setToolTip(f"Step {value} of {self.progress_bar.maximum()}")

    def setRange(self, min_val: int, max_val: int) -> None:
        """Set range."""
        self.progress_bar.setRange(min_val, max_val)
        self.progress_bar.setToolTip(f"Step {self.progress_bar.value()} of {max_val}")


if __name__ == "__main__":  # pragma: no cover
    import sys

    from qtextra.utils.dev import qframe

    def _test1():
        btn1.setValue(btn1.step + 1)
        btn1.active = not btn1.active

    def _test2():
        btn2.setValue(btn2.step + 1)
        btn2.active = not btn2.active

    app, frame, ha = qframe(False)
    frame.setMinimumSize(600, 600)
    btn1 = QtActiveProgressBarButton(frame)
    btn1.evt_clicked.connect(_test1)
    btn1.setText("TEST BUTTON")
    btn1.setRange(0, 100)
    ha.addWidget(btn1)

    btn2 = QtActiveProgressBarButton(frame)
    btn2.evt_clicked.connect(_test2)
    btn2.setText("TEST BUTTON")
    btn2.setRange(0, 100)
    ha.addWidget(btn2)

    frame.show()
    sys.exit(app.exec_())
