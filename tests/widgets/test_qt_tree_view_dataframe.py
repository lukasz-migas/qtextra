"""Tests for QtDataFrameTreeWidget."""

from __future__ import annotations

import time

import numpy as np
import pandas as pd
import pytest
from qtpy.QtCore import QModelIndex, QPoint, Qt

from qtextra.widgets.qt_tree_view_dataframe import TREE_COLUMN, QtDataFrameTreeWidget


@pytest.fixture
def frame() -> pd.DataFrame:
    """Two compounds seen in several datasets, plus one single-row compound."""
    return pd.DataFrame(
        {
            "compound": ["PC 32:0", "PC 32:0", "PC 32:0", "SM 34:1", "SM 34:1", "TG 50:1"],
            "adduct": ["[M+H]+", "[M+Na]+", "[M+H]+", "[M+H]+", "[M+H]+", "[M+NH4]+"],
            "dataset": ["kidney", "kidney", "liver", "kidney", "liver", "liver"],
            "ppm": [1.0, -2.0, 3.0, 0.5, -0.5, 4.0],
            "fdr": [0.01, 0.2, 0.05, 0.1, np.nan, 0.5],
        }
    )


def _widget(qtbot, df: pd.DataFrame, **kwargs) -> QtDataFrameTreeWidget:
    widget = QtDataFrameTreeWidget(None, df, **kwargs)
    qtbot.addWidget(widget)
    widget.resize(800, 400)
    return widget


def _top(model) -> list[str]:
    return [model.data(model.index(row, 0)) for row in range(model.rowCount())]


def _column(model, name: str) -> int:
    return model.model_column(model._column_index(name))


def test_groups_show_counts_and_aggregates(qtbot, frame) -> None:
    widget = _widget(
        qtbot, frame, group_by="compound", label_column="dataset", aggregations={"fdr": "min", "dataset": "nunique"}
    )
    model = widget.model

    assert _top(model) == ["PC 32:0 (3)", "SM 34:1 (2)", "TG 50:1 (1)"]
    pc = model.index(0, 0)
    assert model.rowCount(pc) == 3
    assert model.data(model.index(0, 0, pc)) == "kidney"  # leaf label
    assert model.data(model.index(0, _column(model, "ppm"))) == "0.6667"  # mean
    assert model.data(model.index(0, _column(model, "fdr"))) == "0.0100"  # min
    assert not model.is_column_visible(model._column_index("dataset"))  # label column is shown in the tree column
    widget.set_column_visible("dataset", True)
    assert model.data(model.index(0, _column(model, "dataset"))) == "2"  # nunique
    assert model.data(model.index(0, _column(model, "adduct"))) == "2 values"  # default text aggregation
    assert model.data(model.index(1, _column(model, "adduct"))) == "[M+H]+"
    assert not model.is_column_visible(model._column_index("compound"))
    assert model.data(pc, Qt.ItemDataRole.FontRole).bold()


def test_filters_hide_empty_groups_and_update_aggregates(qtbot, frame) -> None:
    widget = _widget(qtbot, frame, group_by="compound", aggregations={"fdr": "min"})
    model = widget.model

    widget.set_numeric_filter("ppm", minimum=0.0)
    assert _top(model) == ["PC 32:0 (2)", "SM 34:1 (1)", "TG 50:1 (1)"]
    assert model.data(model.index(0, _column(model, "ppm"))) == "2.0000"

    widget.set_value_filter("dataset", ["kidney"])
    assert _top(model) == ["PC 32:0 (1)", "SM 34:1 (1)"]
    assert model.is_column_filtered(model._column_index("dataset"))
    assert model.headerData(_column(model, "dataset"), Qt.Orientation.Horizontal, Qt.ItemDataRole.FontRole).italic()

    widget.clear_filters()
    widget.set_row_mask(frame["compound"].ne("PC 32:0").to_numpy())
    assert _top(model) == ["SM 34:1 (2)", "TG 50:1 (1)"]
    widget.set_row_mask(None)
    assert len(_top(model)) == 3
    with pytest.raises(ValueError, match="one value per"):
        widget.set_row_mask(np.ones(2, dtype=bool))


def test_numeric_filter_blank_handling(qtbot, frame) -> None:
    widget = _widget(qtbot, frame)
    widget.set_numeric_filter("fdr", maximum=0.1, include_blanks=False)
    assert widget.visible_count() == 3
    widget.set_numeric_filter("fdr", maximum=0.1, include_blanks=True)
    assert widget.visible_count() == 4
    assert widget.model.distinct_values_for_column(widget.model._column_index("dataset")) == ["kidney", "liver"]


def test_sorting_orders_groups_by_aggregate_and_leaves_within_groups(qtbot, frame) -> None:
    widget = _widget(qtbot, frame, group_by="compound", label_column="dataset", aggregations={"ppm": "max"})
    model = widget.model

    widget.set_sort("ppm", Qt.SortOrder.DescendingOrder)
    assert _top(model) == ["TG 50:1 (1)", "PC 32:0 (3)", "SM 34:1 (2)"]
    pc = model.index(1, 0)
    ppm = _column(model, "ppm")
    assert [model.data(model.index(row, ppm, pc)) for row in range(3)] == ["3.0000", "1.0000", "-2.0000"]
    assert model.headerData(ppm, Qt.Orientation.Horizontal).endswith("▼")

    widget.set_sort(TREE_COLUMN, Qt.SortOrder.DescendingOrder)
    assert _top(model)[0] == "TG 50:1 (1)"
    widget.clear_sorting()
    assert _top(model) == ["PC 32:0 (3)", "SM 34:1 (2)", "TG 50:1 (1)"]

    widget.show()
    header = widget.tree_view.header()
    position = QPoint(header.sectionViewportPosition(ppm) + header.sectionSize(ppm) // 2, header.height() // 2)
    qtbot.mouseClick(header.viewport(), Qt.MouseButton.LeftButton, pos=position)  # a real click sorts
    assert model.sort_column == model._column_index("ppm")
    assert model.sort_order == Qt.SortOrder.AscendingOrder
    qtbot.mouseClick(header.viewport(), Qt.MouseButton.LeftButton, pos=position)  # still clickable after refresh
    assert model.sort_order == Qt.SortOrder.DescendingOrder


def test_two_levels_and_flat_mode(qtbot, frame) -> None:
    widget = _widget(qtbot, frame, group_by=["compound", "adduct"], label_column="dataset")
    model = widget.model

    pc = model.index(0, 0)
    assert model.rowCount(pc) == 2
    assert model.data(model.index(0, 0, pc)) == "[M+H]+ (2)"
    assert model.rowCount(model.index(0, 0, pc)) == 2
    assert model.parent(model.index(0, 0, model.index(0, 0, pc))) == model.index(0, 0, pc)
    assert model.parent() is widget  # QObject parent still works

    widget.set_group_by(None)
    assert model.rowCount() == len(frame)
    assert not model.hasChildren(model.index(0, 0))
    assert model.is_column_visible(model._column_index("compound"))  # grouping column is shown again


def test_colors_for_leaves_and_groups(qtbot, frame) -> None:
    widget = _widget(qtbot, frame, group_by="compound")
    model = widget.model

    widget.color_numeric("ppm", vmin=-5, vmax=5, vcenter=0.0)
    leaf_colors = model.leaf_colors("ppm")
    group_colors = model.group_colors("ppm")
    assert leaf_colors.shape == (len(frame), 4)
    assert group_colors is not None
    pc = model.index(0, 0)
    ppm = _column(model, "ppm")
    assert model.data(model.index(0, ppm), Qt.ItemDataRole.BackgroundRole) is not None
    assert model.data(model.index(0, ppm, pc), Qt.ItemDataRole.BackgroundRole) is not None
    assert model.data(model.index(0, ppm, pc), Qt.ItemDataRole.ForegroundRole) is not None

    widget.color_categorical("dataset")
    assert model.leaf_colors("dataset")[0].tolist() != model.leaf_colors("dataset")[2].tolist()
    widget.clear_colors()
    assert model.leaf_colors("ppm") is None

    rgba = np.zeros((len(frame), 4), dtype=np.uint8)
    rgba[5] = (200, 0, 0, 255)
    model.set_row_background(rgba)
    tg = model.index(2, 0)
    assert model.data(model.index(0, 1, tg), Qt.ItemDataRole.BackgroundRole).color().red() == 200


def test_column_visibility(qtbot, frame) -> None:
    widget = _widget(qtbot, frame, group_by="compound")
    model = widget.model
    n_columns = model.columnCount()

    widget.set_column_visible("ppm", False)
    assert model.columnCount() == n_columns - 1
    widget.set_visible_columns(["fdr"])
    assert model.columnCount() == 2
    assert not model.set_column_visible("fdr", False)  # last column stays


def test_selection_maps_to_source_rows(qtbot, frame) -> None:
    widget = _widget(qtbot, frame, group_by="compound")
    seen = []
    widget.evt_current_changed.connect(seen.append)
    model = widget.model

    widget.tree_view.setCurrentIndex(model.index(0, 0))
    assert seen[-1].is_group
    assert seen[-1].group_key == ("PC 32:0",)
    assert seen[-1].source_rows.tolist() == [0, 1, 2]

    assert widget.select_source_row(4)
    assert seen[-1].source_row == 4
    assert widget.tree_view.isExpanded(model.index(1, 0))

    widget.tree_view.selectAll()
    assert sorted(widget.selected_source_rows().tolist()) == list(range(len(frame)))

    widget.set_numeric_filter("ppm", minimum=10)
    assert not widget.select_source_row(4)
    assert model.index_for_source_row(4) == QModelIndex()


def test_keyboard_navigation_emits_current(qtbot, frame) -> None:
    widget = _widget(qtbot, frame, group_by="compound")
    widget.show()
    seen = []
    widget.evt_current_changed.connect(seen.append)
    widget.tree_view.setCurrentIndex(widget.model.index(0, 0))
    qtbot.keyClick(widget.tree_view, Qt.Key.Key_Down)
    assert seen[-1].group_key == ("SM 34:1",)


def test_state_survives_refresh_and_set_data(qtbot, frame) -> None:
    widget = _widget(qtbot, frame, group_by="compound")
    model = widget.model
    widget.tree_view.expand(model.index(1, 0))
    widget.select_source_row(3)
    widget.set_sort("ppm", Qt.SortOrder.AscendingOrder)
    widget.color_numeric("ppm")

    widget.set_numeric_filter("fdr", maximum=0.3)
    sm = model.index(model.index_for_node(model.node_for_key(("SM 34:1",))).row(), 0)
    assert widget.tree_view.isExpanded(sm)
    assert widget.current_selection().source_row == 3

    widget.set_data(frame.assign(ppm=frame["ppm"] * 2))
    assert model.sort_column == model._column_index("ppm")
    assert model.is_column_filtered(model._column_index("fdr"))
    assert model.leaf_colors("ppm") is not None
    assert model.group_by == ["compound"]

    widget.set_data(pd.DataFrame({"other": [1, 2]}), keep_state=False)
    assert model.sort_column is None
    assert model.rowCount() == 2


def test_group_label_column_and_visible_dataframe(qtbot, frame) -> None:
    labelled = frame.assign(name=frame["compound"].str.replace(" ", "_"))
    widget = _widget(qtbot, labelled, group_by="compound", group_label_column="name")

    assert _top(widget.model)[0] == "PC_32:0 (3)"
    widget.set_numeric_filter("ppm", maximum=0)
    assert widget.visible_dataframe()["ppm"].tolist() == [-2.0, -0.5]


def test_auto_expand(qtbot, frame) -> None:
    widget = _widget(qtbot, frame, group_by="compound", auto_expand=5)
    assert widget.tree_view.isExpanded(widget.model.index(0, 0))


def test_large_frame_stays_responsive(qtbot) -> None:
    """Guard against pathological slowdowns (loose bound, not a benchmark)."""
    rng = np.random.default_rng(0)
    n_rows = 100_000
    df = pd.DataFrame(
        {
            "group": rng.integers(0, 5000, n_rows).astype(str),
            "value": rng.random(n_rows),
            "label": rng.choice(["a", "b", "c"], n_rows),
        }
    )
    start = time.perf_counter()
    widget = _widget(qtbot, df, group_by="group", aggregations={"value": "max"})
    widget.set_numeric_filter("value", minimum=0.5)
    widget.set_sort("value", Qt.SortOrder.DescendingOrder)
    elapsed = time.perf_counter() - start

    assert widget.visible_count() == int((df["value"] >= 0.5).sum())
    assert elapsed < 20


def test_set_data_group_by_none_means_flat(qtbot, frame) -> None:
    widget = _widget(qtbot, frame, group_by="compound")
    widget.set_data(frame)  # omitted: keep grouping
    assert widget.model.group_by == ["compound"]
    widget.set_data(frame, group_by=None)
    assert widget.model.group_by == []
    assert not widget.model.is_column_visible(widget.model._column_index("compound"))  # visibility kept


def test_log_color_scale(qtbot) -> None:
    df = pd.DataFrame({"g": ["a", "a", "b"], "intensity": [1e-4, 1e-1, 0.0]})
    widget = _widget(qtbot, df, group_by="g")
    widget.color_numeric("intensity", colormap="viridis", log=True)
    colors = widget.model.leaf_colors("intensity")
    assert colors[0].tolist() != colors[1].tolist()
    assert colors[2][3] == 0  # zero is undefined on a log scale
