"""Export artifacts from a PatternResult: JSON, preview PNG, grid PNG, BOM text.

All rendering uses Pillow only (no external font files shipped; we try common
system fonts and fall back to the default bitmap if none are available).

Outputs (plan §3.5):
- pattern.json  structured data; the backbone of the API response
- preview.png   flat pixel-art image for quick visual comparison with original
- grid.png      chart with colored cells + symbols + reference crosshairs
- bom.txt       human-readable BOM
- bom.csv       machine-readable BOM

PDF export is deferred to M2 (needs reportlab).
"""

from __future__ import annotations

import csv
import json
from dataclasses import asdict
from pathlib import Path
from typing import Union

from PIL import Image, ImageDraw, ImageFont

from pixelbeans.types import PatternResult

PathLike = Union[str, Path]


# ---- JSON --------------------------------------------------------------------

def pattern_to_dict(result: PatternResult) -> dict:
    """Convert PatternResult into a JSON-safe dict matching the API contract."""
    return {
        "version": "0.1.0",
        "size": {"width": result.width, "height": result.height},
        "pattern": [
            [
                None
                if cell.is_empty
                else {"code": cell.code, "hex": cell.hex, "symbol": cell.symbol}
                for cell in row
            ]
            for row in result.cells
        ],
        "palette_used": [asdict(e) for e in result.palette_used],
        "stats": asdict(result.stats),
        "palette_meta": {
            "brand": result.palette_meta.brand,
            "source": result.palette_meta.source,
            "total": result.palette_meta.total,
        },
        "config": {
            "target_width": result.config.target_width,
            "target_height": result.config.target_height,
            "brightness": result.config.brightness,
            "contrast": result.config.contrast,
            "saturation": result.config.saturation,
            "sharpen": result.config.sharpen,
            "alpha_threshold": result.config.alpha_threshold,
            "max_colors": result.config.max_colors,
            "dither": result.config.dither,
            "remove_isolated_beads": result.config.remove_isolated_beads,
            "min_region_size": result.config.min_region_size,
        },
    }


def write_json(result: PatternResult, path: PathLike) -> None:
    data = pattern_to_dict(result)
    Path(path).write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


# ---- color helpers -----------------------------------------------------------

def _hex_to_rgb(hex_str: str) -> tuple[int, int, int]:
    h = hex_str.lstrip("#")
    if len(h) == 8:
        h = h[:6]  # drop alpha channel for rendering
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _contrast_color(rgb: tuple[int, int, int]) -> tuple[int, int, int]:
    """Pick black or white for legible text on top of `rgb`."""
    r, g, b = rgb
    # Rec. 709 luminance — good proxy for perceived brightness
    lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return (0, 0, 0) if lum > 140 else (255, 255, 255)


def _load_font(size: int) -> ImageFont.ImageFont:
    """Try common system fonts; fall back to Pillow's bitmap default."""
    candidates = [
        "DejaVuSans-Bold.ttf",
        "DejaVuSans.ttf",
        "arialbd.ttf",
        "arial.ttf",
        "Arial.ttf",
        "Helvetica.ttf",
    ]
    for name in candidates:
        try:
            return ImageFont.truetype(name, size=size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


def _text_size(draw: ImageDraw.ImageDraw, text: str, font) -> tuple[int, int]:
    """Pillow changed the API around v10; handle both."""
    if hasattr(draw, "textbbox"):
        l, t, r, b = draw.textbbox((0, 0), text, font=font)
        return r - l, b - t
    return draw.textsize(text, font=font)


# ---- PNGs --------------------------------------------------------------------

def render_preview(
    result: PatternResult,
    *,
    cell_size: int = 8,
    mode: str = "square",
) -> Image.Image:
    """Flat pixel-art preview. `mode='round'` draws a disc per cell (bead sim)."""
    if mode not in ("square", "round"):
        raise ValueError("mode must be 'square' or 'round'")
    W, H = result.width, result.height
    img = Image.new("RGBA", (W * cell_size, H * cell_size), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)

    for y, row in enumerate(result.cells):
        for x, cell in enumerate(row):
            if cell.is_empty:
                continue
            rgb = _hex_to_rgb(cell.hex)
            x0, y0 = x * cell_size, y * cell_size
            x1, y1 = x0 + cell_size, y0 + cell_size
            if mode == "square":
                draw.rectangle([x0, y0, x1 - 1, y1 - 1], fill=rgb + (255,))
            else:
                pad = max(1, cell_size // 10)
                draw.ellipse(
                    [x0 + pad, y0 + pad, x1 - pad, y1 - pad],
                    fill=rgb + (255,),
                )
    return img


def render_grid(
    result: PatternResult,
    *,
    cell_size: int = 24,
    minor_line: tuple[int, int, int] = (140, 140, 140),
    major_line: tuple[int, int, int] = (0, 0, 0),
    major_every: int = 10,
) -> Image.Image:
    """Paper-chart view: colored cells + symbol per cell + 10-cell crosshairs."""
    W, H = result.width, result.height
    img_w, img_h = W * cell_size, H * cell_size
    img = Image.new("RGB", (img_w, img_h), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    font = _load_font(max(8, cell_size - 10))

    # 1) fill cells + symbols
    for y, row in enumerate(result.cells):
        for x, cell in enumerate(row):
            x0, y0 = x * cell_size, y * cell_size
            x1, y1 = x0 + cell_size, y0 + cell_size
            if cell.is_empty:
                draw.rectangle([x0, y0, x1 - 1, y1 - 1], fill=(240, 240, 240))
                draw.line([x0, y0, x1 - 1, y1 - 1], fill=(200, 200, 200))
                continue
            rgb = _hex_to_rgb(cell.hex)
            draw.rectangle([x0, y0, x1 - 1, y1 - 1], fill=rgb)
            txt_color = _contrast_color(rgb)
            tw, th = _text_size(draw, cell.symbol, font)
            tx = x0 + (cell_size - tw) // 2
            ty = y0 + (cell_size - th) // 2 - 1
            draw.text((tx, ty), cell.symbol, fill=txt_color, font=font)

    # 2) grid lines; major lines overdrawn last so they sit above minor
    for x in range(W + 1):
        xp = min(x * cell_size, img_w - 1)
        draw.line([(xp, 0), (xp, img_h - 1)], fill=minor_line, width=1)
    for y in range(H + 1):
        yp = min(y * cell_size, img_h - 1)
        draw.line([(0, yp), (img_w - 1, yp)], fill=minor_line, width=1)

    for x in range(0, W + 1, major_every):
        xp = min(x * cell_size, img_w - 1)
        draw.line([(xp, 0), (xp, img_h - 1)], fill=major_line, width=2)
    for y in range(0, H + 1, major_every):
        yp = min(y * cell_size, img_h - 1)
        draw.line([(0, yp), (img_w - 1, yp)], fill=major_line, width=2)

    return img


def write_preview(result: PatternResult, path: PathLike, **kw) -> None:
    render_preview(result, **kw).save(path)


def write_grid(result: PatternResult, path: PathLike, **kw) -> None:
    render_grid(result, **kw).save(path)


# ---- BOM ---------------------------------------------------------------------

def write_bom_text(result: PatternResult, path: PathLike) -> None:
    entries = sorted(result.palette_used, key=lambda e: (-e.count, e.code))
    lines = [
        f"# Bill of Materials — {result.palette_meta.brand}",
        f"# grid: {result.width} × {result.height} = {result.width * result.height} cells",
        f"# beads: {result.stats.total_beads}  (empty cells: {result.stats.empty_cells})",
        f"# unique colors: {result.stats.unique_colors}",
        "",
        f"{'symbol':<8}{'code':<10}{'hex':<12}{'count':>8}  name",
        "-" * 60,
    ]
    for e in entries:
        lines.append(f"{e.symbol:<8}{e.code:<10}{e.hex:<12}{e.count:>8}  {e.name}")
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_bom_csv(result: PatternResult, path: PathLike) -> None:
    entries = sorted(result.palette_used, key=lambda e: (-e.count, e.code))
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["symbol", "code", "hex", "name", "count"])
        for e in entries:
            w.writerow([e.symbol, e.code, e.hex, e.name, e.count])


# ---- umbrella ----------------------------------------------------------------

def write_all(
    result: PatternResult,
    out_dir: PathLike,
    *,
    preview_cell_size: int = 8,
    grid_cell_size: int = 24,
    preview_mode: str = "square",
) -> dict[str, Path]:
    """Write the full M1 artifact set. Returns a map of name → written path."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths = {
        "pattern_json": out / "pattern.json",
        "preview_png": out / "preview.png",
        "grid_png": out / "grid.png",
        "bom_txt": out / "bom.txt",
        "bom_csv": out / "bom.csv",
    }
    write_json(result, paths["pattern_json"])
    write_preview(result, paths["preview_png"], cell_size=preview_cell_size, mode=preview_mode)
    write_grid(result, paths["grid_png"], cell_size=grid_cell_size)
    write_bom_text(result, paths["bom_txt"])
    write_bom_csv(result, paths["bom_csv"])
    return paths
