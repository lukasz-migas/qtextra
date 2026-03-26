# Mixins

`qtextra.mixins` collects reusable behavior blocks that are shared by dialogs,
popups, and other composite widgets.

The module currently focuses on:

- documentation and help buttons
- configuration hydration guards
- periodic and one-shot timers
- notification helpers
- minimize, close, and drag-and-drop behaviors

## Common Mixins

- `DocumentationMixin`: adds tutorial and help-button layouts and resolves local
  `docs/...` links into file URIs.
- `ConfigMixin`: wraps configuration application so widgets can suppress
  side-effects while state is being restored.
- `TimerMixin`: creates widget-owned timers and exposes a small timing context
  manager.
- `IndicatorMixin`: emits the global toast, message, and notification signals
  used elsewhere in the library.

## Notes

- `ConfigMixin.setting_config()` restores its internal guard flag even if
  applying configuration raises an exception.
- `TimerMixin._add_single_shot_timer()` returns a real one-shot `QTimer`
  instance that stays owned by the widget.
