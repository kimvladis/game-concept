#!/usr/bin/env python3
"""
gemini_image.py -- image generator on the paid Gemini API (Nano Banana 2.1 by default), key in GEMINI_API_KEY.

  python3 gemini_image.py --prompt-file F --out art/raw/NAME.png --size 1536x1024 [--name NAME]
                          [--model gemini-nano-banana-2.1] [--image-size auto|1K|2K|4K] [--thinking minimal|medium|high]
                          [REF ...]

ref2game.json ("command" provider):
  "generator": { "provider": "command", "opaque": ["bg_sky*", "*_tex"],
    "command": { "template": "python3 <skill>/scripts/gemini_image.py --prompt-file {prompt_file} --out {out} --size {size} --name {name} {refs}",
                 "max_refs": 10, "timeout": 300 } }

How it works: one POST to /v1beta/interactions with response_format {type: image, mime_type: image/jpeg (the only
value the API accepts), aspect_ratio, image_size}; reference images go as base64 image blocks after the prompt, in order (Image 1, 2, ...).
The last image of the model_output step is written to --out as PNG; thought images are skipped.

Limits: aspect ratios only (the nearest of RATIOS; gen.py resizes/pads to the exact size); image_size tiers 1K/2K/4K
(auto = the smallest tier that covers --size); JPEG only, so no alpha (use --alpha key); paid per image, no free tier. Prints the
usage and a cost estimate at the list prices in RATES (check ai.google.dev/gemini-api/docs/pricing).
"""
import argparse
import base64
import io
import json
import math
import os
import sys
import time
import urllib.error
import urllib.request

from PIL import Image

API = "https://generativelanguage.googleapis.com/v1beta/interactions"
MODEL = "gemini-nano-banana-2.1"
RATIOS = ["1:1", "3:2", "2:3", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"]
TIER_LONG = {"1K": 1376, "2K": 2752, "4K": 5504}        # long side of a 16:9 image per tier (measured: 1K = 1376x768)
# USD per 1M tokens: input, text/thinking output, image output (pricing page, 2026-10)
RATES = {"gemini-nano-banana-2.1": (1.50, 7.50, 30.0), "gemini-3.1-flash-image": (0.50, 3.0, 60.0),
         "gemini-3.1-flash-lite-image": (0.25, 1.50, 30.0), "gemini-3-pro-image": (2.00, 12.0, 120.0)}
RETRY = [10, 30]                                          # seconds before a retry on 429 / 5xx
MIME = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}


def nearest_ratio(w, h):
    t = math.log(w / h)
    return min(RATIOS, key=lambda r: abs(math.log(int(r.split(":")[0]) / int(r.split(":")[1])) - t))


def tier_for(w, h):
    for t, long_side in TIER_LONG.items():
        if max(w, h) <= long_side * 1.05:
            return t
    return "4K"


def post(body, key, timeout):
    req = urllib.request.Request(API, data=json.dumps(body).encode(),
                                 headers={"x-goog-api-key": key, "Content-Type": "application/json"})
    for wait in RETRY + [None]:
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            msg = e.read().decode(errors="replace")[:1000]
            if wait is None or not (e.code == 429 or e.code >= 500):
                sys.exit(f"gemini_image: HTTP {e.code}: {msg}")
            print(f"gemini_image: HTTP {e.code}, retry in {wait}s: {msg[:200]}", flush=True)
        except (urllib.error.URLError, TimeoutError) as e:
            if wait is None:
                sys.exit(f"gemini_image: {e}")
            print(f"gemini_image: {e}, retry in {wait}s", flush=True)
        time.sleep(wait)
    sys.exit("gemini_image: unreachable")


def cost(model, usage):
    r = RATES.get(model)
    if not r:
        return None
    img = sum(m.get("tokens", 0) for m in usage.get("output_tokens_by_modality", []) if m.get("modality") == "image")
    text = usage.get("total_output_tokens", 0) - img + usage.get("total_thought_tokens", 0)
    return (usage.get("total_input_tokens", 0) * r[0] + text * r[1] + img * r[2]) / 1e6


def main():
    ap = argparse.ArgumentParser(description="image generator on the Gemini API (Nano Banana 2.1)")
    ap.add_argument("--prompt-file", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--size", default="1024x1024")
    ap.add_argument("--name", default="img")
    ap.add_argument("--model", default="", help=f"default {MODEL}")
    ap.add_argument("--image-size", default="auto", choices=["auto", "1K", "2K", "4K"])
    ap.add_argument("--thinking", default="", choices=["", "minimal", "medium", "high"], help="default: the model's")
    ap.add_argument("--timeout", type=float, default=240)
    ap.add_argument("refs", nargs="*")
    a = ap.parse_args()

    key = os.environ.get("GEMINI_API_KEY", "")
    if not key:
        sys.exit("gemini_image: GEMINI_API_KEY is not set")
    model = a.model or MODEL
    w, h = (int(v) for v in a.size.lower().split("x"))
    ar, tier = nearest_ratio(w, h), (tier_for(w, h) if a.image_size == "auto" else a.image_size)
    prompt = open(a.prompt_file, encoding="utf-8").read().strip()
    content = [{"type": "text", "text": prompt}]
    for r in a.refs:
        ext = os.path.splitext(r)[1].lower()
        if not os.path.isfile(r):
            sys.exit(f"gemini_image: no such reference: {r}")
        if ext in MIME:
            data, mime = open(r, "rb").read(), MIME[ext]
        else:                                             # anything else PIL reads goes as PNG
            buf = io.BytesIO()
            Image.open(r).save(buf, "PNG")
            data, mime = buf.getvalue(), "image/png"
        content.append({"type": "image", "mime_type": mime, "data": base64.b64encode(data).decode()})
    body = {"model": model, "input": [{"type": "user_input", "content": content}],
            "response_format": {"type": "image", "mime_type": "image/jpeg", "aspect_ratio": ar, "image_size": tier}}
    if a.thinking:
        body["generation_config"] = {"thinking_level": a.thinking}

    print(f"gemini_image: {a.name} -> {model}, {ar} {tier} for {w}x{h}, {len(a.refs)} ref(s)", flush=True)
    t0 = time.time()
    d = post(body, key, a.timeout)
    imgs = [c for s in d.get("steps", []) if s.get("type") == "model_output"
            for c in (s.get("content") or []) if c.get("type") == "image" and c.get("data")]
    if not imgs:
        texts = [c.get("text", "") for s in d.get("steps", []) for c in (s.get("content") or []) if c.get("type") == "text"]
        sys.exit("gemini_image: no image in the response (blocked?): status " + str(d.get("status")) + "; "
                 + " ".join(texts)[:600])
    im = Image.open(io.BytesIO(base64.b64decode(imgs[-1]["data"])))
    out = os.path.splitext(a.out)[0] + ".png"
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    im.convert("RGBA" if "A" in im.getbands() else "RGB").save(out)
    usage = d.get("usage", {})
    c = cost(model, usage)
    print(f"gemini_image: -> {out} {im.size} {imgs[-1].get('mime_type')} in {time.time() - t0:.0f}s; "
          f"tokens in {usage.get('total_input_tokens', 0)} out {usage.get('total_output_tokens', 0)} "
          f"thought {usage.get('total_thought_tokens', 0)}" + (f"; ~${c:.4f}" if c is not None else ""), flush=True)


if __name__ == "__main__":
    main()
