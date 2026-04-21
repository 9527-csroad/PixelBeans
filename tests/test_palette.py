"""Tests for Palette: loading, alias dedup, subset, nearest-neighbor mapping."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from pixelbeans.palette import Palette, load_palette, clear_cache
from pixelbeans.types import PaletteMeta

PALETTES_DIR = Path(__file__).resolve().parent.parent / "palettes"


@pytest.fixture(autouse=True)
def _clear_cache():
    clear_cache()
    yield
    clear_cache()


# ---- construction ------------------------------------------------------------

def _make_palette(colors):
    return Palette.from_entries("TEST", colors, source="synthetic")


def test_load_mard():
    p = load_palette("mard", palettes_dir=PALETTES_DIR)
    assert p.meta.brand == "MARD"
    assert p.meta.total == 291
    assert len(p) == 290  # 291 entries but Q4/R11 share hex → one deduped
    assert p.lab.shape == (len(p), 3)
    assert p.lab.min() < 0  # Lab a/b can be negative


# ---- alias handling (Q4 / R11 same hex) --------------------------------------

def test_alias_dedup():
    colors = [
        {"code": "X1", "name": "X1", "hex": "#FF0000", "category": "A"},
        {"code": "X2", "name": "X2", "hex": "#00FF00", "category": "A"},
        {"code": "X3", "name": "X3", "hex": "#FF0000", "category": "A"},
    ]
    p = _make_palette(colors)
    assert len(p) == 2  # X1 and X2 survive
    assert "X3" in p.aliases
    assert p.aliases["X3"] == "X1"
    assert p.colors[0].aliases == ("X3",)


def test_alias_index_of():
    colors = [
        {"code": "A", "name": "A", "hex": "#111111", "category": "A"},
        {"code": "B", "name": "B", "hex": "#222222", "category": "A"},
        {"code": "C", "name": "C", "hex": "#111111", "category": "A"},
    ]
    p = _make_palette(colors)
    assert p.index_of("A") == 0
    assert p.index_of("C") == 0  # alias → A
    with pytest.raises(KeyError):
        p.index_of("Z")


# ---- subset ------------------------------------------------------------------

def test_subset_restriction():
    colors = [
        {"code": "R", "name": "R", "hex": "#FF0000", "category": "A"},
        {"code": "G", "name": "G", "hex": "#00FF00", "category": "A"},
        {"code": "B", "name": "B", "hex": "#0000FF", "category": "A"},
    ]
    p = _make_palette(colors)
    s = p.subset(["R", "B"])
    assert len(s) == 2
    assert {c.code for c in s.colors} == {"R", "B"}
    assert s.lab.shape == (2, 3)


# ---- nearest-neighbor --------------------------------------------------------

def test_nearest_matches_exact_palette_colors():
    colors = [
        {"code": "R", "name": "R", "hex": "#FF0000"},
        {"code": "G", "name": "G", "hex": "#00FF00"},
        {"code": "B", "name": "B", "hex": "#0000FF"},
    ]
    p = _make_palette(colors)
    # 3×3 image with pure palette colors
    rgb = np.array(
        [
            [[255, 0, 0], [0, 255, 0], [0, 0, 255]],
            [[255, 0, 0], [0, 255, 0], [0, 0, 255]],
            [[255, 0, 0], [0, 255, 0], [0, 0, 255]],
        ],
        dtype=np.uint8,
    )
    indices = p.nearest_indices(rgb)
    assert np.all(indices == np.array([[0, 1, 2], [0, 1, 2], [0, 1, 2]]))


def test_nearest_intermediate_color_picks_closer():
    colors = [
        {"code": "BK", "name": "BK", "hex": "#000000"},
        {"code": "WH", "name": "WH", "hex": "#FFFFFF"},
    ]
    p = _make_palette(colors)
    rgb = np.array([[[64, 64, 64]]], dtype=np.uint8)
    idx = p.nearest_indices(rgb)
    assert idx[0, 0] == 0  # closer to black


def test_nearest_deterministic_with_top_k():
    colors = [
        {"code": f"C{i:02d}", "name": f"C{i:02d}", "hex": f"#{i:02x}{i:02x}{i:02x}"}
        for i in range(0, 256, 4)
    ]
    p = _make_palette(colors)
    rgb = np.array([[[100, 100, 100], [200, 200, 200]]], dtype=np.uint8)
    r5 = p.nearest_indices(rgb, top_k=5)
    r10 = p.nearest_indices(rgb, top_k=10)
    assert np.array_equal(r5, r10)
