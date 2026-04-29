"""Color science primitives: sRGB ↔ Lab and CIEDE2000 (ΔE2000).

Why we roll our own instead of using `colour-science`:
- Keep runtime deps minimal (end users of the future API/端侧包 won't want
  the full colour-science dependency chain).
- Future ports to Kotlin/Swift/TypeScript can translate this file line-by-line;
  colour-science is not portable.

All functions are vectorized over arbitrary leading dims. The last dimension
of color arrays is always 3 (RGB or Lab).

References:
- sRGB D65 white point; IEC 61966-2-1
- CIEDE2000 per Sharma, Wu, Dalal (2005)
  https://hajim.rochester.edu/ece/sites/gsharma/ciede2000/
"""

from __future__ import annotations

import numpy as np

# ---- constants ---------------------------------------------------------------

# sRGB → linear RGB → XYZ (D65, 2° observer)
_RGB_TO_XYZ = np.array(
    [
        [0.4124564, 0.3575761, 0.1804375],
        [0.2126729, 0.7151522, 0.0721750],
        [0.0193339, 0.1191920, 0.9503041],
    ],
    dtype=np.float64,
)
_XYZ_TO_RGB = np.linalg.inv(_RGB_TO_XYZ)

# D65 reference white (normalized so Y=1)
_D65 = np.array([0.95047, 1.00000, 1.08883], dtype=np.float64)

# CIE Lab constants
_DELTA = 6.0 / 29.0
_DELTA3 = _DELTA ** 3          # ≈ 0.008856
_KAPPA = (1.0 / 3.0) * (29.0 / 6.0) ** 2   # ≈ 7.787
_BIAS = 4.0 / 29.0


# ---- sRGB <-> linear ---------------------------------------------------------

def srgb_to_linear(srgb01: np.ndarray) -> np.ndarray:
    """sRGB in [0,1] → linear RGB in [0,1]. Shape preserved."""
    srgb01 = np.asarray(srgb01, dtype=np.float64)
    low = srgb01 <= 0.04045
    return np.where(low, srgb01 / 12.92, ((srgb01 + 0.055) / 1.055) ** 2.4)


def linear_to_srgb(linear: np.ndarray) -> np.ndarray:
    """Linear RGB in [0,1] → sRGB in [0,1]. Shape preserved."""
    linear = np.clip(np.asarray(linear, dtype=np.float64), 0.0, 1.0)
    low = linear <= 0.0031308
    return np.where(low, linear * 12.92, 1.055 * (linear ** (1.0 / 2.4)) - 0.055)


# ---- RGB <-> XYZ -------------------------------------------------------------

def linear_to_xyz(linear: np.ndarray) -> np.ndarray:
    """Linear RGB [0,1] → XYZ (Y normalized to 1 for D65 white)."""
    linear = np.asarray(linear, dtype=np.float64)
    return linear @ _RGB_TO_XYZ.T


def xyz_to_linear(xyz: np.ndarray) -> np.ndarray:
    """XYZ → linear RGB [0,1]."""
    xyz = np.asarray(xyz, dtype=np.float64)
    return xyz @ _XYZ_TO_RGB.T


# ---- XYZ <-> Lab -------------------------------------------------------------

def _lab_f(t: np.ndarray) -> np.ndarray:
    # piecewise nonlinearity used in XYZ→Lab
    return np.where(t > _DELTA3, np.cbrt(t), _KAPPA * t + _BIAS)


def _lab_f_inv(t: np.ndarray) -> np.ndarray:
    return np.where(t > _DELTA, t ** 3, (t - _BIAS) / _KAPPA)


def xyz_to_lab(xyz: np.ndarray) -> np.ndarray:
    """XYZ (Y=1 white) → Lab. L in [0,100], a,b typically in [-128,127]."""
    xyz = np.asarray(xyz, dtype=np.float64)
    fx = _lab_f(xyz[..., 0] / _D65[0])
    fy = _lab_f(xyz[..., 1] / _D65[1])
    fz = _lab_f(xyz[..., 2] / _D65[2])
    L = 116.0 * fy - 16.0
    a = 500.0 * (fx - fy)
    b = 200.0 * (fy - fz)
    return np.stack([L, a, b], axis=-1)


def lab_to_xyz(lab: np.ndarray) -> np.ndarray:
    lab = np.asarray(lab, dtype=np.float64)
    L, a, b = lab[..., 0], lab[..., 1], lab[..., 2]
    fy = (L + 16.0) / 116.0
    fx = fy + a / 500.0
    fz = fy - b / 200.0
    x = _lab_f_inv(fx) * _D65[0]
    y = _lab_f_inv(fy) * _D65[1]
    z = _lab_f_inv(fz) * _D65[2]
    return np.stack([x, y, z], axis=-1)


# ---- convenience: uint8 sRGB <-> Lab -----------------------------------------

def srgb_u8_to_lab(rgb_u8: np.ndarray) -> np.ndarray:
    """Uint8 sRGB [0..255] → Lab. Last dim = 3."""
    rgb01 = np.asarray(rgb_u8, dtype=np.float64) / 255.0
    return xyz_to_lab(linear_to_xyz(srgb_to_linear(rgb01)))


def lab_to_srgb_u8(lab: np.ndarray) -> np.ndarray:
    """Lab → uint8 sRGB [0..255], clipped to valid gamut."""
    rgb01 = linear_to_srgb(xyz_to_linear(lab_to_xyz(lab)))
    return np.clip(np.round(rgb01 * 255.0), 0, 255).astype(np.uint8)


def hex_to_lab(hex_str: str) -> np.ndarray:
    """'#RRGGBB' → Lab as 1-D array of shape (3,)."""
    h = hex_str.lstrip("#")
    rgb = np.array([int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)], dtype=np.uint8)
    return srgb_u8_to_lab(rgb)


# ---- CIEDE2000 (ΔE2000) ------------------------------------------------------

def delta_e_2000(
    lab1: np.ndarray,
    lab2: np.ndarray,
    kL: float = 1.0,
    kC: float = 1.0,
    kH: float = 1.0,
) -> np.ndarray:
    """Batch CIEDE2000. `lab1` and `lab2` broadcast on leading dims; last dim = 3.

    Returns array of ΔE values with the broadcasted leading shape.
    """
    lab1 = np.asarray(lab1, dtype=np.float64)
    lab2 = np.asarray(lab2, dtype=np.float64)
    L1, a1, b1 = lab1[..., 0], lab1[..., 1], lab1[..., 2]
    L2, a2, b2 = lab2[..., 0], lab2[..., 1], lab2[..., 2]

    # Step 1: chroma adjustment with G factor
    C1 = np.sqrt(a1 * a1 + b1 * b1)
    C2 = np.sqrt(a2 * a2 + b2 * b2)
    C_bar = 0.5 * (C1 + C2)
    C_bar7 = C_bar ** 7
    G = 0.5 * (1.0 - np.sqrt(C_bar7 / (C_bar7 + 25.0 ** 7)))
    a1p = (1.0 + G) * a1
    a2p = (1.0 + G) * a2
    C1p = np.sqrt(a1p * a1p + b1 * b1)
    C2p = np.sqrt(a2p * a2p + b2 * b2)

    # hue angles in degrees, in [0, 360)
    h1p = np.degrees(np.arctan2(b1, a1p)) % 360.0
    h2p = np.degrees(np.arctan2(b2, a2p)) % 360.0
    # undefined hue (chroma == 0) → 0
    h1p = np.where(C1p == 0, 0.0, h1p)
    h2p = np.where(C2p == 0, 0.0, h2p)

    # Step 2: dL', dC', dH'
    dLp = L2 - L1
    dCp = C2p - C1p

    dhp = h2p - h1p
    dhp = np.where(dhp > 180.0, dhp - 360.0, dhp)
    dhp = np.where(dhp < -180.0, dhp + 360.0, dhp)
    dhp = np.where(C1p * C2p == 0.0, 0.0, dhp)
    dHp = 2.0 * np.sqrt(C1p * C2p) * np.sin(np.radians(dhp) / 2.0)

    # Step 3: weighting factors
    Lp_bar = 0.5 * (L1 + L2)
    Cp_bar = 0.5 * (C1p + C2p)

    hp_sum = h1p + h2p
    hp_diff = np.abs(h1p - h2p)
    hp_bar = np.where(
        C1p * C2p == 0.0,
        hp_sum,
        np.where(
            hp_diff <= 180.0,
            hp_sum / 2.0,
            np.where(hp_sum < 360.0, (hp_sum + 360.0) / 2.0, (hp_sum - 360.0) / 2.0),
        ),
    )

    T = (
        1.0
        - 0.17 * np.cos(np.radians(hp_bar - 30.0))
        + 0.24 * np.cos(np.radians(2.0 * hp_bar))
        + 0.32 * np.cos(np.radians(3.0 * hp_bar + 6.0))
        - 0.20 * np.cos(np.radians(4.0 * hp_bar - 63.0))
    )
    dTheta = 30.0 * np.exp(-(((hp_bar - 275.0) / 25.0) ** 2))
    Cp_bar7 = Cp_bar ** 7
    RC = 2.0 * np.sqrt(Cp_bar7 / (Cp_bar7 + 25.0 ** 7))
    SL = 1.0 + (0.015 * (Lp_bar - 50.0) ** 2) / np.sqrt(20.0 + (Lp_bar - 50.0) ** 2)
    SC = 1.0 + 0.045 * Cp_bar
    SH = 1.0 + 0.015 * Cp_bar * T
    RT = -np.sin(np.radians(2.0 * dTheta)) * RC

    term_L = dLp / (kL * SL)
    term_C = dCp / (kC * SC)
    term_H = dHp / (kH * SH)

    return np.sqrt(term_L * term_L + term_C * term_C + term_H * term_H + RT * term_C * term_H)


def delta_e_2000_matrix(lab_pixels: np.ndarray, lab_palette: np.ndarray) -> np.ndarray:
    """Pairwise ΔE2000 between each pixel and every palette color.

    `lab_pixels`: shape (..., 3). `lab_palette`: shape (K, 3).
    Returns shape (..., K) with ΔE values.
    """
    pixels = lab_pixels[..., np.newaxis, :]  # (..., 1, 3)
    palette = lab_palette[np.newaxis, :, :]  # (1, K, 3) (broadcasts over leading dims)
    # align ranks
    while palette.ndim < pixels.ndim:
        palette = palette[np.newaxis, ...]
    return delta_e_2000(pixels, palette)
