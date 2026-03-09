"""macOS desktop notifications via osascript."""

from __future__ import annotations

import subprocess


def notify(title: str, message: str) -> None:
    """Send a macOS desktop notification with a sound."""
    # Escape double quotes in the message to avoid osascript errors
    safe_title = title.replace('"', '\\"')
    safe_message = message.replace('"', '\\"')
    script = (
        f'display notification "{safe_message}" '
        f'with title "{safe_title}" sound name "Glass"'
    )
    subprocess.run(["osascript", "-e", script], check=False)
