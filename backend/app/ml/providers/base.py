"""Inference provider abstraction (architecture §5.4).

Every inference backend implements ``InferenceProvider.generate``. The pipeline
never imports a concrete provider directly — it resolves one through the registry,
so Fal.ai can be swapped for Replicate / self-hosted without pipeline changes.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ProviderConfig:
    """Per-call configuration passed to a provider."""

    image_size: int = 1024
    num_inference_steps: int = 28
    guidance_scale: float = 30.0
    extra: dict = field(default_factory=dict)


@dataclass
class GenerationResult:
    """What every provider returns, regardless of backend."""

    image: bytes
    cost_usd: float
    duration_ms: int
    provider: str


class InferenceProvider(ABC):
    """Inpainting inference backend.

    Contract: given the source image, a binary mouth mask, and a prompt, return the
    inpainted result plus cost/latency telemetry for the ``generations`` row.
    """

    name: str = "base"

    @abstractmethod
    async def generate(
        self,
        *,
        image: bytes,
        mask: bytes,
        prompt: str,
        config: ProviderConfig,
    ) -> GenerationResult:
        raise NotImplementedError
