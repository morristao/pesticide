from __future__ import annotations

from dataclasses import dataclass

from PIL import Image, ImageStat

from app.core.model_registry import Prediction
from app.models.base import BasePestModel, ModelMetadata


@dataclass
class HeuristicThresholds:
    dry_threshold: float = 25.0
    fungal_threshold: float = 18.0
    pest_threshold: float = 12.5


class ColorSignatureModel(BasePestModel):
    """Crude heuristic model using RGB ratios as a placeholder for a real model."""

    def __init__(self, thresholds: HeuristicThresholds | None = None) -> None:
        self.thresholds = thresholds or HeuristicThresholds()
        self.metadata = ModelMetadata(
            id="color-signature-v1",
            name="Color Signature Heuristic",
            version="0.1.0",
            description="Baseline heuristic that inspects color balance to mimic pest/disease detection.",
            labels=["leaf_scorch", "powdery_mildew", "pest_damage", "healthy"],
        )

    async def predict(self, image: Image.Image) -> Prediction:
        rgb_image = image.convert("RGB")
        stats = ImageStat.Stat(rgb_image)
        r, g, b = stats.mean
        green_ratio = g / (r + g + b)
        red_ratio = r / (r + g + b)
        dryness_score = (red_ratio - green_ratio) * 100
        fungal_score = (1 - green_ratio) * 80
        pest_score = (green_ratio - red_ratio) * 60

        if dryness_score > self.thresholds.dry_threshold:
            label = "leaf_scorch"
            confidence = min(0.95, dryness_score / 100)
        elif fungal_score > self.thresholds.fungal_threshold:
            label = "powdery_mildew"
            confidence = min(0.9, fungal_score / 80)
        elif pest_score > self.thresholds.pest_threshold:
            label = "pest_damage"
            confidence = min(0.85, pest_score / 60)
        else:
            label = "healthy"
            confidence = 0.55

        return Prediction(
            label=label,
            confidence=round(confidence, 3),
            extra={
                "dryness_score": round(dryness_score, 2),
                "fungal_score": round(fungal_score, 2),
                "pest_score": round(pest_score, 2),
            },
        )
