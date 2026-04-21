"""Pydantic models for the Pattern API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SizeResponse(BaseModel):
    width: int
    height: int


class PatternCell(BaseModel):
    code: str
    hex: str
    symbol: str


class PaletteUsedEntry(BaseModel):
    code: str
    name: str
    hex: str
    symbol: str
    count: int


class PatternStats(BaseModel):
    total_beads: int
    unique_colors: int
    empty_cells: int


class PaletteMetaResponse(BaseModel):
    brand: str
    source: str
    total: int


class PatternResponse(BaseModel):
    ok: bool = True
    size: SizeResponse
    pattern: list[list[PatternCell]]
    palette_used: list[PaletteUsedEntry]
    stats: PatternStats
    preview_png: str = Field(description="base64-encoded PNG")
    grid_png: str = Field(description="base64-encoded PNG")


class ErrorResponse(BaseModel):
    ok: bool = False
    detail: str
