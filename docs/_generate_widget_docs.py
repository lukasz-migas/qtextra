from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent


@dataclass(frozen=True)
class WidgetDoc:
    slug: str
    title: str
    section: str
    summary: str
    example: str
    classes: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()
    screenshot_path: str = ""
    screenshot_width: int = 520


DOCS = Path(__file__).resolve().parent
WIDGET_DOCS = DOCS / "widgets"

CATALOG: tuple[WidgetDoc, ...] = (
    WidgetDoc(
        slug="qt_active_overlay",
        title="QtActiveOverlay",
        section="Progress And Status",
        summary="Animated busy indicators for lightweight in-place activity feedback.",
        example="qt_active_overlay.py",
        classes=(
            "qtextra.widgets.qt_active_overlay.QtActiveOverlay",
            "qtextra.widgets.qt_active_overlay.QtActiveWidget",
        ),
        notes=(
            "Use `QtActiveOverlay` for a compact inline animated indicator made of dots.",
            "Use `QtActiveWidget` when you want a larger spinner or loading illustration with text.",
        ),
        screenshot_width=460,
    ),
    WidgetDoc(
        slug="qt_button",
        title="QtPushButton (variants)",
        section="Actions And Buttons",
        summary="Theme-aware push buttons with activity and rich-text display helpers.",
        example="qt_button.py",
        classes=(
            "qtextra.widgets.qt_button.QtPushButton",
            "qtextra.widgets.qt_button.QtActivePushButton",
            "qtextra.widgets.qt_button.QtRichTextButton",
        ),
        notes=(
            "Use `QtActivePushButton` when a click should immediately communicate background activity.",
            "Use `QtRichTextButton` when button text needs inline emphasis or multiple styles.",
        ),
    ),
    WidgetDoc(
        slug="qt_button_icon",
        title="QtIconButtons",
        section="Actions And Buttons",
        summary="A family of icon buttons for toggles, state indicators, and common toolbar actions.",
        example="qt_button_icon.py",
        classes=(
            "qtextra.widgets.qt_button_icon.QtImagePushButton",
            "qtextra.widgets.qt_button_icon.QtTogglePushButton",
            "qtextra.widgets.qt_button_icon.QtStateButton",
            "qtextra.widgets.qt_button_icon.QtPriorityButton",
        ),
        notes=(
            "Single-state variants swap between two related icons when toggled.",
            "Stateful variants such as `QtStateButton` cycle through multiple semantic states.",
        ),
        screenshot_width=720,
    ),
    WidgetDoc(
        slug="qt_button_progress",
        title="QtActiveProgressBarButton",
        section="Progress And Status",
        summary="A button that pairs a progress bar with inline activity and cancel affordances.",
        example="qt_button_progress.py",
        classes=("qtextra.widgets.qt_button_progress.QtActiveProgressBarButton",),
        notes=("Use it when you want the action trigger and the progress readout to stay visually connected.",),
        screenshot_width=360,
    ),
    WidgetDoc(
        slug="qt_button_tag",
        title="QtTagManager",
        section="Selection And Input",
        summary="Interactive tag chips with filtering and add/remove affordances.",
        example="qt_button_tag.py",
        classes=(
            "qtextra.widgets.qt_button_tag.QtTagButton",
            "qtextra.widgets.qt_button_tag.QtTagManager",
        ),
        notes=("This pattern works well for faceted search, label editors, and small state pickers.",),
    ),
    WidgetDoc(
        slug="qt_collapsible",
        title="QtCheckCollapsible",
        section="Disclosure And Layout",
        summary="A `superqt.QCollapsible` variant with checkbox, action button, and warning state in the header.",
        example="qt_collapsible.py",
        classes=("qtextra.widgets.qt_collapsible.QtCheckCollapsible",),
        notes=(
            "The content area uses a `QFormLayout`, so `addRow` works naturally for form-style panels.",
            "Header controls can be shown or hidden independently depending on the workflow.",
        ),
        screenshot_width=360,
    ),
    WidgetDoc(
        slug="qt_combobox_color",
        title="QtColorSwatchComboBox",
        section="Selection And Input",
        summary="A combobox that presents a grid of named color swatches.",
        example="qt_combobox_color.py",
        classes=("qtextra.widgets.qt_combobox_color.QtColorSwatchComboBox",),
        notes=("Useful for compact palette pickers and theme configuration panels.",),
        screenshot_width=420,
    ),
    WidgetDoc(
        slug="qt_combobox_multi",
        title="QtMultiSelectComboBox",
        section="Selection And Input",
        summary="A multi-select combobox that renders the current selection as inline chips.",
        example="qt_combobox_multi.py",
        classes=("qtextra.widgets.qt_combobox_multi.QtMultiSelectComboBox",),
        notes=("The popup includes built-in search for longer option lists.",),
        screenshot_width=520,
    ),
    WidgetDoc(
        slug="qt_combobox_search",
        title="Qt Search Comboboxes",
        section="Selection And Input",
        summary="Search-first combobox variants for inline filtering and type-ahead selection.",
        example="qt_combobox_search.py",
        classes=(
            "qtextra.widgets.qt_combobox_search.QtSearchComboBox",
            "qtextra.widgets.qt_combobox_search.QtSearchableComboBox",
        ),
        notes=(
            "`QtSearchComboBox` uses a custom popup panel with its own search field.",
            "`QtSearchableComboBox` extends `QComboBox` with completer-based filtering.",
        ),
        screenshot_width=520,
    ),
    WidgetDoc(
        slug="qt_dict_tag_editor",
        title="QtDictTagEditor",
        section="Data Editors",
        summary="Editable key-value tables for small dictionaries with search and typed values.",
        example="qt_dict_tag_editor.py",
        classes=("qtextra.widgets.qt_dict_tag_editor.QtDictTagEditor",),
        notes=("Useful for settings panels and metadata editors where the shape is small and dynamic.",),
        screenshot_width=620,
    ),
    WidgetDoc(
        slug="qt_dict_tag_viewer",
        title="QtDictTagViewer",
        section="Data Editors",
        summary="A read-only searchable dictionary viewer for compact metadata tables.",
        example="qt_dict_tag_viewer.py",
        classes=("qtextra.widgets.qt_dict_tag_viewer.QtDictTagViewer",),
        notes=("Pairs well with the editor variant when you need separate edit and inspect modes.",),
        screenshot_width=620,
    ),
    WidgetDoc(
        slug="qt_filter_edit",
        title="QtFilterEdit",
        section="Selection And Input",
        summary="Filter-token entry widgets for building simple search and match expressions.",
        example="qt_filter_edit.py",
        classes=("qtextra.widgets.qt_filter_edit.QtFilterEdit",),
        notes=("Supports standard stacked layout, above-input controls, flow layouts, and an AND/OR mode switch.",),
        screenshot_width=620,
    ),
    WidgetDoc(
        slug="qt_progress_bar_floating",
        title="QtFloatingProgressBar",
        section="Progress And Status",
        summary="A floating progress overlay that stays anchored to a window, dialog, or child widget.",
        example="qt_progress_bar_floating.py",
        classes=("qtextra.widgets.qt_progress_bar_floating.QtFloatingProgressBar",),
        notes=(
            "Use busy mode when total progress is unknown and determinate mode when you have a concrete range.",
            "Attach it to either a child content widget or directly to a top-level dialog or main window.",
        ),
        screenshot_width=620,
    ),
    WidgetDoc(
        slug="qt_label_icon",
        title="QtQtaLabel (variants)",
        section="Labels And Display",
        summary="Theme-aware static and animated icon labels built on QtAwesome mappings.",
        example="qt_label_icon.py",
        classes=(
            "qtextra.widgets.qt_label_icon.QtQtaLabel",
            "qtextra.widgets.qt_label_icon.QtPulsingAttentionLabel",
            "qtextra.widgets.qt_label_icon.QtWarningPulseLabel",
        ),
        notes=(
            "Use static labels for status icons and pulsing labels when something needs attention without a full dialog.",
        ),
        screenshot_width=760,
    ),
    WidgetDoc(
        slug="qt_label_read_more",
        title="QReadMoreLessLabel",
        section="Labels And Display",
        summary="Rich text that can stay compact by default and expand into a two-column explanation when needed.",
        example="",
        classes=("qtextra.widgets.qt_label_read_more.QReadMoreLessLabel",),
        notes=(
            "Use `<moreless>` to enable the collapsed preview mode.",
            "Use `<split>` to divide the expanded content into left and right areas.",
        ),
        screenshot_width=520,
    ),
    WidgetDoc(
        slug="qt_label_scroll",
        title="QtScrollableLabel",
        section="Labels And Display",
        summary="Scrollable rich text labels for longer explanations inside constrained layouts.",
        example="qt_label_scroll.py",
        classes=("qtextra.widgets.qt_label_scroll.QtScrollableLabel",),
    ),
    WidgetDoc(
        slug="qt_multi_dict_tag_editor",
        title="QtMultiDictTagEditor",
        section="Data Editors",
        summary="Edit multiple named dictionaries together with an aggregate summary view.",
        example="qt_multi_dict_tag_editor.py",
        classes=(
            "qtextra.widgets.qt_multi_dict_tag_editor.QtMultiDictTagEditor",
            "qtextra.widgets.qt_multi_dict_summary.QtMultiDictSummaryWidget",
        ),
        notes=("Useful when multiple samples or records share similar metadata fields.",),
        screenshot_width=760,
    ),
    WidgetDoc(
        slug="qt_multi_dict_tag_viewer",
        title="QtMultiDictTagViewer",
        section="Data Editors",
        summary="Read-only multi-record dictionary viewing with a synchronized summary widget.",
        example="qt_multi_dict_tag_viewer.py",
        classes=(
            "qtextra.widgets.qt_multi_dict_tag_viewer.QtMultiDictTagViewer",
            "qtextra.widgets.qt_multi_dict_summary.QtMultiDictSummaryWidget",
        ),
        screenshot_width=760,
    ),
    WidgetDoc(
        slug="qt_notification_badge",
        title="QtNotificationBadge",
        section="Progress And Status",
        summary="Attach count and dot badges to existing widgets without changing their layout.",
        example="qt_notification_badge.py",
        classes=("qtextra.widgets.qt_notification_badge.QtNotificationBadge",),
        notes=("Badges work with standard Qt widgets as well as qtextra-specific labels and buttons.",),
        screenshot_width=760,
    ),
    WidgetDoc(
        slug="qt_overlay",
        title="QtOverlay",
        section="Progress And Status",
        summary="Floating labels and message widgets anchored to another widget.",
        example="qt_overlay.py",
        classes=(
            "qtextra.widgets.qt_overlay.QtOverlay",
            "qtextra.widgets.qt_overlay.QtOverlayLabel",
            "qtextra.widgets.qt_overlay.QtOverlayMessage",
            "qtextra.widgets.qt_overlay.QtOverlayDismissMessage",
        ),
        notes=("Overlays automatically follow the anchor widget as it moves, resizes, shows, or hides.",),
        screenshot_width=560,
    ),
    WidgetDoc(
        slug="qt_popout",
        title="QtPopout",
        section="Feedback And Teaching",
        summary="Contextual popouts that point back to a target widget.",
        example="qt_popout.py",
        classes=("qtextra.widgets.qt_popout.QtPopout",),
        notes=("Use popouts for contextual explanations that should stay near the triggering control.",),
        screenshot_width=620,
    ),
    WidgetDoc(
        slug="qt_progress_report",
        title="QtProgressReport",
        section="Progress And Status",
        summary="Vertical progress report with labelled circle markers and typed step models.",
        example="qt_progress_report.py",
        classes=(
            "qtextra.widgets.qt_progress_report.ProgressStepStatus",
            "qtextra.widgets.qt_progress_report.ProgressReportStep",
            "qtextra.widgets.qt_progress_report.QtProgressReport",
        ),
        screenshot_width=560,
    ),
    WidgetDoc(
        slug="qt_progress_step",
        title="QtStepProgressBar",
        section="Progress And Status",
        summary="Step-based progress visualization for multi-stage workflows.",
        example="qt_progress_step.py",
        classes=("qtextra.widgets.qt_progress_step.QtStepProgressBar",),
        screenshot_width=480,
    ),
    WidgetDoc(
        slug="qt_search_panel",
        title="QtSearchPanel",
        section="Selection And Input",
        summary="Reusable search and replace panel for text editors and plain-text views.",
        example="qt_search_panel.py",
        classes=("qtextra.widgets.qt_text_search.QtSearchPanel",),
        notes=("This widget is a good default when you want shared editor search behavior across the app.",),
        screenshot_width=680,
    ),
    WidgetDoc(
        slug="qt_system_summary",
        title="QtSystemSummaryWidget",
        section="Progress And Status",
        summary="A compact system summary widget for application and runtime metadata.",
        example="qt_system_summary.py",
        classes=("qtextra.widgets.qt_system_summary.QtSystemSummaryWidget",),
        screenshot_width=540,
    ),
    WidgetDoc(
        slug="qt_table_view_array",
        title="QtArrayTableView",
        section="Data Editors",
        summary="High-volume array tables with sorting, lazy row loading, and optional colormap rendering.",
        example="qt_table_view_array.py",
        classes=(
            "qtextra.widgets.qt_table_view_array.QtRotatedHeaderView",
            "qtextra.widgets.qt_table_view_array.QtArrayTableModel",
            "qtextra.widgets.qt_table_view_array.QtArrayTableView",
        ),
        notes=("Designed for large numpy or pandas-backed numeric tables.",),
        screenshot_width=760,
    ),
    WidgetDoc(
        slug="qt_table_view_dataframe",
        title="QtDataFrameWidget",
        section="Data Editors",
        summary="A dataframe viewer with synchronized headers and support for pandas and polars inputs.",
        example="qt_table_view_dataframe.py",
        classes=("qtextra.widgets.qt_table_view_dataframe.QtDataFrameWidget",),
        notes=("Good for inspection tools, debug panels, and tabular previews in desktop apps.",),
        screenshot_width=820,
    ),
    WidgetDoc(
        slug="qt_tag_editor",
        title="QtTagEditor",
        section="Selection And Input",
        summary="A lightweight tag entry widget for adding, removing, and deduplicating short labels.",
        example="qt_tag_editor.py",
        classes=("qtextra.widgets.qt_tag_editor.QtTagEditor",),
        notes=("Supports both flow and horizontally scrollable layouts depending on available space.",),
        screenshot_width=520,
    ),
    WidgetDoc(
        slug="qt_toggle_group",
        title="QtToggleGroup",
        section="Selection And Input",
        summary="Compact grouped toggle buttons with exclusive and multi-select modes.",
        example="qt_toggle_group.py",
        classes=("qtextra.widgets.qt_toggle_group.QtToggleGroup",),
        notes=(
            "Read the current selection from `value` and the current position from `index`.",
            "Use `from_schema` when a JSON-style schema already describes the options.",
        ),
        screenshot_width=520,
    ),
    WidgetDoc(
        slug="qt_toolbar_panel",
        title="QtPanelToolbar",
        section="Actions And Buttons",
        summary="A vertical toolbar that toggles stacked panels, with optional labelled buttons.",
        example="qt_toolbar_panel.py",
        classes=(
            "qtextra.widgets.qt_toolbar_panel.QtPanelToolbar",
            "qtextra.widgets.qt_toolbar_panel.QtPanelWidget",
        ),
        notes=(
            "Use `title=` to create labelled toolbar buttons and `elide=False` when the full label should widen the toolbar.",
            "Set `label_hidden` at runtime to switch between icon-only and labelled layouts.",
        ),
        screenshot_width=620,
    ),
    WidgetDoc(
        slug="qt_toolbar_mini",
        title="QtMiniToolbar",
        section="Actions And Buttons",
        summary="A dense icon-toolbar widget for compact utility actions.",
        example="qt_toolbar_mini.py",
        classes=("qtextra.widgets.qt_toolbar_mini.QtMiniToolbar",),
        notes=("Supports horizontal and vertical layouts, separators, spacers, and inserted tools.",),
        screenshot_width=560,
    ),
    WidgetDoc(
        slug="qt_tooltip",
        title="QtToolTip",
        section="Feedback And Teaching",
        summary="Custom tooltip bubbles with tail positions, optional images, and styled content.",
        example="qt_tooltip.py",
        classes=(
            "qtextra.widgets.qt_tooltip.QtToolTip",
            "qtextra.widgets.qt_tooltip.TipPosition",
        ),
        screenshot_width=620,
        screenshot_path="../assets/qt_tooltip_rich.jpg",
    ),
    WidgetDoc(
        slug="qt_tutorial",
        title="QtTutorial",
        section="Feedback And Teaching",
        summary="Guided tutorial overlays that walk the user through a sequence of widgets.",
        example="qt_tutorial.py",
        classes=(
            "qtextra.widgets.qt_tutorial.QtTutorial",
            "qtextra.widgets.qt_tutorial.TutorialStep",
            "qtextra.widgets.qt_tutorial.Position",
        ),
        notes=("Tutorial steps point at target widgets and can place the callout in many relative positions.",),
        screenshot_width=620,
    ),
)


def render_page(item: WidgetDoc) -> str:
    summary = f"# {item.title}\n\n{item.summary}\n"

    if item.screenshot_path:
        screenshot_block = _render_screenshot_path(item)
    elif item.example:
        screenshot_block = f"{{{{ show_example('{item.example}', {item.screenshot_width}) }}}}"
    else:
        screenshot_block = f"{{{{ show_widget({item.screenshot_width}) }}}}"

    example_block = dedent(
        f"""
        ## Screenshot

        {screenshot_block}
        """,
    ).strip()

    if item.example:
        example_block += (
            dedent(
                f"""

                ## Example

                Source: `examples/{item.example}`

                {{{{ include_example('{item.example}') }}}}
                """,
            ).rstrip()
        )

    notes_block = ""
    if item.notes:
        notes = "\n".join(f"- {note}" for note in item.notes)
        notes_block = f"\n## Notes\n\n{notes}\n"

    api_block = ""
    if item.classes:
        api = "\n\n".join(f"{{{{ show_members('{cls}') }}}}" for cls in item.classes)
        api_block = f"\n## API\n\n{api}\n"

    return f"{summary}\n{example_block}{notes_block}{api_block}"


def _render_screenshot_path(item: WidgetDoc) -> str:
    screenshot_path = item.screenshot_path.strip()
    if screenshot_path.startswith("!["):
        return screenshot_path
    return f"![screenshot]({screenshot_path}){{ loading=lazy; width={item.screenshot_width} }}"


def render_index(items: tuple[WidgetDoc, ...]) -> str:
    grouped: dict[str, list[WidgetDoc]] = defaultdict(list)
    for item in items:
        grouped[item.section].append(item)

    sections = []
    for section in sorted(grouped):
        body = "\n".join(
            f"- [{item.title}](./{item.slug}.md): {item.summary[0].lower() + item.summary[1:]}"
            for item in sorted(grouped[section], key=lambda entry: entry.title.lower())
        )
        sections.append(f"## {section}\n\n{body}")

    joined_sections = "\n\n".join(sections)
    return (
        "# Widgets\n\n"
        "The widget docs now pull runnable examples directly from the repository and build screenshots from those same\n"
        "example files. That keeps the examples, images, and API notes aligned.\n\n"
        "Browse by capability below, then open the individual pages for screenshots, runnable code, and API references.\n\n"
        f"{joined_sections}\n"
    )


def main() -> None:
    WIDGET_DOCS.mkdir(exist_ok=True, parents=True)
    for item in CATALOG:
        if item.slug == "qt_label_read_more":
            continue
        (WIDGET_DOCS / f"{item.slug}.md").write_text(render_page(item), encoding="utf-8")

    # Keep the read-more page hand-authored because it does not yet have a dedicated example script.
    (WIDGET_DOCS / "index.md").write_text(render_index(CATALOG), encoding="utf-8")


if __name__ == "__main__":
    main()
