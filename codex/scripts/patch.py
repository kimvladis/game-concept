#!/usr/bin/env python3
"""
patch.py -- put a region of an earlier concept version back into an edited one.

  python3 patch.py --from v1a.png --into v1a-e1.png --box 330,430,420,495 --out v1a-e1p.png [--feather 6]

Image edits keep the layout pixel-aligned but re-render everything, so text and small details can break in areas the
edit was not about (e.g. "ROCKS" -> "ROCRS"), and asking the generator to fix the spelling keeps the error. The earlier
version still has it right: this pastes that box back with a feathered edge. Before pasting it compares a ring around
the box in both images and refuses when they differ (the layout moved), unless --force.
Box: x0,y0,x1,y1 in pixels of --into; both images must have the same size.
"""
import argparse
import sys

import numpy as np
from PIL import Image, ImageFilter

RING_MAX = 18.0   # mean |diff| (0-255) around the box; unchanged areas of an edit measure ~5-9, a changed area ~20


def main():
    ap = argparse.ArgumentParser(description="put a box of an earlier concept version back into an edited one")
    ap.add_argument("--from", dest="src", required=True, help="earlier version that has the region right")
    ap.add_argument("--into", required=True, help="edited version to fix")
    ap.add_argument("--box", required=True, help="x0,y0,x1,y1 in pixels")
    ap.add_argument("--out", required=True)
    ap.add_argument("--feather", type=int, default=6, help="soft edge width in px")
    ap.add_argument("--force", action="store_true", help="paste even if the layout around the box moved")
    a = ap.parse_args()

    src = Image.open(a.src).convert("RGB")
    dst = Image.open(a.into).convert("RGB")
    if src.size != dst.size:
        sys.exit(f"sizes differ: {src.size} vs {dst.size}")
    x0, y0, x1, y1 = (int(v) for v in a.box.split(","))
    w, h = dst.size
    if not (0 <= x0 < x1 <= w and 0 <= y0 < y1 <= h):
        sys.exit(f"box {a.box} is outside the {w}x{h} image")

    r = a.feather * 2 + 8                                       # ring just outside the box
    rx0, ry0, rx1, ry1 = max(0, x0 - r), max(0, y0 - r), min(w, x1 + r), min(h, y1 + r)
    d = np.abs(np.asarray(src, int) - np.asarray(dst, int)).mean(2)
    ring = np.zeros_like(d, bool)
    ring[ry0:ry1, rx0:rx1] = True
    ring[y0:y1, x0:x1] = False
    ring_diff = float(d[ring].mean())
    print(f"patch: ring diff {ring_diff:.1f} (unchanged areas ~5-9)")
    if ring_diff > RING_MAX and not a.force:
        sys.exit(f"patch: the layout around the box moved (ring diff {ring_diff:.1f} > {RING_MAX}); "
                 "pick a box in an area the edit did not touch, or --force")

    mask = Image.new("L", dst.size, 0)
    mask.paste(255, (x0 + a.feather, y0 + a.feather, x1 - a.feather, y1 - a.feather))
    mask = mask.filter(ImageFilter.GaussianBlur(a.feather / 2)) if a.feather else mask
    Image.composite(src, dst, mask).save(a.out)
    print(f"patch: {a.src} box {a.box} -> {a.out}")


if __name__ == "__main__":
    main()
