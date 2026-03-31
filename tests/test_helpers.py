"""Tests for qtextra.helpers."""

from __future__ import annotations

import warnings

import pytest
from koyo.system import IS_MAC
from qtpy import API_NAME
from qtpy.QtCore import QSize, Qt
from qtpy.QtGui import QAction, QIntValidator
from qtpy.QtWidgets import QCheckBox, QLabel, QWidget

import qtextra.helpers as hp

# ── layout helpers ─────────────────────────────────────────────────────────────


class TestMakeLayouts:
    def test_make_h_layout_empty(self, qtbot):
        w = QWidget()
        qtbot.addWidget(w)
        layout = hp.make_h_layout()
        assert layout is not None
        assert layout.count() == 0

    def test_make_h_layout_with_widgets(self, qtbot):
        w = QWidget()
        qtbot.addWidget(w)
        a = QLabel("A")
        b = QLabel("B")
        layout = hp.make_h_layout(a, b)
        assert layout.count() == 2

    def test_make_h_layout_spacing(self, qtbot):
        layout = hp.make_h_layout(spacing=8)
        assert layout.spacing() == 8

    def test_make_h_layout_margin_int(self, qtbot):
        layout = hp.make_h_layout(margin=10)
        assert layout.contentsMargins().left() == 10
        assert layout.contentsMargins().right() == 10

    def test_make_h_layout_margin_tuple(self, qtbot):
        layout = hp.make_h_layout(margin=(1, 2, 3, 4))
        m = layout.contentsMargins()
        assert (m.left(), m.top(), m.right(), m.bottom()) == (1, 2, 3, 4)

    def test_make_h_layout_stretch_before(self, qtbot):
        a = QLabel("A")
        layout = hp.make_h_layout(a, stretch_before=True)
        # stretch item + widget = 2 items
        assert layout.count() == 2

    def test_make_h_layout_stretch_after(self, qtbot):
        a = QLabel("A")
        layout = hp.make_h_layout(a, stretch_after=True)
        assert layout.count() == 2

    def test_make_v_layout_empty(self, qtbot):
        layout = hp.make_v_layout()
        assert layout is not None
        assert layout.count() == 0

    def test_make_v_layout_with_widgets(self, qtbot):
        a = QLabel("A")
        b = QLabel("B")
        layout = hp.make_v_layout(a, b)
        assert layout.count() == 2

    def test_make_v_layout_spacing_and_margin(self, qtbot):
        layout = hp.make_v_layout(spacing=5, margin=3)
        assert layout.spacing() == 5
        assert layout.contentsMargins().top() == 3

    def test_make_grid_layout_column_stretch(self, qtbot):
        layout = hp.make_grid_layout(column_to_stretch={0: 2, 1: 1})
        assert layout.columnStretch(0) == 2
        assert layout.columnStretch(1) == 1

    def test_make_grid_layout_int_column_stretch(self, qtbot):
        layout = hp.make_grid_layout(column_to_stretch=0)
        assert layout.columnStretch(0) == 1

    def test_make_form_layout(self, qtbot):
        w = QWidget()
        qtbot.addWidget(w)
        layout = hp.make_form_layout(parent=w, spacing=4)
        assert layout.spacing() == 4

    def test_make_form_layout_with_rows_and_stretch_after(self, qtbot):
        w = QWidget()
        qtbot.addWidget(w)
        field = QLabel("Value")
        layout = hp.make_form_layout(("Name", field), parent=w, stretch_after=True)
        assert layout.rowCount() == 2
        assert layout.itemAt(0, layout.ItemRole.FieldRole).widget() is field


class TestFormLayoutHelpers:
    def test_find_row_helpers_and_remove_insert(self, qtbot):
        parent = QWidget()
        qtbot.addWidget(parent)
        layout = hp.make_form_layout(parent=parent)
        first = QLabel("First value")
        second = QLabel("Second value")
        layout.addRow("First", first)
        layout.addRow("Second", second)

        assert hp.find_row_for_widget(layout, first) == 0
        assert hp.find_row_for_label_in_form_layout(layout, "Second") == 1
        assert hp.find_row_for_widget(layout, QLabel("missing")) is None
        assert hp.find_row_for_label_in_form_layout(layout, "Missing") is None

        row, label_widget, field_widget = hp.remove_widget_in_form_layout(layout, "First")
        assert row == 0
        assert label_widget.text() == "First"
        assert field_widget is first
        assert layout.rowCount() == 1

        replacement = QLabel("Replacement")
        hp.insert_widget_in_form_layout(layout, row, label_widget, replacement)
        assert layout.rowCount() == 2
        assert hp.find_row_for_widget(layout, replacement) == 0

    def test_remove_widget_in_form_layout_missing_label(self, qtbot):
        parent = QWidget()
        qtbot.addWidget(parent)
        layout = hp.make_form_layout(parent=parent)
        layout.addRow("First", QLabel("First value"))

        row, label_widget, field_widget = hp.remove_widget_in_form_layout(layout, "Missing")
        assert row is None
        assert label_widget is None
        assert field_widget is None

    def test_deprecated_make_hbox_layout(self, qtbot):
        parent = QWidget()
        qtbot.addWidget(parent)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            layout = hp.make_hbox_layout(parent, spacing=2)
            assert any("make_hbox_layout" in str(x.message) for x in w)
        assert layout.spacing() == 2
        assert layout.parent() is parent

    def test_deprecated_make_vbox_layout(self, qtbot):
        parent = QWidget()
        qtbot.addWidget(parent)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            layout = hp.make_vbox_layout(parent, spacing=3)
            assert any("make_vbox_layout" in str(x.message) for x in w)
        assert layout.spacing() == 3
        assert layout.parent() is parent

    def test_make_h_layout_rejects_none_widget(self):
        with pytest.raises(TypeError, match="Unsupported item"):
            hp.make_h_layout(None)


# ── widget factory functions ───────────────────────────────────────────────────


class TestMakeLabel:
    def test_basic(self, qtbot):
        w = QWidget()
        qtbot.addWidget(w)
        lbl = hp.make_label(w, "hello")
        assert lbl.text() == "hello"

    def test_bold(self, qtbot):
        w = QWidget()
        qtbot.addWidget(w)
        lbl = hp.make_label(w, "bold text", bold=True)
        assert lbl.font().bold()

    def test_wrap(self, qtbot):
        w = QWidget()
        qtbot.addWidget(w)
        lbl = hp.make_label(w, "wrap", wrap=True)
        assert lbl.wordWrap()

    def test_object_name(self, qtbot):
        w = QWidget()
        qtbot.addWidget(w)
        lbl = hp.make_label(w, object_name="my_label")
        assert lbl.objectName() == "my_label"

    def test_tooltip(self, qtbot):
        w = QWidget()
        qtbot.addWidget(w)
        lbl = hp.make_label(w, tooltip="tip text")
        assert lbl.toolTip() == "tip text"

    def test_hidden(self, qtbot):
        w = QWidget()
        qtbot.addWidget(w)
        lbl = hp.make_label(w, "x", hide=True)
        assert lbl.isHidden()

    def test_visible_false(self, qtbot):
        w = QWidget()
        qtbot.addWidget(w)
        lbl = hp.make_label(w, "x", visible=False)
        assert not lbl.isVisible()

    def test_deprecated_activated_func(self, qtbot):
        w = QWidget()
        qtbot.addWidget(w)
        called = []
        with warnings.catch_warnings(record=True) as warns:
            warnings.simplefilter("always")
            hp.make_label(w, activated_func=lambda url: called.append(url))
            assert any("activated_func" in str(x.message) for x in warns)

    def test_deprecated_click_func(self, qtbot):
        w = QWidget()
        qtbot.addWidget(w)
        with warnings.catch_warnings(record=True) as warns:
            warnings.simplefilter("always")
            hp.make_label(w, click_func=lambda: None)
            assert any("click_func" in str(x.message) for x in warns)

    def test_description_kwarg_as_tooltip(self, qtbot):
        w = QWidget()
        qtbot.addWidget(w)
        lbl = hp.make_label(w, description="desc tip")
        assert lbl.toolTip() == "desc tip"


class TestMakeCombobox:
    def test_items(self, qtbot):
        w = QWidget()
        qtbot.addWidget(w)
        cb = hp.make_combobox(w, items=["A", "B", "C"])
        assert cb.count() == 3

    def test_value(self, qtbot):
        w = QWidget()
        qtbot.addWidget(w)
        cb = hp.make_combobox(w, items=["A", "B", "C"], value="B")
        assert cb.currentText() == "B"

    def test_default_fallback(self, qtbot):
        w = QWidget()
        qtbot.addWidget(w)
        cb = hp.make_combobox(w, items=["X", "Y"], default="Y")
        assert cb.currentText() == "Y"

    def test_enum_alias(self, qtbot):
        w = QWidget()
        qtbot.addWidget(w)
        cb = hp.make_combobox(w, enum=["P", "Q"])
        assert cb.count() == 2

    def test_options_alias(self, qtbot):
        w = QWidget()
        qtbot.addWidget(w)
        cb = hp.make_combobox(w, options=["R", "S"])
        assert cb.count() == 2

    def test_func_callback(self, qtbot):
        w = QWidget()
        qtbot.addWidget(w)
        received = []
        cb = hp.make_combobox(w, items=["A", "B"], func=lambda t: received.append(t))
        cb.setCurrentText("B")
        assert "B" in received

    def test_tooltip(self, qtbot):
        w = QWidget()
        qtbot.addWidget(w)
        cb = hp.make_combobox(w, tooltip="my tip")
        assert cb.toolTip() == "my tip"

    def test_func_index_callback(self, qtbot):
        w = QWidget()
        qtbot.addWidget(w)
        received = []
        cb = hp.make_combobox(w, items=["A", "B"], func_index=lambda t: received.append(t))
        cb.setCurrentText("B")
        assert received[-1] == "B"

    def test_object_name(self, qtbot):
        w = QWidget()
        qtbot.addWidget(w)
        cb = hp.make_combobox(w, items=["A"], object_name="combo_name")
        assert cb.objectName() == "combo_name"


class TestMakeCheckbox:
    def test_text_and_value(self, qtbot):
        w = QWidget()
        qtbot.addWidget(w)
        chk = hp.make_checkbox(w, "Enable", value=True)
        assert chk.text() == "Enable"
        assert chk.isChecked()

    def test_default_value(self, qtbot):
        w = QWidget()
        qtbot.addWidget(w)
        chk = hp.make_checkbox(w, default=True)
        assert chk.isChecked()

    def test_func_callback(self, qtbot):
        w = QWidget()
        qtbot.addWidget(w)
        states = []
        chk = hp.make_checkbox(w, func=lambda s: states.append(s))
        chk.setChecked(True)
        assert len(states) > 0

    def test_tristate(self, qtbot):
        w = QWidget()
        qtbot.addWidget(w)
        chk = hp.make_checkbox(w, tristate=True)
        assert chk.isTristate()

    def test_hidden(self, qtbot):
        w = QWidget()
        qtbot.addWidget(w)
        chk = hp.make_checkbox(w, hide=True)
        assert chk.isHidden()

    def test_clicked_callback_and_properties(self, qtbot):
        w = QWidget()
        qtbot.addWidget(w)
        clicked = []
        chk = hp.make_checkbox(w, clicked=lambda state: clicked.append(state), properties={"role": "primary"})
        chk.click()
        assert clicked == [True]
        assert chk.property("role") == "primary"


class TestMakeLineEdit:
    def test_default_placeholder_and_object_name(self, qtbot):
        w = QWidget()
        qtbot.addWidget(w)
        line = hp.make_line_edit(w, default="Alpha", placeholder="Enter", object_name="line_name")
        assert line.text() == "Alpha"
        assert line.placeholderText() == "Enter"
        assert line.objectName() == "line_name"

    def test_validator_and_callbacks(self, qtbot):
        w = QWidget()
        qtbot.addWidget(w)
        changed = []
        entered = []
        cleared = []
        line = hp.make_line_edit(
            w,
            validator=QIntValidator(0, 10, w),
            func_changed=lambda text: changed.append(text),
            func_enter=lambda: entered.append(True),
            func_clear=lambda: cleared.append(True),
        )
        assert line.validator() is not None
        line.setText("5")
        line.returnPressed.emit()
        action = line.findChild(QAction)
        if action:
            action.trigger()
        assert changed[-1] == "5"
        assert entered == [True]
        assert cleared == [True]


class TestSpinBoxes:
    def test_make_int_spin_box_options(self, qtbot):
        w = QWidget()
        qtbot.addWidget(w)
        seen = []
        spin = hp.make_int_spin_box(
            w,
            minimum=1,
            maximum=9,
            step_size=2,
            value=3,
            prefix="$",
            suffix="px",
            keyboard_tracking=False,
            func=lambda value: seen.append(value),
            properties={"role": "number"},
        )
        spin.setValue(5)
        assert spin.minimum() == 1
        assert spin.maximum() == 9
        assert spin.singleStep() == 2
        assert spin.prefix() == "$"
        assert spin.suffix() == "px"
        assert spin.keyboardTracking() is False
        assert spin.property("role") == "number"
        assert seen[-1] == 5

    def test_make_double_spin_box_options(self, qtbot):
        w = QWidget()
        qtbot.addWidget(w)
        seen = []
        spin = hp.make_double_spin_box(
            w,
            minimum=0.5,
            maximum=2.5,
            step_size=0.5,
            value=1.5,
            n_decimals=2,
            prefix="~",
            suffix="s",
            func=lambda value: seen.append(value),
        )
        spin.setValue(2.0)
        assert spin.minimum() == 0.5
        assert spin.maximum() == 2.5
        assert spin.singleStep() == 0.5
        assert spin.decimals() == 2
        assert spin.prefix() == "~"
        assert spin.suffix() == "s"
        assert seen[-1] == 2.0


class TestMakeSlider:
    def test_range(self, qtbot):
        w = QWidget()
        qtbot.addWidget(w)
        s = hp.make_slider(w, minimum=10, maximum=50, value=20)
        assert s.minimum() == 10
        assert s.maximum() == 50
        assert s.value() == 20

    def test_func_callback(self, qtbot):
        w = QWidget()
        qtbot.addWidget(w)
        values = []
        s = hp.make_slider(w, minimum=0, maximum=100, value=0, func=lambda v: values.append(v))
        s.setValue(42)
        assert 42 in values


# ── size policy helpers ────────────────────────────────────────────────────────


class TestSetSizerPolicy:
    def test_min_size_tuple(self, qtbot):
        w = QWidget()
        qtbot.addWidget(w)
        hp.set_sizer_policy(w, min_size=(100, 50))
        assert w.minimumWidth() == 100
        assert w.minimumHeight() == 50

    def test_max_size_tuple(self, qtbot):
        w = QWidget()
        qtbot.addWidget(w)
        hp.set_sizer_policy(w, max_size=(200, 150))
        assert w.maximumWidth() == 200
        assert w.maximumHeight() == 150

    def test_min_size_qsize(self, qtbot):
        w = QWidget()
        qtbot.addWidget(w)
        hp.set_sizer_policy(w, min_size=QSize(80, 40))
        assert w.minimumWidth() == 80
        assert w.minimumHeight() == 40

    def test_no_size_no_crash(self, qtbot):
        w = QWidget()
        qtbot.addWidget(w)
        hp.set_sizer_policy(w)  # should not raise


# ── style helpers ──────────────────────────────────────────────────────────────


class TestStyleHelpers:
    def test_set_tooltip(self, qtbot):
        w = QWidget()
        qtbot.addWidget(w)
        hp.set_tooltip(w, "a tooltip")
        assert w.toolTip() == "a tooltip"

    def test_set_bold(self, qtbot):
        w = QLabel("text")
        qtbot.addWidget(w)
        hp.set_bold(w, True)
        assert w.font().bold()

    def test_set_bold_false(self, qtbot):
        w = QLabel("text")
        qtbot.addWidget(w)
        hp.set_bold(w, False)
        assert not w.font().bold()

    def test_update_widget_style(self, qtbot):
        w = QWidget()
        qtbot.addWidget(w)
        hp.update_widget_style(w, "my_style")
        assert w.objectName() == "my_style"

    def test_set_object_name_no_change_if_same(self, qtbot):
        w = QWidget()
        qtbot.addWidget(w)
        w.setObjectName("same")
        # Should not crash or raise even when the same name is set
        hp.set_object_name(w, object_name="same")
        assert w.objectName() == "same"

    def test_set_object_name_updates(self, qtbot):
        w = QWidget()
        qtbot.addWidget(w)
        hp.set_object_name(w, object_name="new_name")
        assert w.objectName() == "new_name"

    def test_set_properties(self, qtbot):
        w = QWidget()
        qtbot.addWidget(w)
        hp.set_properties(w, {"data-role": "primary"})
        assert w.property("data-role") == "primary"

    def test_set_properties_none_no_crash(self, qtbot):
        w = QWidget()
        qtbot.addWidget(w)
        hp.set_properties(w, None)  # should not raise


# ── screen geometry helper ─────────────────────────────────────────────────────


class TestGetCurrentScreenGeometry:
    def test_returns_qrect(self, qtbot):
        from qtpy.QtCore import QRect

        rect = hp.get_current_screen_geometry()
        assert isinstance(rect, QRect)
        assert rect.width() > 0
        assert rect.height() > 0

    def test_full_geometry_when_false(self, qtbot):
        rect_avail = hp.get_current_screen_geometry(available=True)
        rect_full = hp.get_current_screen_geometry(available=False)
        # Full geometry is >= available geometry
        assert rect_full.width() >= rect_avail.width()

    def test_deprecated_avaliable_spelling(self, qtbot):
        """Passing old misspelled `avaliable` kwarg should still work with a warning."""
        from qtpy.QtCore import QRect

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            rect = hp.get_current_screen_geometry(avaliable=True)
            assert isinstance(rect, QRect)
            assert any("avaliable" in str(x.message) for x in w)


# ── hyper helper ───────────────────────────────────────────────────────────────


class TestHyper:
    def test_string_link_default_prefix(self):
        result = hp.hyper("example.com", "Click here")
        assert "href='goto:example.com'" in result
        assert "Click here" in result

    def test_string_link_no_prefix(self):
        result = hp.hyper("http://example.com", "Link", prefix="")
        assert "href='http://example.com'" in result

    def test_path_link(self, tmp_path):
        p = tmp_path / "file.txt"
        p.write_text("hello")
        result = hp.hyper(p, "Open")
        assert "file://" in result
        assert "Open" in result

    def test_no_value_uses_link(self):
        result = hp.hyper("target", prefix="goto")
        assert ">target<" in result


# ── validate_func helper ───────────────────────────────────────────────────────


class TestValidateFunc:
    def test_single_callable(self):
        def f():
            return None

        result = hp._validate_func(f)
        assert result == [f]

    def test_list_of_callables(self):
        def f1():
            return None

        def f2():
            return None

        result = hp._validate_func([f1, f2])
        assert result == [f1, f2]

    def test_filters_non_callables(self):
        def f():
            return None

        result = hp._validate_func([f, "not_callable", None])
        assert result == [f]


# ── get_orientation helper ─────────────────────────────────────────────────────


class TestGetOrientation:
    def test_string_horizontal(self):
        result = hp.get_orientation("horizontal")
        assert result == Qt.Orientation.Horizontal

    def test_string_vertical(self):
        result = hp.get_orientation("vertical")
        assert result == Qt.Orientation.Vertical

    def test_qt_orientation_passthrough(self):
        result = hp.get_orientation(Qt.Orientation.Vertical)
        assert result == Qt.Orientation.Vertical


# ── make_spacer helpers ────────────────────────────────────────────────────────


class TestSpacers:
    def test_make_h_spacer(self, qtbot):
        spacer = hp.make_h_spacer()
        assert spacer is not None

    def test_make_v_spacer(self, qtbot):
        spacer = hp.make_v_spacer()
        assert spacer is not None

    def test_make_spacer_widget(self, qtbot):
        w = hp.make_spacer_widget()
        assert isinstance(w, QWidget)


# ── make_btn ───────────────────────────────────────────────────────────────────


class TestMakeBtn:
    def test_text_and_tooltip(self, qtbot):
        parent = QWidget()
        qtbot.addWidget(parent)
        btn = hp.make_btn(parent, "Click me", tooltip="tip")
        assert btn.text() == "Click me"
        assert btn.toolTip() == "tip"

    def test_func_callback(self, qtbot):
        parent = QWidget()
        qtbot.addWidget(parent)
        clicked = []
        btn = hp.make_btn(parent, "OK", func=lambda: clicked.append(1))
        btn.click()
        assert clicked == [1]

    def test_disabled(self, qtbot):
        parent = QWidget()
        qtbot.addWidget(parent)
        btn = hp.make_btn(parent, "X", disabled=True)
        assert not btn.isEnabled()


# ── make_separator helpers ─────────────────────────────────────────────────────


class TestSeparators:
    def test_make_h_line(self, qtbot):
        parent = QWidget()
        qtbot.addWidget(parent)
        line = hp.make_h_line(parent)
        assert line is not None

    def test_make_v_line(self, qtbot):
        parent = QWidget()
        qtbot.addWidget(parent)
        line = hp.make_v_line(parent)
        assert line is not None

    def test_make_h_line_with_text(self, qtbot):
        parent = QWidget()
        qtbot.addWidget(parent)
        widget = hp.make_h_line_with_text("Section", parent=parent)
        assert widget is not None


class TestSignalHelpers:
    def test_qt_signals_blocked_blocks_and_restores(self, qtbot):
        widget = QCheckBox()
        qtbot.addWidget(widget)
        seen = []
        widget.stateChanged.connect(seen.append)

        with hp.qt_signals_blocked(widget):
            widget.setChecked(True)

        assert widget.isChecked() is True
        assert seen == []

        widget.setChecked(False)
        assert seen[-1] == 0

    def test_qt_signals_blocked_passthrough(self, qtbot):
        widget = QCheckBox()
        qtbot.addWidget(widget)
        seen = []
        widget.stateChanged.connect(seen.append)

        with hp.qt_signals_blocked(widget, block_signals=False):
            widget.setChecked(True)

        assert seen[-1] == 2


class TestMiscHelpers:
    def test_safe_float(self):
        assert hp.safe_float("1.25") == 1.25
        assert hp.safe_float("bad", default=3.5) == 3.5
        assert hp.safe_float(None, default=4.0) == 4.0

    def test_make_auto_update_layout(self, qtbot):
        parent = QWidget()
        qtbot.addWidget(parent)
        seen = []
        button, checkbox, layout = hp.make_auto_update_layout(parent, lambda: seen.append("clicked"))

        assert button.text() == "Update"
        assert checkbox.text() == "Auto-update"
        assert checkbox.isChecked() is True
        assert button.isEnabled() is False
        assert layout.count() == 2

        checkbox.setChecked(False)
        assert button.isEnabled() is True

        button.click()
        assert seen == ["clicked"]


# ── make_swatch_grid index fix ─────────────────────────────────────────────────


class TestMakeSwatchGrid:
    def test_grid_swatch_count_matches_colors(self, qtbot):
        parent = QWidget()
        qtbot.addWidget(parent)
        colors = ["#ff0000", "#00ff00", "#0000ff", "#ffffff", "#000000"]
        indices_received = []
        layout, swatches = hp.make_swatch_grid(parent, colors, func=lambda i, c: indices_received.append(i))
        assert len(swatches) == 5

    def test_flow_layout_swatch_count(self, qtbot):
        parent = QWidget()
        qtbot.addWidget(parent)
        colors = ["#ff0000", "#00ff00", "#0000ff"]
        layout, swatches = hp.make_swatch_grid(parent, colors, func=lambda i, c: None, use_flow_layout=True)
        assert len(swatches) == 3

    def test_grid_indices_are_global_not_per_chunk(self, qtbot):
        """Regression: swatch count must match color count even across chunk boundaries."""
        parent = QWidget()
        qtbot.addWidget(parent)
        # 12 colors — crosses the 10-per-row boundary
        colors = [f"#{i:02x}{i:02x}{i:02x}" for i in range(12)]
        received_indices = []

        def record(i, color):
            received_indices.append(i)

        layout, swatches = hp.make_swatch_grid(parent, colors, func=record)
        # All 12 swatches must be present
        assert len(swatches) == 12

        # Trigger each swatch by setting a distinct new color — should fire unique indices
        new_colors = [f"#{(i + 1) % 256:02x}{(i + 2) % 256:02x}{(i + 3) % 256:02x}" for i in range(12)]
        for swatch, new_color in zip(swatches, new_colors):
            swatch.set_color(new_color)

        # Indices should be 0..11 (not resetting to 0..1 after the 10th swatch)
        assert len(received_indices) == 12
        assert sorted(received_indices) == list(range(12))


@pytest.mark.skipif(API_NAME == "pyside6" and IS_MAC, reason="Skipped on PySide6 on macOS")
def test_add_flash_animation(qtbot):
    widget = QWidget()
    qtbot.addWidget(widget)
    assert widget.graphicsEffect() is None
    hp.add_flash_animation(widget, duration=50)
    assert widget.graphicsEffect() is not None
    assert hasattr(widget, "_flash_animation")
    qtbot.waitUntil(lambda: widget.graphicsEffect() is None, timeout=1500)
    assert widget.graphicsEffect() is None
    assert not hasattr(widget, "_flash_animation")
