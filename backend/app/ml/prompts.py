"""Prompt construction from a style template (architecture §5.2).

The ``prompt_template`` stored on the ``styles`` row may either be a complete prompt
or contain ``{style}`` / other ``{variables}`` to interpolate. We always append a
short safety suffix reinforcing "modify teeth only, preserve everything else" — the
single most important instruction for clean inpainting.
"""

from __future__ import annotations

import string

# Reinforces the inpainting contract regardless of style wording.
SAFETY_SUFFIX = (
    "photorealistic, modify only the teeth inside the mouth, "
    "preserve original lip shape, skin tone, lighting and facial features"
)


class _SafeDict(dict):
    """Leave unknown {placeholders} untouched instead of raising KeyError."""

    def __missing__(self, key: str) -> str:  # pragma: no cover - trivial
        return "{" + key + "}"


def build_prompt(template: str, *, style_name: str | None = None, **variables: str) -> str:
    """Render a style template into the final prompt sent to the provider."""
    ctx = _SafeDict(style=style_name or "", **variables)
    try:
        rendered = string.Formatter().vformat(template, (), ctx).strip()
    except (ValueError, IndexError):
        # Malformed template — fall back to the raw text rather than failing the job.
        rendered = template.strip()

    lowered = rendered.lower()
    if "photorealistic" in lowered and "preserve" in lowered:
        return rendered  # template already carries the safety language
    return f"{rendered}, {SAFETY_SUFFIX}"
