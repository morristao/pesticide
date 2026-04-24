from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from PIL import Image
from torchvision import transforms

from app.core.model_registry import Prediction
from app.models.base import BasePestModel, ModelMetadata


def _build_classifier(backbone: str, num_classes: int, pretrained: bool = False) -> nn.Module:
    from torchvision.models import (
        resnet50,
        ResNet50_Weights,
        efficientnet_v2_s,
        EfficientNet_V2_S_Weights,
    )

    if backbone == "resnet50":
        weights = ResNet50_Weights.IMAGENET1K_V2 if pretrained else None
        model = resnet50(weights=weights)
        in_features = model.fc.in_features
        model.fc = nn.Linear(in_features, num_classes)
        return model
    elif backbone == "efficientnet_v2_s":
        weights = EfficientNet_V2_S_Weights.IMAGENET1K_V1 if pretrained else None
        model = efficientnet_v2_s(weights=weights)
        in_features = model.classifier[1].in_features
        model.classifier[1] = nn.Linear(in_features, num_classes)
        return model
    else:
        raise ValueError(f"Unsupported backbone: {backbone}")


def _build_eval_transform(img_size: int) -> transforms.Compose:
    return transforms.Compose(
        [
            transforms.Resize(img_size),
            transforms.CenterCrop(img_size),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ]
    )


@dataclass
class _OvaEntry:
    label: str
    ckpt: Path
    backbone: str


def _load_ova_map(ova_map_path: Path, default_backbone: str) -> List[_OvaEntry]:
    with ova_map_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    entries: List[_OvaEntry] = []
    # Accept two formats:
    # 1) { "models": { "Healthy": {"ckpt": "...", "backbone": "efficientnet_v2_s"}, "label": {...} }, "img_size": 448 }
    # 2) { "Healthy": "path/to/ckpt", "label": "path/to/ckpt", ... }
    if isinstance(data, dict) and "models" in data and isinstance(data["models"], dict):
        for label, spec in data["models"].items():
            if isinstance(spec, dict) and "ckpt" in spec:
                ckpt = Path(spec["ckpt"])  # may be relative to ova_map_path
                if not ckpt.is_absolute():
                    ckpt = ova_map_path.parent / ckpt
                backbone = str(spec.get("backbone", default_backbone))
                entries.append(_OvaEntry(label=label, ckpt=ckpt, backbone=backbone))
    elif isinstance(data, dict):
        for label, ckpt in data.items():
            if not isinstance(ckpt, str):
                continue
            p = Path(ckpt)
            if not p.is_absolute():
                p = ova_map_path.parent / p
            entries.append(_OvaEntry(label=label, ckpt=p, backbone=default_backbone))
    else:
        raise ValueError("Unsupported OVA map format")

    if not entries:
        raise ValueError("Empty OVA map: no models provided")
    return entries


class LeafNineOvaEnsemble(BasePestModel):
    """OvA ensemble: one binary classifier per class; pick the highest positive prob."""

    def __init__(
        self,
        ova_map: Optional[str | Path] = None,
        ova_dir: Optional[str | Path] = None,
        default_backbone: Optional[str] = None,
        device: Optional[str] = None,
        img_size: Optional[int] = None,
    ) -> None:
        # Default in-repo directory for ova artifacts
        default_dir = Path(__file__).resolve().parents[2] / "model_store" / "leaf9" / "ova"

        map_path = Path(os.getenv("LEAF9_OVA_MAP", str(ova_map) if ova_map else str(default_dir / "ova_map.json")))
        models_root = Path(os.getenv("LEAF9_OVA_DIR", str(ova_dir) if ova_dir else str(default_dir)))
        backbone = (default_backbone or os.getenv("LEAF9_BACKBONE", "efficientnet_v2_s")).lower()
        self.device = torch.device((device or os.getenv("LEAF9_DEVICE", ("cuda" if torch.cuda.is_available() else "cpu"))).lower())
        self.img_size = int(os.getenv("LEAF9_IMG_SIZE", str(img_size or 448)))

        entries = _load_ova_map(map_path, default_backbone=backbone)
        self.labels: List[str] = [e.label for e in entries]

        self.models: List[Tuple[str, nn.Module]] = []
        for e in entries:
            ckpt_path = e.ckpt
            if not ckpt_path.is_absolute():
                ckpt_path = models_root / ckpt_path
            if not ckpt_path.exists():
                raise FileNotFoundError(f"OVA checkpoint not found for '{e.label}': {ckpt_path}")
            m = _build_classifier(backbone=e.backbone, num_classes=2, pretrained=False)
            ckpt = torch.load(ckpt_path, map_location=self.device)
            state_dict = ckpt.get("state_dict", ckpt)
            m.load_state_dict(state_dict, strict=True)
            m.to(self.device)
            m.eval()
            self.models.append((e.label, m))

        self.tf = _build_eval_transform(self.img_size)
        self.metadata = ModelMetadata(
            id="leaf9-ova-v1",
            name="Leaf 9-Class OvA Ensemble",
            version="1.0.0",
            description=f"One-vs-all ensemble with {len(self.models)} binary checkpoints",
            labels=self.labels,
        )

    async def predict(self, image: Image.Image) -> Prediction:  # type: ignore[override]
        img = image.convert("RGB")
        x = self.tf(img).unsqueeze(0).to(self.device)

        scores: List[Tuple[str, float]] = []
        with torch.inference_mode():
            for label, model in self.models:
                logits = model(x)
                probs = F.softmax(logits, dim=1).squeeze(0)
                pos_prob = float(probs[1].item())  # index 1 = positive class
                scores.append((label, pos_prob))

        scores.sort(key=lambda kv: kv[1], reverse=True)
        top_label, top_prob = scores[0]
        top5 = {lbl: float(prob) for lbl, prob in scores[:5]}

        return Prediction(
            label=top_label,
            confidence=round(float(top_prob), 6),
            extra={"top5": top5},
        )

