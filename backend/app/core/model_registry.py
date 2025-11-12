from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Protocol, TYPE_CHECKING

from PIL import Image


@dataclass
class Prediction:
    label: str
    confidence: float
    extra: dict[str, float | int | str]


if TYPE_CHECKING:  # Avoid circular import during runtime
    from app.models.base import ModelMetadata


class PestModel(Protocol):
    """Lightweight protocol that any inference model must satisfy."""

    metadata: "ModelMetadata"

    async def predict(self, image: Image.Image) -> Prediction:
        ...


class ModelRegistry:
    """In-memory registry so new models can be plugged in dynamically."""

    def __init__(self) -> None:
        self._models: Dict[str, PestModel] = {}

    def register(self, model: PestModel) -> None:
        model_id = model.metadata.id
        if model_id in self._models:
            raise ValueError(f"Model '{model_id}' already registered")
        self._models[model_id] = model

    def get(self, model_id: str) -> PestModel:
        try:
            return self._models[model_id]
        except KeyError as exc:
            raise KeyError(f"Unknown model '{model_id}'") from exc

    def list(self) -> Iterable[PestModel]:
        return self._models.values()

    async def predict(self, model_id: str, image: Image.Image) -> Prediction:
        model = self.get(model_id)
        return await model.predict(image)
