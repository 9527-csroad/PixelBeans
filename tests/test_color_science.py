"""Golden-value tests for color_science.

sRGB→Lab values cross-checked against `colour-science` (dev-only) and any
standard online sRGB↔Lab calculator; kept as hard-coded constants here so
runtime tests do not require colour-science.

ΔE2000 pairs from Sharma, Wu, Dalal (2005) — the canonical implementation
test suite:
    https://hajim.rochester.edu/ece/sites/gsharma/ciede2000/
"""

from __future__ import annotations

import numpy as np
import pytest

from pixelbeans.color_science import (
    delta_e_2000,
    delta_e_2000_matrix,
    hex_to_lab,
    lab_to_srgb_u8,
    srgb_u8_to_lab,
)


# ---- sRGB ↔ LAB round-trip ---------------------------------------------------

@pytest.mark.parametrize(
    "rgb, expected_lab",
    [
        # standard references (D65 white point, 2° observer)
        ((255, 255, 255), (100.0, 0.0, 0.0)),
        ((0, 0, 0), (0.0, 0.0, 0.0)),
        ((255, 0, 0), (53.24, 80.09, 67.20)),
        ((0, 255, 0), (87.74, -86.18, 83.18)),
        ((0, 0, 255), (32.30, 79.20, -107.86)),
        ((128, 128, 128), (53.59, 0.0, 0.0)),
    ],
)
def test_srgb_to_lab_golden(rgb, expected_lab):
    lab = srgb_u8_to_lab(np.array(rgb, dtype=np.uint8))
    assert lab.shape == (3,)
    np.testing.assert_allclose(lab, expected_lab, atol=0.02)


def test_srgb_lab_round_trip_preserves_common_colors():
    # loop a representative set through LAB and back; must land within ±1 u8
    colors = np.array(
        [
            [255, 255, 255],
            [0, 0, 0],
            [200, 100, 50],
            [10, 200, 220],
            [128, 128, 128],
            [73, 181, 45],
        ],
        dtype=np.uint8,
    )
    lab = srgb_u8_to_lab(colors)
    recovered = lab_to_srgb_u8(lab)
    np.testing.assert_allclose(recovered.astype(int), colors.astype(int), atol=1)


def test_hex_to_lab_matches_rgb_version():
    a = hex_to_lab("#FF8040")
    b = srgb_u8_to_lab(np.array([0xFF, 0x80, 0x40], dtype=np.uint8))
    np.testing.assert_allclose(a, b)


# ---- ΔE2000 (Sharma 2005 golden) ---------------------------------------------

# Subset of the Sharma/Wu/Dalal reference pairs — strong coverage of the
# hue-wrap, chroma rotation, and achromatic edge cases.
_SHARMA_PAIRS = [
    # (lab1, lab2, expected_dE)
    ((50.0, 2.6772, -79.7751), (50.0, 0.0, -82.7485), 2.0425),
    ((50.0, 3.1571, -77.2803), (50.0, 0.0, -82.7485), 2.8615),
    ((50.0, 2.8361, -74.0200), (50.0, 0.0, -82.7485), 3.4412),
    ((50.0, -1.3802, -84.2814), (50.0, 0.0, -82.7485), 1.0000),
    ((50.0, -1.1848, -84.8006), (50.0, 0.0, -82.7485), 1.0000),
    ((50.0, -0.9009, -85.5211), (50.0, 0.0, -82.7485), 1.0000),
    ((50.0, 0.0, 0.0), (50.0, -1.0, 2.0), 2.3669),
    ((50.0, -1.0, 2.0), (50.0, 0.0, 0.0), 2.3669),
    ((50.0, 2.49, -0.001), (50.0, -2.49, 0.0009), 7.1792),
    ((50.0, 2.49, -0.001), (50.0, -2.49, 0.0010), 7.1792),
    ((50.0, 2.49, -0.001), (73.0, 25.0, -18.0), 27.1492),
    ((50.0, 2.49, -0.001), (61.0, -5.0, 29.0), 22.8977),
    ((50.0, 2.5, 0.0), (50.0, 0.0, -2.5), 4.3065),
]


@pytest.mark.parametrize("lab1, lab2, expected", _SHARMA_PAIRS)
def test_delta_e_2000_sharma_golden(lab1, lab2, expected):
    dE = delta_e_2000(np.array(lab1), np.array(lab2))
    # 1e-3 for close pairs, but larger ΔE (>20) accumulates more floating-point
    # drift from the Sharma reference rounding; tolerate 0.01 there.
    atol = 0.01 if expected > 20 else 1e-3
    assert dE == pytest.approx(expected, abs=atol)


def test_delta_e_2000_is_symmetric():
    rng = np.random.default_rng(7)
    a = rng.uniform([0, -50, -50], [100, 50, 50], size=(20, 3))
    b = rng.uniform([0, -50, -50], [100, 50, 50], size=(20, 3))
    np.testing.assert_allclose(delta_e_2000(a, b), delta_e_2000(b, a), atol=1e-9)


def test_delta_e_2000_zero_for_identical_colors():
    lab = np.array([[50.0, 12.0, -3.0], [80.0, 0.0, 0.0]])
    np.testing.assert_allclose(delta_e_2000(lab, lab), 0.0, atol=1e-10)


def test_delta_e_2000_matrix_shape():
    pix = np.zeros((4, 5, 3))
    pal = np.ones((7, 3))
    out = delta_e_2000_matrix(pix, pal)
    assert out.shape == (4, 5, 7)
