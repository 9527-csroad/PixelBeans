"""Pydantic schemas for the PixelBeans API."""

from __future__ import annotations

from pydantic import BaseModel, Field


# ── Request ───────────────────────────────────────────────────────────────

class PatternRequest(BaseModel):
    """Request body for POST /api/v1/pattern."""

    # image as base64 (without data: prefix)
    image: str = Field(description="Base64-encoded image (JPG/PNG)")

    # required params
    width: int = Field(ge=10, le=500, description="Pattern grid width")
    height: int = Field(ge=10, le=500, description="Pattern grid height")
    palette: str = Field(description="Palette brand, e.g. 'mard'")

    # optional params
    max_colors: int | None = Field(default=None, ge=1, le=100, description="Max unique colors")
    brightness: float = Field(default=1.0, ge=0.1, le=3.0)
    contrast: float = Field(default=1.0, ge=0.1, le=3.0)
    saturation: float = Field(default=1.0, ge=0.1, le=3.0)
    sharpen: bool = False
    remove_isolated: bool = True
    min_region_size: int = Field(default=2, ge=1, le=10)


# ── Response ───────────────────────────────────────────────────────────────

class PatternCellResponse(BaseModel):
    code: str
    hex: str


class ColorEntryResponse(BaseModel):
    code: str
    name: str
    hex: str
    symbol: str
    count: int


class StatsResponse(BaseModel):
    total_beads: int
    unique_colors: int
    empty_cells: int


class PatternResponse(BaseModel):
    """Response body for POST /api/v1/pattern."""

    width: int
    height: int
    pattern: list[list[PatternCellResponse]]
    colors: list[ColorEntryResponse]
    stats: StatsResponse
    preview_image: str = Field(description="Base64 PNG — pixel art preview")
    grid_image: str = Field(description="Base64 PNG — symbol grid with crosshairs")
    pattern_image: str = Field(description="Base64 PNG — flat color grid (no symbols)")


class ErrorResponse(BaseModel):
    detail: str
    error_code: str | None = None
