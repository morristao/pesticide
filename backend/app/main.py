from __future__ import annotations

import io
import os
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image, UnidentifiedImageError
from typing import Annotated

from app.core.model_registry import ModelRegistry
from app.models import load_models
from app.schemas import ModelInfo, PredictionPayload, CompactPrediction


def _parse_csv(value: str, allow_wildcard: bool = True) -> list[str]:
    tokens = [entry.strip() for entry in value.split(",") if entry.strip()]
    if allow_wildcard:
        if not tokens or "*" in tokens:
            return ["*"]
    return tokens or (["*"] if allow_wildcard else [])


DEFAULT_ORIGINS = ["http://localhost:3000", "http://localhost:5173"]
frontend_origin = os.getenv("FRONTEND_ORIGIN")
if frontend_origin:
    DEFAULT_ORIGINS.append(frontend_origin)

def _dedupe(items: list[str]) -> list[str]:
    seen: dict[str, None] = {}
    for entry in items:
        if entry not in seen:
            seen[entry] = None
    return list(seen.keys())


allowed_origins_env = os.getenv("APP_ALLOWED_ORIGINS")
ALLOWED_ORIGINS = (
    _parse_csv(allowed_origins_env)
    if allowed_origins_env
    else _dedupe(DEFAULT_ORIGINS)
)
TRUSTED_HOSTS = _parse_csv(os.getenv("APP_TRUSTED_HOSTS", "*"))
ALLOW_CREDENTIALS = os.getenv("APP_ALLOW_CREDENTIALS", "false").lower() == "true"
FORCE_HTTPS = os.getenv("APP_FORCE_HTTPS", "false").lower() == "true"

app = FastAPI(
    title="Pest & Disease Detection Service",
    version="0.1.0",
    description="Upload crop images, run selectable detection models, and retrieve predictions.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=ALLOW_CREDENTIALS and ALLOWED_ORIGINS != ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

if TRUSTED_HOSTS != ["*"]:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=TRUSTED_HOSTS)

if FORCE_HTTPS:
    app.add_middleware(HTTPSRedirectMiddleware)

registry = ModelRegistry()
load_models(registry)

STATIC_DIR = Path(__file__).parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", response_class=HTMLResponse)
async def landing_page() -> HTMLResponse:
    index_path = STATIC_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="UI not built yet.")
    return HTMLResponse(index_path.read_text(encoding="utf-8"))


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/healthz", include_in_schema=False)
async def healthz() -> dict[str, str]:
    return await health()


@app.get("/api/v1/models")
async def list_models() -> list[ModelInfo]:
    return [
        ModelInfo(
            id=model.metadata.id,
            name=model.metadata.name,
            version=model.metadata.version,
            description=model.metadata.description,
            labels=model.metadata.labels,
        )
        for model in registry.list()
    ]


@app.post("/api/v1/infer", response_model=PredictionPayload)
async def infer(
    # Avoid pydantic protected namespace warning by not naming the parameter "model_id",
    # while still accepting the incoming form field as "model_id" via alias.
    selected_model: Annotated[str, Form(alias="model_id")],
    image: UploadFile = File(...),
) -> PredictionPayload:
    try:
        contents = await image.read()
        pil_image = Image.open(io.BytesIO(contents))
        pil_image = pil_image.convert("RGB")
    except UnidentifiedImageError as exc:
        raise HTTPException(status_code=400, detail="Invalid or corrupt image file.") from exc

    try:
        prediction = await registry.predict(model_id=selected_model, image=pil_image)
        model = registry.get(selected_model)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    payload = PredictionPayload(
        model=ModelInfo(
            id=model.metadata.id,
            name=model.metadata.name,
            version=model.metadata.version,
            description=model.metadata.description,
            labels=model.metadata.labels,
        ),
        label=prediction.label,
        confidence=prediction.confidence,
        extra=prediction.extra,
    )
    return payload


@app.post("/api/v1/infer/compact", response_model=CompactPrediction)
async def infer_compact(
    selected_model: Annotated[str, Form(alias="model_id")],
    image: UploadFile = File(...),
) -> CompactPrediction:
    try:
        contents = await image.read()
        pil_image = Image.open(io.BytesIO(contents))
        pil_image = pil_image.convert("RGB")
    except UnidentifiedImageError as exc:
        raise HTTPException(status_code=400, detail="Invalid or corrupt image file.") from exc

    try:
        prediction = await registry.predict(model_id=selected_model, image=pil_image)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return CompactPrediction(label=prediction.label, confidence=prediction.confidence)
