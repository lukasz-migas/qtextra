"""Help utilities for displaying messages in HTML format."""

import typing as ty

COLORS = {
    "error": "#ff121e",
    "warning": "#ff693c",
    "check_warning": "#ff693c",
    "success": "#1ed75f",
    "check": "#1ed75f",
    "normal": "#777777",
    "hint": "#00a6ff",
}


def _make_message(
    kind: ty.Literal["error", "warning", "success", "normal", "hint"],
    message: str,
    small: bool = False,
    medium: bool = False,
    large: bool = False,
    add_icon: bool = False,
    add_dash: bool = True,
) -> str:
    """Returns HTML formatted message."""
    color = COLORS[kind]
    if add_icon:
        icon = {"error": "🔴", "warning": "🟠", "success": "🟢", "normal": "🟡", "hint": "🔵"}[kind]
        message = f"{icon} {message}"
    if add_dash:
        message = f"— {message}" if not message.startswith("—") else message
    if small:
        return f'<span class="{kind}" style="color: {color}; font-size: 10px">{message}</span>'
    if medium:
        return f'<span class="{kind}" style="color: {color}; font-size: 14px">{message}</span>'
    if large:
        return f'<span class="{kind}" style="color: {color}; font-size: 18px">{message}</span>'
    return f'<span class="{kind}" style="color: {color}">{message}</span>'


def sort_errors(errors: list[str]) -> list[str]:
    """Sort errors with the order: 'hints', 'errors', 'warnings'."""
    errors = errors or []
    return sorted(
        errors, key=lambda x: ('class="hint"' in x, 'class="error"' in x, 'class="warning"' in x), reverse=True
    )


def get_icon_state(errors: list[str]) -> tuple[str, str]:
    """Return icon state based on the error messages."""
    state = "check"
    for error in errors:
        if 'class="error"' in error:
            state = "error"
            break
        if 'class="warning"' in error:
            state = "warning"
            break
    return state, COLORS[state]
