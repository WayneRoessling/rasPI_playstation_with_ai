"""Render diagram batch 2: D-2.2 (sim screenshot), D-4.1 + D-4.2 (SVG → PNG).

Headless Chromium via Playwright. No cairo / native deps required.
Run from the repo root: `python docs/user-manuals/source/_render_batch2.py`.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from playwright.async_api import async_playwright

REPO_ROOT = Path(__file__).resolve().parents[3]
SRC = REPO_ROOT / "docs" / "user-manuals" / "source"
IMG = REPO_ROOT / "docs" / "user-manuals" / "images"

SIM_URL = "http://127.0.0.1:8765/"
SCALE = 2  # device_scale_factor — produces ~2x DPI output

# Diagrams to render: (source_svg_basename, viewBox_w, viewBox_h)
SVG_TARGETS = [
    ("D-4.1", 1200, 400),
    ("D-4.2", 1100, 560),
]


HTML_WRAPPER = """<!doctype html>
<html><head><meta charset="utf-8">
<style>
html, body {{ margin: 0; padding: 0; background: #fff; }}
body {{ width: {w}px; height: {h}px; }}
svg {{ display: block; width: {w}px; height: {h}px; }}
</style>
</head><body>{svg}</body></html>"""


async def render_svg(playwright_, svg_id: str, vb_w: int, vb_h: int) -> None:
    svg_path = SRC / f"{svg_id}.svg"
    out_path = IMG / f"{svg_id}.png"
    svg = svg_path.read_text(encoding="utf-8")
    html = HTML_WRAPPER.format(w=vb_w, h=vb_h, svg=svg)

    browser = await playwright_.chromium.launch()
    context = await browser.new_context(
        viewport={"width": vb_w, "height": vb_h},
        device_scale_factor=SCALE,
    )
    page = await context.new_page()
    await page.set_content(html, wait_until="load")
    # Find the SVG element on the page and screenshot exactly that.
    locator = page.locator("svg")
    await locator.wait_for(state="visible")
    await locator.screenshot(path=str(out_path), omit_background=False)
    await browser.close()
    print(f"  rendered {svg_id}.svg -> {out_path.relative_to(REPO_ROOT)}")


async def capture_sim(playwright_) -> None:
    """Drive the simulator to a representative state and screenshot it."""
    out_path = IMG / "D-2.2.png"
    browser = await playwright_.chromium.launch()
    context = await browser.new_context(
        viewport={"width": 1400, "height": 900},
        device_scale_factor=SCALE,
    )
    page = await context.new_page()
    await page.goto(SIM_URL, wait_until="domcontentloaded")

    # Wait for the WS to flip to "connected" — the panel.js code sets the
    # #status element's text and class to "connected" when the socket opens.
    try:
        await page.wait_for_function(
            "() => { const el = document.getElementById('status');"
            " return el && /connected/i.test(el.textContent); }",
            timeout=10_000,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"  WARNING: connected status not seen ({exc!r}); proceeding anyway.")

    # Allow render to settle (LED grid, switch row, OLED canvases populated).
    await page.wait_for_timeout(800)

    # Optional: nudge the panel so it doesn't look empty.
    # Click the first two toggle switches if they exist.
    try:
        switches = page.locator("#switch-row .switch")
        n = await switches.count()
        for i in (0, 2, 4):
            if i < n:
                await switches.nth(i).click()
                await page.wait_for_timeout(120)
    except Exception:
        pass

    # Toggle PIR motion (single click — fires a momentary event).
    try:
        await page.locator("#pir").click(timeout=1500)
    except Exception:
        pass

    # Set the key to ARM so master OLED has a state worth showing.
    try:
        await page.select_option("#key-pos", "ARM")
    except Exception:
        pass

    # Let the protocol log accumulate a few frames.
    await page.wait_for_timeout(600)

    await page.screenshot(path=str(out_path), full_page=True)
    await browser.close()
    print(f"  captured sim screenshot -> {out_path.relative_to(REPO_ROOT)}")


async def main() -> None:
    IMG.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as p:
        print("Rendering SVG diagrams ...")
        for svg_id, w, h in SVG_TARGETS:
            await render_svg(p, svg_id, w, h)
        print("Capturing simulator screenshot (D-2.2) ...")
        await capture_sim(p)
    print("Done.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(130)
