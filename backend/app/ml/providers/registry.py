"""Resolve an InferenceProvider by name. Add new backends here only."""

from __future__ import annotations

from app.config import get_settings

from .base import InferenceProvider
from .fal import FalFluxFillProvider
from .mock import MockProvider

_REGISTRY: dict[str, type[InferenceProvider]] = {
    MockProvider.name: MockProvider,
    FalFluxFillProvider.name: FalFluxFillProvider,
    # Phase 2+: "replicate_flux": ReplicateProvider, "self_hosted": RunPodProvider, ...
}


def get_provider(name: str | None = None) -> InferenceProvider:
    """Resolve the inference provider.

    When ``name`` is not given, honour the mock flag first: ``MOCK_INFERENCE=true``
    (default) — or a missing ``FAL_API_KEY`` — routes to :class:`MockProvider`, so a
    fresh clone generates end-to-end with no credentials and no cost. An explicit
    ``name`` always wins (e.g. the spike runner forcing a specific backend).
    """
    if name is None:
        settings = get_settings()
        if settings.mock_inference or not settings.fal_api_key:
            name = MockProvider.name
        else:
            name = settings.inference_provider
    try:
        return _REGISTRY[name]()
    except KeyError as exc:
        raise ValueError(
            f"Unknown inference provider '{name}'. Known: {sorted(_REGISTRY)}"
        ) from exc
