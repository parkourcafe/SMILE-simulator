"""Shared test fixtures."""

from __future__ import annotations

import io

import pytest
from PIL import Image


@pytest.fixture
def selfie_bytes() -> bytes:
    """A synthetic 800x800 'face' image good enough to exercise the pipeline."""
    img = Image.new("RGB", (800, 800), (220, 190, 170))  # skin-ish
    # a darker mouth-ish region lower-center
    for x in range(300, 500):
        for y in range(560, 620):
            img.putpixel((x, y), (120, 60, 60))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
