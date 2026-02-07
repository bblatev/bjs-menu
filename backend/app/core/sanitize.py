"""Text sanitization utilities to prevent XSS attacks."""

import html


def sanitize_text(value: str | None) -> str | None:
    """Sanitize user-supplied text to prevent stored XSS.

    HTML-escapes dangerous characters (&, <, >, ", ') so that
    user input is safe to render in a browser without being
    interpreted as HTML/JavaScript.

    Use on all user-supplied text fields that will be rendered in a browser.
    """
    if value is None:
        return None
    return html.escape(value, quote=True)
