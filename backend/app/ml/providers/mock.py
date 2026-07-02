"""MockProvider — deterministic offline inpainting stand-in (v1.1).

Default provider when ``MOCK_INFERENCE=true`` (see config) so the whole product
runs, and the e2e generation journey works, with zero external credentials and no
cost. It does NOT call any network service.

Output is deterministic for a given (image, mask): the masked mouth region is
brightened/whitened (a crude "whiter teeth" cue so before/after is visibly
different) and a small "MOCK" tag is stamped in the corner so nobody mistakes a
mock result for a real Fal.ai generation.
"""

from __future__ import annotations

import io

from PIL import Image, ImageDraw, ImageFont

from .base import GenerationResult, InferenceProvider, ProviderConfig

# Fixed, non-zero so telemetry/plots look realistic; cost stays 0 (no real spend).
MOCK_DURATION_MS = 1200


class MockProvider(InferenceProvider):
    name = "mock"

    async def generate(
        self,
        *,
        image: bytes,
        mask: bytes,
        prompt: str,
        config: ProviderConfig,
    ) -> GenerationResult:
        base = Image.open(io.BytesIO(image)).convert("RGB")
        mask_l = Image.open(io.BytesIO(mask)).convert("L").resize(base.size)

        # Whiten + brighten the masked mouth region: blend toward near-white using
        # the mask as alpha. Deterministic — no randomness.
        whitened = Image.new("RGB", base.size, (245, 246, 240))
        result = Image.composite(whitened, base, mask_l.point(lambda p: int(p * 0.7)))

        draw = ImageDraw.Draw(result)
        try:
            font = ImageFont.truetype("DejaVuSans-Bold.ttf", size=max(14, base.width // 28))
        except OSError:
            font = ImageFont.load_default()
        draw.text((10, 10), "MOCK", font=font, fill=(255, 40, 40))

        buf = io.BytesIO()
        result.save(buf, format="PNG")
        return GenerationResult(
            image=buf.getvalue(),
            cost_usd=0.0,
            duration_ms=MOCK_DURATION_MS,
            provider=self.name,
        )
