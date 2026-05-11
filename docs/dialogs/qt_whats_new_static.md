# WhatsNewStaticDialog

Static release notes dialog inspired by PyCharm's "What's New" page.

## Example

Source: `examples/dialog_whats_new_static.py`

{{ include_example('dialog_whats_new_static.py') }}

## Notes

- Use `WhatsNewStaticContent` to define the app name, version, highlights, optional video, and optional call-to-action.
- Use `WhatsNewHighlight` entries for the image, title, and subtitle shown in each tile.
- Use `WhatsNewVideo` when the release has a video tour image and optional URL.

## API

{{ show_members('qtextra.dialogs.qt_whats_new_static.QtWhatsNewStaticDialog') }}

{{ show_members('qtextra.dialogs.qt_whats_new_static.QtWhatsNewStaticWidget') }}

{{ show_members('qtextra.dialogs.qt_whats_new_static.WhatsNewStaticContent') }}

{{ show_members('qtextra.dialogs.qt_whats_new_static.WhatsNewHighlight') }}

{{ show_members('qtextra.dialogs.qt_whats_new_static.WhatsNewVideo') }}
