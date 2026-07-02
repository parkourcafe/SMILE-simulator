"""Fal.ai FLUX.1 [pro] Fill provider (primary, MVP).

Endpoint: ``fal-ai/flux-pro/v1/fill``. Cost ~$0.05/megapixel. Latency 3–8s.
Inputs are base64 data URIs (image + mask); output is a result image URL we fetch.
"""

from __future__ import annotations

import base64
import time

import httpx

from app.config import get_settings

from .base import GenerationResult, InferenceProvider, ProviderConfig

FAL_QUEUE_BASE = "https://fal.run"
COST_PER_MEGAPIXEL_USD = 0.05


def _data_uri(data: bytes, mime: str = "image/png") -> str:
    return f"data:{mime};base64,{base64.b64encode(data).decode()}"


class FalFluxFillProvider(InferenceProvider):
    name = "fal_flux_pro_fill"

    def __init__(self) -> None:
        self.settings = get_settings()

    async def generate(
        self,
        *,
        image: bytes,
        mask: bytes,
        prompt: str,
        config: ProviderConfig,
    ) -> GenerationResult:
        if not self.settings.fal_api_key:
            raise RuntimeError("FAL_API_KEY not configured.")

        endpoint = self.settings.fal_flux_fill_endpoint
        payload = {
            "prompt": prompt,
            "image_url": _data_uri(image),
            "mask_url": _data_uri(mask),
            "num_inference_steps": config.num_inference_steps,
            "guidance_scale": config.guidance_scale,
            **config.extra,
        }
        headers = {"Authorization": f"Key {self.settings.fal_api_key}"}

        started = time.monotonic()
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(f"{FAL_QUEUE_BASE}/{endpoint}", headers=headers, json=payload)
            if resp.status_code >= 400:
                raise RuntimeError(f"Fal.ai error {resp.status_code}: {resp.text}")
            body = resp.json()
            result_url = body["images"][0]["url"]
            img_resp = await client.get(result_url)
            img_resp.raise_for_status()
            result_bytes = img_resp.content
        duration_ms = int((time.monotonic() - started) * 1000)

        megapixels = (config.image_size * config.image_size) / 1_000_000
        cost = round(megapixels * COST_PER_MEGAPIXEL_USD, 4)
        return GenerationResult(
            image=result_bytes,
            cost_usd=cost,
            duration_ms=duration_ms,
            provider=self.name,
        )
