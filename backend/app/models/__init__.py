from __future__ import annotations

from app.core.model_registry import ModelRegistry
from app.models.mock_model import ColorSignatureModel


def load_models(registry: ModelRegistry) -> None:
    """Register every available model implementation."""

    registry.register(ColorSignatureModel())
