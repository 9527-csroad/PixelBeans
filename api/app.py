"""PixelBeans standalone HTTP API.

Self-contained FastAPI app — no React, no web UI.
Only Python code for App developers to integrate.

Usage:
    cd api && uvicorn app:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import base64
import io
import sys
from pathlib import Path

# Ensure the local directory is on sys.path so we can import pixelbeans + schemas
API_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(API_ROOT))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image

from pixelbeans import PipelineConfig, run
from pixelbeans.export import render_grid, render_preview
from pixelbeans.palette import load_palette as load_palette_core

from schemas import (
    ColorEntryResponse,
    PatternCellResponse,
    PatternRequest,
    PatternResponse,
    StatsResponse,
)

API_VERSION = "1.0.0"

app = FastAPI(title="PixelBeans API", version=API_VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PALETTES_DIR = API_ROOT / "palettes"


# ── Helpers ────────────────────────────────────────────────────────────────

def _decode_image(data_b64: str) -> Image.Image:
    """Decode a base64 image string into a PIL Image (RGBA)."""
    raw = base64.b64decode(data_b64)
    return Image.open(io.BytesIO(raw)).convert("RGBA")


def _img_to_b64(img: Image.Image) -> str:
    """Encode a PIL Image as base64 PNG string."""
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def _render_pattern(result, cell_size: int = 16) -> Image.Image:
    """Flat color grid — no symbols, no text, just colored cells.

    This is the 3rd output image alongside preview and grid.
    """
    W, H = result.width, result.height
    img = Image.new("RGB", (W * cell_size, H * cell_size), (255, 255, 255))
    draw = img.load()
    for y in range(H):
        for x in range(W):
            cell = result.cells[y][x]
            if cell.is_empty:
                continue
            h = cell.hex.lstrip("#")
            if len(h) == 8:
                h = h[:6]
            rgb = (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
            for dy in range(cell_size):
                for dx in range(cell_size):
                    draw[x * cell_size + dx, y * cell_size + dy] = rgb
    return img


# ── Endpoints ───────────────────────────────────────────────────────────────

@app.post("/api/v1/pattern", response_model=PatternResponse)
def generate_pattern(req: PatternRequest):
    """Generate a perler bead pattern from an image.

    Request:
        image        — base64-encoded image (JPG/PNG)
        width        — target grid width  (10-500)
        height       — target grid height (10-500)
        palette      — palette brand (e.g. 'mard')
        max_colors   — optional max unique colors
        brightness   — brightness multiplier (default 1.0)
        contrast     — contrast multiplier (default 1.0)
        saturation   — saturation multiplier (default 1.0)
        sharpen      — apply unsharp mask (default false)
        remove_isolated — merge isolated beads (default true)
        min_region_size — min connected region size (default 2)

    Response:
        width         — grid width
        height        — grid height
        pattern       — 2D grid [{code, hex}, ...]
        colors        — used color list [{code, name, hex, symbol, count}, ...]
        stats         — {total_beads, unique_colors, empty_cells}
        preview_image — base64 PNG: pixel art preview
        grid_image    — base64 PNG: symbol grid with crosshairs
        pattern_image — base64 PNG: flat color grid (no symbols)
    """
    palette_path = PALETTES_DIR / f"{req.palette.lower()}.json"
    if not palette_path.exists():
        raise HTTPException(status_code=404, detail=f"Palette '{req.palette}' not found")

    try:
        img = _decode_image(req.image)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid image: {e}")

    pal = load_palette_core(req.palette.lower())
    config = PipelineConfig(
        target_width=req.width,
        target_height=req.height,
        brightness=req.brightness,
        contrast=req.contrast,
        saturation=req.saturation,
        sharpen=req.sharpen,
        max_colors=req.max_colors,
        remove_isolated_beads=req.remove_isolated,
        min_region_size=req.min_region_size,
    )

    try:
        result = run(img, pal, config)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pattern generation failed: {e}")

    # Render 3 images
    preview_img = render_preview(result, cell_size=8, mode="square")
    grid_img = render_grid(result, cell_size=24)
    pattern_img = _render_pattern(result, cell_size=16)

    # Build response
    pattern_2d = [
        [PatternCellResponse(code=c.code, hex=c.hex) for c in row]
        for row in result.cells
    ]
    colors = [
        ColorEntryResponse(
            code=e.code, name=e.name, hex=e.hex, symbol=e.symbol, count=e.count,
        )
        for e in result.palette_used
    ]

    return PatternResponse(
        width=req.width,
        height=req.height,
        pattern=pattern_2d,
        colors=colors,
        stats=StatsResponse(
            total_beads=result.stats.total_beads,
            unique_colors=result.stats.unique_colors,
            empty_cells=result.stats.empty_cells,
        ),
        preview_image=_img_to_b64(preview_img),
        grid_image=_img_to_b64(grid_img),
        pattern_image=_img_to_b64(pattern_img),
    )
