"""Command-line entry point for PixelBeans.

Example (matches the M1 DoD in docs/plan.md §8):

    python -m pixelbeans.cli \\
        --input images/sample.png \\
        --size 58x58 \\
        --palette mard \\
        --max-colors 30 \\
        --out result/

or, via the root shim:

    python cli.py --input images/sample.png --size 58x58 --palette mard --out result/
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from pixelbeans import export, load_palette, run
from pixelbeans.types import PipelineConfig


def _parse_size(s: str) -> tuple[int, int]:
    raw = s.lower().replace(" ", "")
    if "x" not in raw:
        raise argparse.ArgumentTypeError(f"--size must look like WxH (got {s!r})")
    try:
        w_str, h_str = raw.split("x", 1)
        w, h = int(w_str), int(h_str)
    except ValueError:
        raise argparse.ArgumentTypeError(f"--size must be integers (got {s!r})")
    if w <= 0 or h <= 0:
        raise argparse.ArgumentTypeError("--size dimensions must be positive")
    return w, h


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="pixelbeans",
        description="Convert a photo into a bead pattern chart.",
    )
    p.add_argument("--input", "-i", required=True, type=Path, help="Input image file")
    p.add_argument("--size", "-s", required=True, type=_parse_size,
                   help="Output grid size, e.g. 58x58")
    p.add_argument("--palette", "-p", default="mard",
                   help="Palette brand (default: mard)")
    p.add_argument("--out", "-o", required=True, type=Path, help="Output directory")
    p.add_argument("--max-colors", type=int, default=None,
                   help="Upper bound on distinct colors in output (default: unlimited)")

    g_pre = p.add_argument_group("preprocessing")
    g_pre.add_argument("--brightness", type=float, default=1.0)
    g_pre.add_argument("--contrast", type=float, default=1.0)
    g_pre.add_argument("--saturation", type=float, default=1.0)
    g_pre.add_argument("--sharpen", action="store_true")
    g_pre.add_argument("--alpha-threshold", type=int, default=128,
                       help="0–255 (default 128); below → empty cell")

    g_post = p.add_argument_group("postprocessing")
    g_post.add_argument("--no-cleanup", action="store_true",
                        help="Skip isolated-bead cleanup")
    g_post.add_argument("--min-region-size", type=int, default=2,
                        help="Island size considered 'isolated' (default 2)")

    g_out = p.add_argument_group("output rendering")
    g_out.add_argument("--preview-cell-size", type=int, default=8)
    g_out.add_argument("--grid-cell-size", type=int, default=24)
    g_out.add_argument("--preview-mode", choices=("square", "round"), default="square")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if not args.input.exists():
        print(f"error: input file not found: {args.input}", file=sys.stderr)
        return 2

    w, h = args.size
    config = PipelineConfig(
        target_width=w,
        target_height=h,
        brightness=args.brightness,
        contrast=args.contrast,
        saturation=args.saturation,
        sharpen=args.sharpen,
        alpha_threshold=args.alpha_threshold,
        max_colors=args.max_colors,
        dither=False,  # M1 does not implement dithering
        remove_isolated_beads=not args.no_cleanup,
        min_region_size=args.min_region_size,
    )

    try:
        palette = load_palette(args.palette)
    except FileNotFoundError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    t0 = time.perf_counter()
    result = run(args.input, palette, config)
    elapsed = time.perf_counter() - t0

    paths = export.write_all(
        result,
        args.out,
        preview_cell_size=args.preview_cell_size,
        grid_cell_size=args.grid_cell_size,
        preview_mode=args.preview_mode,
    )

    print(
        f"Done in {elapsed:.2f}s — "
        f"{result.stats.unique_colors} colors, {result.stats.total_beads} beads"
    )
    print(f"  brand : {result.palette_meta.brand}  ({len(palette)} available)")
    print(f"  size  : {result.width} × {result.height}  "
          f"(empty: {result.stats.empty_cells})")
    for name, path in paths.items():
        print(f"  {name:14s} {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
