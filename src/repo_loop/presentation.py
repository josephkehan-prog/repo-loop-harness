"""Safe rendering helpers for untrusted repository-derived text."""

from __future__ import annotations


def terminal_text(value: object) -> str:
    """Escape control characters before rendering repository data in a terminal."""
    rendered: list[str] = []
    for character in str(value):
        if character.isprintable():
            rendered.append(character)
            continue
        codepoint = ord(character)
        escape = f"\\x{codepoint:02x}" if codepoint <= 0xFF else f"\\u{codepoint:04x}"
        rendered.append(escape)
    return "".join(rendered)
