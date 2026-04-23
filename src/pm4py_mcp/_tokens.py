"""Token-count estimation for abstraction payloads.

Kept in its own module so the heuristic can be swapped for a real tokenizer
(``tiktoken`` / ``anthropic-tokenizer``) in a single edit later. A char÷4
approximation is widely used for English / code-heavy text and avoids adding
a new runtime dependency.
"""

from __future__ import annotations

_CHARS_PER_TOKEN = 4


def estimate_tokens(text: str) -> int:
    """Approximate token count. Returns 0 for empty strings."""
    if not text:
        return 0
    return max(1, len(text) // _CHARS_PER_TOKEN)
