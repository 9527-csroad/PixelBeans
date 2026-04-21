"""Postprocessing: isolated-bead cleanup + color-count cap.

Both operate on an `idx_grid` of shape (H, W) int64 where `-1` marks empty
cells (alpha-masked) and any other value is a palette index.

Isolated-bead cleanup
---------------------
Pixel-art pattern readers want "runs" of color. One stray bead of a rare color
surrounded by another color is almost always a quantization artifact: the
human eye treats it as noise, the user has to go pick one bead of that color
just for a single cell, etc. We detect small same-color connected regions
(4-conn) and re-label them to the majority of their non-empty neighbors.

Color-count cap
---------------
Even after K-Means reduces to ≤ K unique inputs (pipeline §3.3), palette
snapping can yield N distinct palette colors where N <= K but still > user's
max. This pass iteratively merges the least-used palette color into its
nearest-in-LAB surviving color until `distinct_count <= max_colors`.
"""

from __future__ import annotations

import cv2
import numpy as np

from pixelbeans.palette import Palette

_N4 = ((-1, 0), (1, 0), (0, -1), (0, 1))


def cleanup_isolated_beads(
    idx_grid: np.ndarray,
    *,
    min_region_size: int = 2,
    max_passes: int = 4,
) -> np.ndarray:
    """Merge same-color islands of size <= `min_region_size` into neighbor majority.

    Uses 4-connectivity. Empty cells (-1) are never reassigned and do not count
    as neighbors during voting (so a stray bead next to transparency is left
    alone rather than forced to pick any available color).

    Multiple passes catch cascades where cleaning one island exposes another.
    """
    if min_region_size <= 0:
        return idx_grid.copy()

    result = idx_grid.copy()
    H, W = result.shape

    for _ in range(max_passes):
        changed = False
        unique = np.unique(result)
        for c in unique:
            if c == -1:
                continue
            binary = (result == c).astype(np.uint8)
            num_labels, labels = cv2.connectedComponents(binary, connectivity=4)
            for label_id in range(1, num_labels):
                island = np.argwhere(labels == label_id)
                if len(island) > min_region_size:
                    continue
                neighbor_colors: list[int] = []
                for (y, x) in island:
                    for dy, dx in _N4:
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < H and 0 <= nx < W:
                            nc = result[ny, nx]
                            if nc != c and nc != -1:
                                neighbor_colors.append(int(nc))
                if not neighbor_colors:
                    continue
                vals, counts = np.unique(neighbor_colors, return_counts=True)
                # tie-breaker: lowest palette index wins (deterministic)
                top = counts.max()
                winner = int(vals[counts == top].min())
                for (y, x) in island:
                    result[y, x] = winner
                changed = True
        if not changed:
            break
    return result


def cap_color_count(
    idx_grid: np.ndarray,
    palette: Palette,
    *,
    max_colors: int,
) -> np.ndarray:
    """Ensure at most `max_colors` distinct palette indices appear in the grid.

    Strategy: repeatedly identify the least-used color, reassign all its cells
    to the nearest (LAB Euclidean) surviving color. Stable against ties
    (lowest index wins) so same input → same output.
    """
    if max_colors < 1:
        raise ValueError("max_colors must be >= 1")

    result = idx_grid.copy()
    while True:
        visible = result[result != -1]
        if visible.size == 0:
            return result
        vals, counts = np.unique(visible, return_counts=True)
        if len(vals) <= max_colors:
            return result

        # pick victim: least count, tie-break on highest palette index (arbitrary
        # but deterministic; we prefer to keep lower-indexed = earlier-listed colors)
        min_count = counts.min()
        candidates = vals[counts == min_count]
        victim = int(candidates.max())

        survivors = vals[vals != victim]
        victim_lab = palette.lab[victim]
        diffs = palette.lab[survivors] - victim_lab
        d2 = np.einsum("nd,nd->n", diffs, diffs)
        # tie-break: lowest palette index among closest
        best = d2.min()
        closest = survivors[d2 == best]
        replacement = int(np.min(closest))

        result[result == victim] = replacement
