"""FastAPI server for PixelBeans pattern generation."""

from __future__ import annotations

import base64
import io
import os
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image

from pixelbeans import Palette, PipelineConfig, run
from pixelbeans.export import write_all
from pixelbeans.palette import load_palette as load_palette_core

from .schemas import (
    ErrorResponse,
    PaletteMetaResponse,
    PatternResponse,
    PaletteUsedEntry,
    PatternCell,
    PatternStats,
    SizeResponse,
)

app = FastAPI(title="PixelBeans API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PALETTES_DIR = Path(__file__).resolve().parent.parent / "palettes"
PALETTE_BRANDS = ["mard", "zhongyi", "manqi"]


@app.get("/api/v1/palettes")
def list_palettes() -> list[str]:
    return [b for b in PALETTE_BRANDS if (PALETTES_DIR / f"{b}.json").exists()]


@app.get("/api/v1/palettes/{brand}")
def get_palette(brand: str):
    brand_lower = brand.lower()
    path = PALETTES_DIR / f"{brand_lower}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Palette '{brand}' not found")
    import json
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data


@app.post("/api/v1/pattern", response_model=PatternResponse)
def generate_pattern(
    image: UploadFile = File(...),
    width: int = Form(58),
    height: int = Form(58),
    palette: str = Form("mard"),
    max_colors: int | None = Form(None),
    brightness: float = Form(1.0),
    contrast: float = Form(1.0),
    saturation: float = Form(1.0),
    sharpen: bool = Form(False),
    remove_isolated: bool = Form(True),
    min_region_size: int = Form(2),
):
    palette_lower = palette.lower()
    palette_path = PALETTES_DIR / f"{palette_lower}.json"
    if not palette_path.exists():
        raise HTTPException(status_code=404, detail=f"Palette '{palette}' not found")

    try:
        content = image.file.read()
        img = Image.open(io.BytesIO(content)).convert("RGBA")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid image: {e}")

    pal = load_palette_core(palette_lower)

    config = PipelineConfig(
        target_width=width,
        target_height=height,
        brightness=brightness,
        contrast=contrast,
        saturation=saturation,
        sharpen=sharpen,
        max_colors=max_colors,
        remove_isolated_beads=remove_isolated,
        min_region_size=min_region_size,
    )

    try:
        result = run(img, pal, config)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pattern generation failed: {e}")

    out_dir = Path(os.environ.get("PIXELBEANS_TMP", "/tmp/pixelbeans"))
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        write_all(result, str(out_dir))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {e}")

    preview_b64 = _png_to_b64(out_dir / "preview.png")
    grid_b64 = _png_to_b64(out_dir / "grid.png")

    pattern_2d = []
    for row in result.cells:
        pattern_2d.append(
            [PatternCell(code=c.code, hex=c.hex, symbol=c.symbol) for c in row]
        )

    palette_used = [
        PaletteUsedEntry(
            code=e.code, name=e.name, hex=e.hex, symbol=e.symbol, count=e.count
        )
        for e in result.palette_used
    ]

    return PatternResponse(
        size=SizeResponse(width=width, height=height),
        pattern=pattern_2d,
        palette_used=palette_used,
        stats=PatternStats(
            total_beads=result.stats.total_beads,
            unique_colors=result.stats.unique_colors,
            empty_cells=result.stats.empty_cells,
        ),
        preview_png=preview_b64,
        grid_png=grid_b64,
    )


def _png_to_b64(path: Path) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("ascii")
