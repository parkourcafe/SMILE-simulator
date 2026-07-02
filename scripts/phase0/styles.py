"""The four launch styles, mirrored from CLAUDE.md / migration 0003 so the Phase 0
spike runner is self-contained (no database needed)."""

from __future__ import annotations

STYLES: dict[str, str] = {
    "natural_white": (
        "Beautiful naturally white teeth, slight improvement in alignment, "
        "same lip shape and skin tone, photorealistic, maintain original lighting and shadows"
    ),
    "straight_smile": (
        "Perfectly aligned straight teeth, natural white shade, no gaps, same lip shape, "
        "photorealistic dental result, maintain skin texture"
    ),
    "veneer_effect": (
        "Professional dental veneer result, uniform tooth shape and size, "
        "bright white but natural-looking, celebrity-quality smile, same lip contour"
    ),
    "hollywood_smile": (
        "Brilliant white Hollywood smile, perfect symmetry, gleaming teeth, "
        "red carpet ready, maintain natural lip shape and facial features"
    ),
}
