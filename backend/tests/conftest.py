"""Shared test fixtures."""

from __future__ import annotations

import io
import os

import pytest
from PIL import Image

# Tests use synthetic (non-face) images to exercise mask geometry and the pipeline.
# Force the approximate mouth path by pointing the model env at a missing file, so
# results are deterministic whether or not MediaPipe + the model bundle are installed
# locally. (CI doesn't install the `ml` extra, so it already takes this path.)
os.environ["MEDIAPIPE_FACE_MODEL"] = "/nonexistent/face_landmarker.task"


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
