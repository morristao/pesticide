from __future__ import annotations

import os

from app.core.model_registry import ModelRegistry
from app.models.mock_model import ColorSignatureModel


def load_models(registry: ModelRegistry) -> None:
    """Register every available model implementation."""
    # Prefer OvA ensemble if explicitly requested
    mode = os.getenv("LEAF9_MODE", "auto").lower()
    if mode in {"ova", "auto"}:
        try:
            from app.models.leaf9_ova import LeafNineOvaEnsemble  # type: ignore

            registry.register(LeafNineOvaEnsemble())
            return
        except Exception:
            if mode == "ova":
                # If user forced OVA but it fails, fall back to mock
                registry.register(ColorSignatureModel())
                return

    # Otherwise try single multi-class model
    try:
        from app.models.leaf9_pytorch import LeafNineModel  # type: ignore

        registry.register(LeafNineModel())
    except Exception:
        # Fallback to mock heuristic if real model cannot be loaded at startup
        registry.register(ColorSignatureModel())
