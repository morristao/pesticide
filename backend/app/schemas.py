from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ModelInfo(BaseModel):
    id: str
    name: str
    version: str
    description: str
    labels: list[str]


class PredictionPayload(BaseModel):
    model: ModelInfo
    label: str
    confidence: float = Field(ge=0, le=1)
    extra: dict[str, Any]


class CompactPrediction(BaseModel):
    label: str
    confidence: float = Field(ge=0, le=1)
