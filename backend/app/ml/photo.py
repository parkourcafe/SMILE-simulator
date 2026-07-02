"""Photo validation, normalization, and watermarking (Pillow). Architecture §5.1."""

from __future__ import annotations

import io

from PIL import Image, ImageDraw, ImageFont, ImageOps

MIN_DIMENSION = 512
MAX_DIMENSION = 4096
MAX_FILE_BYTES = 10 * 1024 * 1024  # 10 MB
ACCEPTED_FORMATS = {"JPEG", "PNG", "WEBP", "HEIF", "HEIC", "MPO"}


class PhotoValidationError(ValueError):
    """Raised when an uploaded photo fails validation (maps to HTTP 422)."""


def load_and_validate(data: bytes) -> Image.Image:
    """Validate format/size/dimensions and return an RGB image."""
    if len(data) > MAX_FILE_BYTES:
        raise PhotoValidationError("file_too_large")
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except Exception as exc:  # noqa: BLE001 - any decode failure is a bad upload
        raise PhotoValidationError("unreadable_image") from exc
    if img.format and img.format.upper() not in ACCEPTED_FORMATS:
        raise PhotoValidationError("unsupported_format")
    # Honour EXIF orientation — phone photos are often stored rotated with an
    # orientation tag; without this the face is sideways and detection fails.
    img = ImageOps.exif_transpose(img)
    w, h = img.size
    if min(w, h) < MIN_DIMENSION:
        raise PhotoValidationError("too_small")
    if max(w, h) > MAX_DIMENSION:
        raise PhotoValidationError("too_large_dimensions")
    return img.convert("RGB")


def normalize(img: Image.Image, *, size: int = 1024) -> Image.Image:
    """Center-crop to a square and resize to ``size`` x ``size`` (architecture §5.1)."""
    w, h = img.size
    side = min(w, h)
    left = (w - side) // 2
    top = (h - side) // 2
    square = img.crop((left, top, left + side, top + side))
    return square.resize((size, size), Image.LANCZOS)


def to_png_bytes(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def add_watermark(img: Image.Image, text: str = "AI Smile Simulator") -> Image.Image:
    """Semi-transparent diagonal watermark for free-tier results (cannot be cropped out)."""
    base = img.convert("RGBA")
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", size=base.width // 18)
    except OSError:
        font = ImageFont.load_default()

    # Tile the text diagonally so it covers the whole image.
    step = base.width // 3
    for y in range(-base.height, base.height * 2, step):
        for x in range(-base.width, base.width * 2, step * 2):
            draw.text((x, y), text, font=font, fill=(255, 255, 255, 70))

    watermark = overlay.rotate(30, expand=False)
    return Image.alpha_composite(base, watermark).convert("RGB")
