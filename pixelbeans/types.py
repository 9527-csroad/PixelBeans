"""Data models for PixelBeans.

Pure dataclasses with no runtime logic. Serves as the contract between:
- algorithm core (pixelbeans.pipeline)
- persistence (palettes/*.json)
- outer layers (CLI, HTTP API, frontend)

Any change here is a potential API breaking change.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class PaletteColor:
    """A single bead color in a brand palette."""

    code: str
    name: str
    hex: str
    category: str = "核心标准色"
    aliases: tuple[str, ...] = ()

    @property
    def rgb(self) -> tuple[int, int, int]:
        h = self.hex.lstrip("#")
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


@dataclass(frozen=True)
class PaletteMeta:
    """Provenance info for a palette file, echoed into output metadata."""

    brand: str
    source: str
    total: int
    categories: dict[str, int] = field(default_factory=dict)


@dataclass
class PipelineConfig:
    """Knobs that control one photo→pattern conversion."""

    target_width: int
    target_height: int

    # preprocessing
    brightness: float = 1.0
    contrast: float = 1.0
    saturation: float = 1.0
    sharpen: bool = False
    alpha_threshold: int = 128

    # quantization
    max_colors: Optional[int] = None
    dither: bool = False

    # postprocessing
    remove_isolated_beads: bool = True
    min_region_size: int = 2

    def __post_init__(self) -> None:
        if self.target_width <= 0 or self.target_height <= 0:
            raise ValueError("target size must be positive")
        if self.max_colors is not None and self.max_colors < 1:
            raise ValueError("max_colors must be >= 1 or None")
        if not 0 <= self.alpha_threshold <= 255:
            raise ValueError("alpha_threshold must be in [0, 255]")


EMPTY_CODE = "_EMPTY_"


@dataclass(frozen=True)
class PatternCell:
    """One grid cell in the output pattern.

    `code == EMPTY_CODE` means transparent/empty (no bead placed).
    """

    code: str
    hex: str
    symbol: str

    @classmethod
    def empty(cls) -> "PatternCell":
        return cls(code=EMPTY_CODE, hex="#00000000", symbol=" ")

    @property
    def is_empty(self) -> bool:
        return self.code == EMPTY_CODE


@dataclass
class PaletteUsageEntry:
    """Aggregated usage info for a color in the final pattern — the BOM row."""

    code: str
    name: str
    hex: str
    symbol: str
    count: int


@dataclass
class PatternStats:
    total_beads: int
    unique_colors: int
    empty_cells: int


@dataclass
class PatternResult:
    """The full output of one pipeline run.

    `cells[y][x]` — row-major grid, y is row (top→bottom), x is column (left→right).
    """

    width: int
    height: int
    cells: list[list[PatternCell]]
    palette_used: list[PaletteUsageEntry]
    stats: PatternStats
    palette_meta: PaletteMeta
    config: PipelineConfig

    def cell(self, x: int, y: int) -> PatternCell:
        return self.cells[y][x]
