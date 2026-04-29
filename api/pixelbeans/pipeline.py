"""Main pipeline: preprocess → pixelation → palette-constrained quantization.

All functions operate on in-memory arrays; no filesystem I/O except `load_image`.

Flow:
    image (PIL) ─► preprocess ─► (rgb_small (H,W,3) u8, mask (H,W) bool)
                                       │
                                       ▼
                     quantize ─► idx_grid (H,W) int64
                                 (-1 marks masked/empty cells)

The caller (pipeline.run or higher layers) stitches idx_grid + palette into
a `PatternResult`. Postprocessing (isolated-bead cleanup, color-count cap)
lives in `postprocess.py` and runs on `idx_grid` between quantize and assembly.
"""

from __future__ import annotations

from pathlib import Path
from typing import Union

import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter

from pixelbeans.color_science import srgb_u8_to_lab
from pixelbeans.palette import Palette
from pixelbeans.postprocess import cap_color_count, cleanup_isolated_beads
from pixelbeans.types import (
    PaletteUsageEntry,
    PatternCell,
    PatternResult,
    PatternStats,
    PipelineConfig,
)

# 62 alphanumerics + a few punctuation fallbacks (>62 unique colors in one
# pattern is highly unusual — a normal M1 run stays under 30).
_SYMBOL_ALPHABET = (
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "abcdefghijklmnopqrstuvwxyz"
    "0123456789"
    "!@#$%&*+<>?"
)

ImageInput = Union[str, Path, Image.Image, np.ndarray]


# ---- I/O ---------------------------------------------------------------------

def load_image(src: ImageInput) -> Image.Image:
    """Accept a path / PIL Image / ndarray and return a PIL RGBA image."""
    if isinstance(src, Image.Image):
        img = src
    elif isinstance(src, np.ndarray):
        arr = src
        if arr.ndim == 2:
            img = Image.fromarray(arr, mode="L")
        elif arr.shape[-1] == 4:
            img = Image.fromarray(arr, mode="RGBA")
        else:
            img = Image.fromarray(arr, mode="RGB")
    else:
        img = Image.open(src)
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    return img


# ---- preprocess --------------------------------------------------------------

def _center_crop_to_aspect(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """Crop `img` to the aspect ratio of `target_w/target_h`, centered."""
    sw, sh = img.size
    target_aspect = target_w / target_h
    src_aspect = sw / sh
    if abs(src_aspect - target_aspect) < 1e-6:
        return img
    if src_aspect > target_aspect:
        new_w = int(round(sh * target_aspect))
        left = (sw - new_w) // 2
        return img.crop((left, 0, left + new_w, sh))
    new_h = int(round(sw / target_aspect))
    top = (sh - new_h) // 2
    return img.crop((0, top, sw, top + new_h))


def preprocess(img: Image.Image, config: PipelineConfig) -> tuple[np.ndarray, np.ndarray]:
    """Apply enhancements, crop-to-aspect, downsample to target grid.

    Returns
    -------
    rgb_small : (target_h, target_w, 3) uint8
    mask      : (target_h, target_w) bool — True where a bead should be placed
    """
    tw, th = config.target_width, config.target_height

    img = load_image(img)
    img = _center_crop_to_aspect(img, tw, th)

    rgb_layer = img.convert("RGB")
    alpha_layer = img.split()[-1]  # 'A'

    if config.brightness != 1.0:
        rgb_layer = ImageEnhance.Brightness(rgb_layer).enhance(config.brightness)
    if config.contrast != 1.0:
        rgb_layer = ImageEnhance.Contrast(rgb_layer).enhance(config.contrast)
    if config.saturation != 1.0:
        rgb_layer = ImageEnhance.Color(rgb_layer).enhance(config.saturation)
    if config.sharpen:
        rgb_layer = rgb_layer.filter(
            ImageFilter.UnsharpMask(radius=1.5, percent=150, threshold=0)
        )

    rgb_full = np.array(rgb_layer, dtype=np.uint8)
    alpha_full = np.array(alpha_layer, dtype=np.uint8)

    # downsample: INTER_AREA is the right choice for shrinking (plan §3.2)
    rgb_small = cv2.resize(rgb_full, (tw, th), interpolation=cv2.INTER_AREA)
    alpha_small = cv2.resize(alpha_full, (tw, th), interpolation=cv2.INTER_AREA)

    mask = alpha_small >= config.alpha_threshold
    return rgb_small, mask


# ---- K-Means (LAB space, seeded, no sklearn) ---------------------------------

def _kmeans_plus_plus_init(points: np.ndarray, k: int, rng: np.random.Generator) -> np.ndarray:
    """Pick k initial centers using the K-Means++ seeding strategy."""
    n = points.shape[0]
    centers = np.empty((k, points.shape[1]), dtype=points.dtype)
    centers[0] = points[rng.integers(0, n)]
    # running min squared distance to nearest center
    d2 = np.sum((points - centers[0]) ** 2, axis=-1)
    for i in range(1, k):
        total = d2.sum()
        if total <= 0.0:
            centers[i] = points[rng.integers(0, n)]
        else:
            pick = rng.choice(n, p=d2 / total)
            centers[i] = points[pick]
        new_d2 = np.sum((points - centers[i]) ** 2, axis=-1)
        d2 = np.minimum(d2, new_d2)
    return centers


def kmeans_lab(
    lab_pixels: np.ndarray,
    k: int,
    *,
    max_iter: int = 25,
    seed: int = 0,
    tol: float = 1e-4,
) -> tuple[np.ndarray, np.ndarray]:
    """Lloyd K-Means on LAB points. Returns (labels (N,), centers (K, 3)).

    Pure NumPy (~30 lines). At 291-color palette × ~10K pixel scale this is
    well under 100ms and avoids a sklearn runtime dependency (plan §10.1).
    """
    pts = np.asarray(lab_pixels, dtype=np.float64)
    n = pts.shape[0]
    if k <= 0:
        raise ValueError("k must be >= 1")
    if k >= n:
        labels = np.arange(n, dtype=np.int64)
        return labels, pts.copy()

    rng = np.random.default_rng(seed)
    centers = _kmeans_plus_plus_init(pts, k, rng)
    labels = np.zeros(n, dtype=np.int64)

    for _ in range(max_iter):
        # assign: pairwise squared distance, argmin
        diffs = pts[:, None, :] - centers[None, :, :]
        d2 = np.einsum("nkd,nkd->nk", diffs, diffs)
        new_labels = d2.argmin(axis=-1)
        if np.array_equal(new_labels, labels):
            labels = new_labels
            break
        labels = new_labels

        # update: mean of each cluster (leave empty clusters at their old center)
        prev = centers.copy()
        for j in range(k):
            members = pts[labels == j]
            if members.size:
                centers[j] = members.mean(axis=0)
        if np.max(np.abs(centers - prev)) < tol:
            break

    return labels, centers


# ---- quantize ----------------------------------------------------------------

def quantize(
    rgb_u8: np.ndarray,
    mask: np.ndarray,
    palette: Palette,
    config: PipelineConfig,
) -> np.ndarray:
    """Map visible pixels to palette indices via (optional K-Means →) ΔE2000.

    Parameters
    ----------
    rgb_u8 : (H, W, 3) uint8
    mask   : (H, W) bool — only True cells are quantized; False cells get -1.

    Returns
    -------
    idx_grid : (H, W) int64. `-1` on masked cells.
    """
    if rgb_u8.shape[:2] != mask.shape:
        raise ValueError("rgb_u8 and mask shape mismatch")
    H, W, _ = rgb_u8.shape

    lab = srgb_u8_to_lab(rgb_u8)            # (H, W, 3)
    flat_lab = lab.reshape(-1, 3)
    flat_mask = mask.reshape(-1)
    visible_lab = flat_lab[flat_mask]       # (M, 3)

    if visible_lab.size == 0:
        return np.full((H, W), -1, dtype=np.int64)

    if config.max_colors is not None and config.max_colors < len(palette):
        labels, centers = kmeans_lab(visible_lab, config.max_colors)
        center_palette_idx = palette.nearest_indices_from_lab(centers)  # (K,)
        visible_palette_idx = center_palette_idx[labels]                # (M,)
    else:
        visible_palette_idx = palette.nearest_indices_from_lab(visible_lab)

    if config.dither:
        # Floyd-Steinberg deferred to M2 per plan §7. Log a hint if requested.
        import warnings

        warnings.warn("dither=True is not implemented in M1; ignoring", stacklevel=2)

    flat_idx = np.full(H * W, -1, dtype=np.int64)
    flat_idx[flat_mask] = visible_palette_idx
    return flat_idx.reshape(H, W)


# ---- top-level convenience ---------------------------------------------------

def run_grid(
    src: ImageInput,
    palette: Palette,
    config: PipelineConfig,
) -> tuple[np.ndarray, np.ndarray]:
    """End-to-end up through quantization: preprocess → quantize.

    Postprocessing (isolated-bead cleanup, color-count cap) and PatternResult
    assembly are separate steps; see `pixelbeans.postprocess` and
    `pixelbeans.pipeline.assemble` (added in the next step).
    """
    img = load_image(src)
    rgb_small, mask = preprocess(img, config)
    idx_grid = quantize(rgb_small, mask, palette, config)
    return idx_grid, mask


# ---- assembly & full run -----------------------------------------------------

def _assign_symbols(used_indices: list[int]) -> dict[int, str]:
    if len(used_indices) > len(_SYMBOL_ALPHABET):
        raise ValueError(
            f"too many distinct colors ({len(used_indices)}) for symbol encoding; "
            f"alphabet size is {len(_SYMBOL_ALPHABET)}"
        )
    return {pi: _SYMBOL_ALPHABET[k] for k, pi in enumerate(used_indices)}


def assemble(
    idx_grid: np.ndarray,
    mask: np.ndarray,
    palette: Palette,
    config: PipelineConfig,
) -> PatternResult:
    """Stitch an index grid + palette into the public PatternResult.

    Symbols are assigned in palette canonical order (i.e. the order entries
    appear in the brand JSON), so the same set of colors always produces the
    same symbol mapping — important for reproducibility across runs and
    for users cross-referencing multiple patterns.
    """
    if idx_grid.shape != mask.shape:
        raise ValueError("idx_grid and mask shape mismatch")
    H, W = idx_grid.shape

    visible = idx_grid[idx_grid != -1]
    used_indices = sorted({int(i) for i in np.unique(visible).tolist()})
    symbol_of = _assign_symbols(used_indices)

    # per-index counts
    if visible.size:
        vals, counts = np.unique(visible, return_counts=True)
        count_of = {int(v): int(c) for v, c in zip(vals, counts)}
    else:
        count_of = {}

    cells: list[list[PatternCell]] = []
    for y in range(H):
        row: list[PatternCell] = []
        for x in range(W):
            pi = int(idx_grid[y, x])
            if pi == -1:
                row.append(PatternCell.empty())
            else:
                c = palette.colors[pi]
                row.append(PatternCell(code=c.code, hex=c.hex, symbol=symbol_of[pi]))
        cells.append(row)

    palette_used = [
        PaletteUsageEntry(
            code=palette.colors[pi].code,
            name=palette.colors[pi].name,
            hex=palette.colors[pi].hex,
            symbol=symbol_of[pi],
            count=count_of.get(pi, 0),
        )
        for pi in used_indices
    ]

    stats = PatternStats(
        total_beads=int(visible.size),
        unique_colors=len(used_indices),
        empty_cells=int((idx_grid == -1).sum()),
    )

    return PatternResult(
        width=W,
        height=H,
        cells=cells,
        palette_used=palette_used,
        stats=stats,
        palette_meta=palette.meta,
        config=config,
    )


def run(
    src: ImageInput,
    palette: Palette,
    config: PipelineConfig,
) -> PatternResult:
    """Full photo → pattern conversion. The public entry point.

    Stages: preprocess → quantize → (optional isolated-bead cleanup) →
    (optional color-count cap) → assemble PatternResult.
    """
    idx_grid, mask = run_grid(src, palette, config)

    if config.remove_isolated_beads:
        idx_grid = cleanup_isolated_beads(
            idx_grid, min_region_size=config.min_region_size
        )

    if config.max_colors is not None:
        # Safety net: if palette-snap + cleanup left > max_colors, merge rarest.
        idx_grid = cap_color_count(
            idx_grid, palette, max_colors=config.max_colors
        )

    return assemble(idx_grid, mask, palette, config)
