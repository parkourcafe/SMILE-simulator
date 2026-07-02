"""Mouth mask generation from lip landmarks (architecture §5.3).

Strategy: fill the outer lip contour white on black → dilate 15–20px → Gaussian blur
(sigma 5–8) for a feathered edge. Feathering is critical: sharp mask edges produce a
visible "pasted-in" boundary that destroys user trust.

Implemented with Pillow only (no hard OpenCV dependency): dilation via ``MaxFilter``,
feathering via ``GaussianBlur``.
"""

from __future__ import annotations

from PIL import Image, ImageDraw, ImageFilter

from .face_mesh import MouthLandmarks

DILATE_PX = 18  # architecture: 15–20px
FEATHER_SIGMA = 6  # architecture: 5–8


def build_mouth_mask(landmarks: MouthLandmarks) -> Image.Image:
    """Return an 8-bit grayscale mask (white = inpaint region) at image resolution."""
    mask = Image.new("L", (landmarks.width, landmarks.height), 0)
    draw = ImageDraw.Draw(mask)
    if len(landmarks.outer) >= 3:
        draw.polygon(landmarks.outer, fill=255)

    # Dilate: MaxFilter kernel must be odd; approximate the px radius.
    kernel = max(3, (DILATE_PX // 2) * 2 + 1)
    mask = mask.filter(ImageFilter.MaxFilter(size=min(kernel, 25)))

    # Feathered edge.
    mask = mask.filter(ImageFilter.GaussianBlur(radius=FEATHER_SIGMA))
    return mask


def mask_to_png_bytes(mask: Image.Image) -> bytes:
    import io

    buf = io.BytesIO()
    mask.save(buf, format="PNG")
    return buf.getvalue()
