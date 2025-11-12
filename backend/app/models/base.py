from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from PIL import Image

from app.core.model_registry import Prediction


@dataclass
class ModelMetadata:
    id: str
    name: str
    version: str
    description: str
    labels: list[str]


class BasePestModel:
    """Base helper so concrete models only implement predict()."""

    metadata: ModelMetadata

    async def predict(self, image: Image.Image) -> Prediction:  # pragma: no cover - interface
        raise NotImplementedError

    def to_dict(self) -> dict[str, Any]:
        data = self.metadata
        return {
            "id": data.id,
            "name": data.name,
            "version": data.version,
            "description": data.description,
            "labels": data.labels,
        }
