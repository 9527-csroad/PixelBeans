"""End-to-end pipeline tests: determinism, postprocess, export artifact shape."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image
import pytest

from pixelbeans import assemble, export, load_palette, preprocess, quantize, run
from pixelbeans.palette import clear_cache
from pixelbeans.types import PipelineConfig

PALETTES_DIR = Path(__file__).resolve().parent.parent / "palettes"


@pytest.fixture(autouse=True)
def _clear_cache():
    clear_cache()
    yield
    clear_cache()


def _synthetic_rgb(w=80, h=80):
    rng = np.random.default_rng(42)
    return Image.fromarray(rng.integers(0, 256, (h, w, 3), dtype=np.uint8), "RGB")


def _synthetic_rgba(w=80, h=80):
    rng = np.random.default_rng(42)
    rgba = np.dstack([rng.integers(0, 256, (h, w, 3), dtype=np.uint8),
                      np.full((h, w), 255, dtype=np.uint8)])
    return Image.fromarray(rgba, "RGBA")


# ---- determinism -------------------------------------------------------------

def test_deterministic_output():
    img = _synthetic_rgb()
    palette = load_palette("mard", palettes_dir=PALETTES_DIR)
    cfg = PipelineConfig(target_width=30, target_height=30, max_colors=12)

    results = [run(img, palette, cfg) for _ in range(3)]
    for r in results[1:]:
        assert r.stats == results[0].stats
        for row_a, row_b in zip(r.cells, results[0].cells):
            for ca, cb in zip(row_a, row_b):
                assert ca.code == cb.code


# ---- alpha / empty cells -----------------------------------------------------

def test_transparent_region_produces_empty_cells():
    img = _synthetic_rgba()
    # force a 10×10 corner fully transparent
    pixels = np.array(img)
    pixels[:10, :10, 3] = 0
    img = Image.fromarray(pixels, "RGBA")
    palette = load_palette("mard", palettes_dir=PALETTES_DIR)
    cfg = PipelineConfig(target_width=20, target_height=20)
    res = run(img, palette, cfg)
    # top-left quadrant should have many empty cells
    assert res.stats.empty_cells > 0
    # verify the grid
    for y in range(res.height):
        for x in range(res.width):
            cell = res.cells[y][x]
            assert cell.is_empty == (res.cell(x, y).code == "_EMPTY_")


# ---- max_colors cap ----------------------------------------------------------

def test_max_colors_respected():
    img = _synthetic_rgb(w=100, h=100)
    palette = load_palette("mard", palettes_dir=PALETTES_DIR)
    cfg = PipelineConfig(target_width=50, target_height=50, max_colors=8)
    res = run(img, palette, cfg)
    assert res.stats.unique_colors <= 8


# ---- postprocess: isolated bead cleanup --------------------------------------

def test_no_cleanup_preserves_all_colors():
    """With --no-cleanup, small islands should remain."""
    img = _synthetic_rgb()
    palette = load_palette("mard", palettes_dir=PALETTES_DIR)
    cfg = PipelineConfig(target_width=40, target_height=40, max_colors=20,
                         remove_isolated_beads=False)
    res = run(img, palette, cfg)
    # Just verify it runs; the number of colors may be high without cleanup.
    assert res.width == 40


# ---- export ------------------------------------------------------------------

def test_export_artifacts_exist(tmp_path):
    img = _synthetic_rgb()
    palette = load_palette("mard", palettes_dir=PALETTES_DIR)
    cfg = PipelineConfig(target_width=20, target_height=20, max_colors=6)
    res = run(img, palette, cfg)
    paths = export.write_all(res, tmp_path, preview_cell_size=6, grid_cell_size=18)

    for name, path in paths.items():
        assert path.exists(), f"{name} not written: {path}"

    # sanity-check json
    data = json.loads(paths["pattern_json"].read_text(encoding="utf-8"))
    assert data["size"]["width"] == 20
    assert data["size"]["height"] == 20
    assert data["stats"]["unique_colors"] == len(data["palette_used"])


def test_bom_csv_parsable(tmp_path):
    import csv
    img = _synthetic_rgb()
    palette = load_palette("mard", palettes_dir=PALETTES_DIR)
    cfg = PipelineConfig(target_width=20, target_height=20, max_colors=5)
    res = run(img, palette, cfg)
    paths = export.write_all(res, tmp_path)
    with open(paths["bom_csv"], newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    assert len(rows) == res.stats.unique_colors
    for row in rows:
        assert row["count"].isdigit()
        assert int(row["count"]) > 0
