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


# Minimal copy of the training repo's backbone builder to avoid importing external code
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


def _load_label_map(label_map_path: Path) -> Dict[int, str]:
    with label_map_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return {i: name for i, name in enumerate(data)}
    if isinstance(data, dict):
        if "index_to_label" in data and isinstance(data["index_to_label"], dict):
            return {int(k): v for k, v in data["index_to_label"].items()}
        if "label_to_index" in data and isinstance(data["label_to_index"], dict):
            return {int(v): k for k, v in data["label_to_index"].items()}
        # Fallback: flat dict with numeric keys as strings
        try:
            return {int(k): v for k, v in data.items()}
        except Exception as exc:  # pragma: no cover
            raise ValueError("Unsupported label_map format") from exc
    raise ValueError("label_map must be a list or dict")


@dataclass
class _Leaf9Config:
    model_dir: Path
    ckpt_path: Path
    label_map_path: Path
    backbone: str  # "efficientnet_v2_s" or "resnet50" or "auto"
    device: str  # "cuda" or "cpu"
    img_size: int


class LeafNineModel(BasePestModel):
    """Adapter for the Leaf_9_model PyTorch classifier.

    Expects a directory layout like:
      <LEAF9_DIR>/outputs/best.ckpt
      <LEAF9_DIR>/data/label_map.json
    """

    def __init__(
        self,
        model_dir: Optional[str | Path] = None,
        backbone: Optional[str] = None,
        device: Optional[str] = None,
        img_size: int = 448,
    ) -> None:
        # Default model directory inside this repo: backend/model_store/leaf9
        default_internal_dir = Path(__file__).resolve().parents[2] / "model_store" / "leaf9"
        base_dir = (
            Path(model_dir)
            if model_dir
            else Path(os.getenv("LEAF9_DIR", str(default_internal_dir)))
        )

        self.cfg = _Leaf9Config(
            model_dir=base_dir,
            ckpt_path=base_dir / "outputs" / os.getenv("LEAF9_CKPT", "best.ckpt"),
            label_map_path=Path(os.getenv("LEAF9_LABEL_MAP", str(base_dir / "data" / "label_map.json"))),
            backbone=(backbone or os.getenv("LEAF9_BACKBONE", "auto")).lower(),
            device=(device or os.getenv("LEAF9_DEVICE", ("cuda" if torch.cuda.is_available() else "cpu"))).lower(),
            img_size=int(os.getenv("LEAF9_IMG_SIZE", str(img_size))),
        )

        if not self.cfg.ckpt_path.exists():
            raise FileNotFoundError(f"Checkpoint not found: {self.cfg.ckpt_path}")
        if not self.cfg.label_map_path.exists():
            raise FileNotFoundError(f"Label map not found: {self.cfg.label_map_path}")

        self.index_to_label = _load_label_map(self.cfg.label_map_path)
        self.labels: List[str] = [name for _, name in sorted(self.index_to_label.items(), key=lambda kv: kv[0])]
        num_classes = len(self.labels)

        # Build model (auto-try backbones if requested)
        tried: List[str]
        if self.cfg.backbone == "auto":
            tried = ["efficientnet_v2_s", "resnet50"]
        else:
            tried = [self.cfg.backbone]

        device = torch.device(self.cfg.device)
        last_err: Optional[Exception] = None
        model: Optional[nn.Module] = None
        for b in tried:
            try:
                m = _build_classifier(backbone=b, num_classes=num_classes, pretrained=False)
                ckpt = torch.load(self.cfg.ckpt_path, map_location=device)
                state_dict = ckpt.get("state_dict", ckpt)
                m.load_state_dict(state_dict, strict=True)
                m.to(device)
                m.eval()
                model = m
                self.backbone = b
                break
            except Exception as exc:  # pragma: no cover
                last_err = exc
                model = None
        if model is None:
            raise RuntimeError(f"Failed to load model with backbones {tried}: {last_err}")

        self.model = model
        self.device = device
        self.tf = _build_eval_transform(self.cfg.img_size)

        self.metadata = ModelMetadata(
            id="leaf9-pytorch-v1",
            name="Leaf 9-Class Classifier",
            version="1.0.0",
            description=f"PyTorch classifier ({self.backbone}) loaded from {self.cfg.ckpt_path.name}",
            labels=self.labels,
        )

    async def predict(self, image: Image.Image) -> Prediction:  # type: ignore[override]
        img = image.convert("RGB")
        x = self.tf(img).unsqueeze(0).to(self.device)
        with torch.inference_mode():
            logits = self.model(x)
            probs_t = F.softmax(logits, dim=1).squeeze(0).cpu()
        probs: List[float] = probs_t.tolist()
        top_idx = int(np.argmax(probs))
        top_label = self.index_to_label[top_idx]
        top_conf = float(probs[top_idx])

        # Build top-5 dictionary (label -> prob)
        top5_idx = np.argsort(probs)[::-1][:5]
        top5: Dict[str, float] = {self.index_to_label[int(i)]: float(probs[int(i)]) for i in top5_idx}

        return Prediction(
            label=top_label,
            confidence=round(top_conf, 6),
            extra={"top5": top5},
        )
