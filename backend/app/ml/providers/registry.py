"""Resolve an InferenceProvider by name. Add new backends here only."""

from __future__ import annotations

from app.config import get_settings

from .base import InferenceProvider
from .fal import FalFluxFillProvider

_REGISTRY: dict[str, type[InferenceProvider]] = {
    FalFluxFillProvider.name: FalFluxFillProvider,
    # Phase 2+: "replicate_flux": ReplicateProvider, "self_hosted": RunPodProvider, ...
}


def get_provider(name: str | None = None) -> InferenceProvider:
    name = name or get_settings().inference_provider
    try:
        return _REGISTRY[name]()
    except KeyError as exc:
        raise ValueError(
            f"Unknown inference provider '{name}'. Known: {sorted(_REGISTRY)}"
        ) from exc
