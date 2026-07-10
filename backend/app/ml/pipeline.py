"""End-to-end mouth-inpainting pipeline (architecture §5.1).

validate → normalize → face mesh → mouth mask → prompt → inference (provider) →
quality check → watermark (free tier) → return bytes + telemetry.

Storage/DB persistence is the caller's concern (see routers/generate.py); this module
is pure image+inference logic so it is easy to unit-test and reuse off the request path.
"""

from __future__ import annotations

from dataclasses import dataclass

from PIL import Image

from app.config import get_settings

from . import face_mesh, mask, photo, prompts
from .providers.base import ProviderConfig
from .providers.registry import get_provider


@dataclass
class PipelineOutput:
    result_image: bytes
    mask_image: bytes
    prompt: str
    provider: str
    cost_usd: float
    duration_ms: int
    quality_score: float
    face_approximate: bool
    request_id: str | None


def _quality_score(original: Image.Image, result: Image.Image, mask_img: Image.Image) -> float:
    """Cheap heuristic: how well is the face preserved OUTSIDE the mask region?

    Mean absolute pixel difference over non-mask pixels, mapped to a 1–5 scale. A
    well-behaved inpaint changes only the mouth, so non-mask diff should be tiny.
    This is a guardrail, not the human quality scorecard (CLAUDE.md → Quality Criteria).
    """
    try:
        import numpy as np
    except ImportError:  # pragma: no cover
        return 0.0

    a = np.asarray(original.convert("RGB"), dtype=np.float32)
    b = np.asarray(result.convert("RGB").resize(original.size), dtype=np.float32)
    m = np.asarray(mask_img.convert("L").resize(original.size), dtype=np.float32) / 255.0
    outside = 1.0 - m
    denom = outside.sum() * 3 + 1e-6
    diff = (np.abs(a - b).mean(axis=2) * outside).sum() / denom
    # diff 0 → 5.0 (perfect preservation), diff >= 40 → 1.0
    score = max(1.0, min(5.0, 5.0 - (diff / 40.0) * 4.0))
    return round(float(score), 1)


async def run_pipeline(
    *,
    photo_bytes: bytes,
    style_template: str,
    style_name: str,
    apply_watermark: bool,
    provider_name: str | None = None,
) -> PipelineOutput:
    settings = get_settings()
    size = settings.result_image_size

    # 1–2. validate (EXIF-corrected) then face-aware square crop to `size`
    original = photo.load_and_validate(photo_bytes)

    # 3–4. face mesh (detect + crop around the face) + mouth mask
    normalized, landmarks = face_mesh.detect_and_crop(original, size=size)
    mask_img = mask.build_mouth_mask(landmarks)
    mask_bytes = mask.mask_to_png_bytes(mask_img)

    # 5. prompt
    prompt = prompts.build_prompt(style_template, style_name=style_name)

    # 6. inference (behind provider abstraction)
    provider = get_provider(provider_name)
    config = ProviderConfig(image_size=size)
    gen = await provider.generate(
        image=photo.to_png_bytes(normalized),
        mask=mask_bytes,
        prompt=prompt,
        config=config,
    )

    # 7. quality check
    result_img = Image.open(__import__("io").BytesIO(gen.image)).convert("RGB")
    quality = _quality_score(normalized, result_img, mask_img)

    # 8. watermark (free tier)
    if apply_watermark:
        result_img = photo.add_watermark(result_img)

    return PipelineOutput(
        result_image=photo.to_png_bytes(result_img),
        mask_image=mask_bytes,
        prompt=prompt,
        provider=gen.provider,
        cost_usd=gen.cost_usd,
        duration_ms=gen.duration_ms,
        quality_score=quality,
        face_approximate=landmarks.approximate,
        request_id=gen.request_id,
    )
