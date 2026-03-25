"""Tests for qtextra.helpers."""

from __future__ import annotations

import warnings

import pytest
from qtpy.QtCore import QSize, Qt
from qtpy.QtWidgets import QApplication, QCheckBox, QComboBox, QLabel, QWidget

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

    def test_deprecated_make_hbox_layout(self, qtbot):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            layout = hp.make_hbox_layout(spacing=2)
            assert any("make_hbox_layout" in str(x.message) for x in w)
        assert layout.spacing() == 2

    def test_deprecated_make_vbox_layout(self, qtbot):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            layout = hp.make_vbox_layout(spacing=3)
            assert any("make_vbox_layout" in str(x.message) for x in w)
        assert layout.spacing() == 3


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
            lbl = hp.make_label(w, activated_func=lambda url: called.append(url))
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
        from qtpy.QtCore import QRect

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
        f = lambda: None
        result = hp._validate_func(f)
        assert result == [f]

    def test_list_of_callables(self):
        f1 = lambda: None
        f2 = lambda: None
        result = hp._validate_func([f1, f2])
        assert result == [f1, f2]

    def test_filters_non_callables(self):
        f = lambda: None
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
