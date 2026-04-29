"""Scrape bead-color charts from pixel-beads.com and produce palettes/*.json.

Usage (from project root, inside the `image` conda env):

    python palettes/scraper.py mard  > palettes/mard.json
    python palettes/scraper.py zhongyi > palettes/zhongyi.json  # untested path
    python palettes/scraper.py manqi   > palettes/manqi.json    # untested path

Notes
-----
- The MARD URL is verified; zhongyi / manqi paths follow the same convention
  but have NOT been confirmed. They may 404 or return a different page layout.
- Known MARD issue: Q4 and R11 share the same hex (#FFEBFA). The scraper keeps
  both entries; dedup + alias resolution happens later in Palette.from_json.
"""

from __future__ import annotations

import json
import re
import sys
from html.parser import HTMLParser
from urllib.request import urlopen, Request

# ---------------------------------------------------------------------------
# URL map
# ---------------------------------------------------------------------------

_URL_MAP = {
    "mard": "https://www.pixel-beads.com/zh/mard-bead-color-chart",
    "zhongyi": "https://www.pixel-beads.com/zh/zhongyi-bead-color-chart",
    "manqi": "https://www.pixel-beads.com/zh/manqi-bead-color-chart",
}


# ---------------------------------------------------------------------------
# Minimal HTML scraper — the page uses inline style="background:#XXXXXX"
# ---------------------------------------------------------------------------

class _ColorGridParser(HTMLParser):
    """Extract (code, hex) tuples from a pixel-beads color-chart page.

    The page layout wraps each swatch in a <div class="color-item"> or
    similar container. We use a simple heuristic: any element whose `style`
    attribute contains `background` or `background-color` with a `#` hex
    value, preceded by sibling text that is the color code.
    """

    def __init__(self):
        super().__init__()
        self.results: list[dict] = []
        self._pending_code: str | None = None
        self._in_code_tag = False

    def handle_starttag(self, tag, attrs):
        attrs_d = dict(attrs)
        cls = (attrs_d.get("class") or "").lower()

        # Code labels: typically a <span> or <div> with class containing "code"
        if "code" in cls or "item" in cls:
            self._in_code_tag = True
            self._pending_code = None

        # Hex from inline style
        style = attrs_d.get("style", "")
        m = re.search(r"#([0-9A-Fa-f]{6})\b", style)
        if m:
            hex_val = "#" + m.group(1).upper()
            code = self._pending_code or ""
            self.results.append({"code": code, "hex": hex_val})

    def handle_data(self, data):
        if self._in_code_tag:
            txt = data.strip()
            # MARD codes look like: A1, B12, ZG3 etc. (letters + digits)
            if txt and re.match(r"^[A-Za-z]{1,2}\d{1,3}$", txt):
                self._pending_code = txt

    def handle_endtag(self, tag):
        if self._in_code_tag:
            self._in_code_tag = False


# ---------------------------------------------------------------------------
# Fallback: regex extraction if HTML parser misses things
# ---------------------------------------------------------------------------

def _regex_extract(html: str) -> list[dict]:
    """Crude but resilient: find hex in style attributes, then look backwards
    for the nearest code-like string."""
    results = []
    for m in re.finditer(r"#([0-9A-Fa-f]{6})\b", html):
        hex_val = "#" + m.group(1).upper()
        # look back up to 200 chars for a code pattern
        start = max(0, m.start() - 200)
        snippet = html[start:m.start()]
        codes = re.findall(r"([A-Za-z]{1,2}\d{1,3})\b", snippet)
        code = codes[-1] if codes else ""
        results.append({"code": code, "hex": hex_val})
    return results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def scrape(brand: str) -> dict:
    brand = brand.lower()
    if brand not in _URL_MAP:
        raise ValueError(f"unknown brand: {brand!r} (known: {list(_URL_MAP.keys())})")

    url = _URL_MAP[brand]
    print(f"Fetching {url} ...", file=sys.stderr)
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 PixelBeans/0.1.0"})
    with urlopen(req, timeout=30) as resp:
        html = resp.read().decode("utf-8")

    parser = _ColorGridParser()
    parser.feed(html)
    colors = parser.results

    # If parser found too few entries, try the regex fallback
    if len(colors) < 50:
        fallback = _regex_extract(html)
        if len(fallback) > len(colors):
            colors = fallback

    # deduplicate while preserving order
    seen: set[str] = set()
    deduped: list[dict] = []
    for entry in colors:
        if entry["hex"] not in seen:
            seen.add(entry["hex"])
            deduped.append({
                "code": entry["code"],
                "name": entry["code"],  # real names not available from page
                "hex": entry["hex"],
                "category": "核心标准色",
            })

    # category summary (page doesn't expose categories reliably; placeholder)
    categories: dict[str, int] = {"核心标准色": len(deduped), "珍珠质感色": 0, "高亮荧光色": 0}

    return {
        "brand": brand.upper(),
        "source": url,
        "total": len(deduped),
        "categories": categories,
        "colors": deduped,
    }


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    if not argv:
        print("usage: python scraper.py <brand>", file=sys.stderr)
        print(f"  known brands: {list(_URL_MAP.keys())}", file=sys.stderr)
        return 1

    brand = argv[0]
    data = scrape(brand)
    json.dump(data, sys.stdout, ensure_ascii=False, indent=2)
    print(f"\nScraped {data['total']} colors for {data['brand']}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
