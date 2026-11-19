# QtSettingsDialog

A searchable settings dialog: a search box above an icon sidebar, a large page title and one row per setting with the
label on the left and the control on the right.

## Example

Source: `examples/dialog_settings.py`

{{ include_example('dialog_settings.py') }}

## Notes

- Subclass `QtSettingsDialog` and implement `make_pages`, calling `add_page(title, icon)` for each category.
- `QtSettingsPage.add_section` starts a titled group; `add_row(title, widget_or_layout, tooltip=..., keywords=...)`
  adds a setting. Pass an empty title to let the control span the whole row (e.g. a note).
- Search matches the page title, section titles, row labels, tooltips and `keywords`. Pages without matches are hidden
  from the sidebar and a "No settings match" message is shown when nothing matches. `Ctrl+F` focuses the search box.
- Add extra buttons to `sidebar_footer_layout` (below the sidebar) or `content_footer_layout` (below the page).
- Sidebar icons are re-colored when the theme changes.

## API

{{ show_members('qtextra.dialogs.qt_settings.QtSettingsDialog') }}

{{ show_members('qtextra.dialogs.qt_settings.QtSettingsPage') }}
