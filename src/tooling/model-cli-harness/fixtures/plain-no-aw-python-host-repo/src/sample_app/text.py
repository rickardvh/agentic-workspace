"""Text helper functions for examples and tests."""

import re


def summarize_words(text: str, *, limit: int = 12) -> str:
    """Return the first words from text, with an ellipsis when truncated."""
    words = text.split()
    if len(words) <= limit:
        return " ".join(words)
    return " ".join(words[:limit]) + "..."


def to_slug(text: str) -> str:
    """Return a lowercase slug for a title."""
    lowered = text.lower().strip()
    normalized = re.sub(r"[^a-z0-9\s-]", "", lowered)
    return normalized.replace(" ", "-")
