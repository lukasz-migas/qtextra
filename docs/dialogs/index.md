# Dialogs

`qtextra` also includes a set of utility dialogs for common desktop application
flows such as confirmations, changelogs, system information, logging, and
embedded consoles.

For concrete usage patterns, browse the runnable examples in `examples/`,
especially:

- `dialog_changelog.py`
- `dialog_color_list.py`
- `dialog_confirm_close.py`
- `dialog_confirm_with_text.py`
- `dialog_theme_editor.py`
- `dialog_text_replace.py`
- `qt_console.py`
- `qt_logger.py`

The dialog pages are still sparse compared with the widget pages. Expanding
them is a good next contribution target.

## Documented Dialogs

- [Sentry Dialogs](./sentry.md): telemetry opt-in, crash reporting setup, and
  feedback environment variables

- [WhatsNewDialog](./qt_whats_new.md): multi-page release notes and feature-introduction dialog

- [UpdateAvailableDialog](./qt_update_available.md): update prompt with release-note and remind-later actions

- [DialogThemeEditor](./qt_theme_editor.md): live theme editor for colors,
  font sizes, and console styles
