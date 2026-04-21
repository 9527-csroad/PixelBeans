"""PixelBeans — photo to perler bead pattern converter.

Core package. All algorithm modules are pure functions (no I/O side effects
beyond `pipeline.load_image`) so they can be reused as a backend API or
ported to other platforms.
"""

from pixelbeans.palette import Palette, load_palette
from pixelbeans.pipeline import assemble, preprocess, quantize, run, run_grid
from pixelbeans.types import (
    EMPTY_CODE,
    PaletteColor,
    PaletteMeta,
    PaletteUsageEntry,
    PatternCell,
    PatternResult,
    PatternStats,
    PipelineConfig,
)

__version__ = "0.1.0"

__all__ = [
    "EMPTY_CODE",
    "Palette",
    "PaletteColor",
    "PaletteMeta",
    "PaletteUsageEntry",
    "PatternCell",
    "PatternResult",
    "PatternStats",
    "PipelineConfig",
    "assemble",
    "load_palette",
    "preprocess",
    "quantize",
    "run",
    "run_grid",
    "__version__",
]
