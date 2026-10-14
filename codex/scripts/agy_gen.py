#!/usr/bin/env python3
"""
agy_gen.py -- ref2game "command" generator that draws with the Antigravity CLI (agy), i.e. on the user's
Google subscription instead of a paid API key.

  python3 agy_gen.py --prompt-file F --out art/raw/NAME.png --size 1536x1024 [--name NAME]
                     [--model MODEL] [--timeout 600] [REF ...]

ref2game.json:
  "generator": { "provider": "command", "opaque": ["bg_sky*", "*_tex"],
    "command": { "template": "python3 <skill>/scripts/agy_gen.py --prompt-file {prompt_file} --out {out} --size {size} --name {name} {refs}",
                 "max_refs": 4, "timeout": 900 } }

How it works. agy has no image tool of its own; its built-in "image-generator" subagent has
generate_image(Prompt, ImagePaths, AspectRatio, ImageName), which saves a JPEG to
~/.gemini/antigravity-cli/brain/<conversation>/<ImageName>_<ms>.jpg. This script asks agy (print mode) to hand the
prompt to that subagent verbatim for exactly one call, finds the file by its unique ImageName (safe with parallel
batches and with other agy sessions), and writes it to --out as PNG.

Limits: aspect ratios only (the nearest of RATIOS; gen.py resizes/pads to the exact size); JPEG output, so no
native alpha (use --alpha key; for pixel art run gen.py pixel to re-snap); the subscription's quota; ~30-90 s per image.
"""
import argparse
import glob
import json
import math
import os
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import time

from PIL import Image

BRAIN = os.path.join(os.environ.get("AGY_HOME", os.path.expanduser("~/.gemini/antigravity-cli")), "brain")
# UNVERIFIED: the aspect ratios Gemini image models document; generate_image's own list is not published.
RATIOS = ["1:1", "3:2", "2:3", "4:3", "3:4", "4:5", "5:4", "16:9", "9:16", "21:9"]

MSG = """Invoke the image-generator subagent once and wait for its reply. Pass it exactly this task:

Call generate_image EXACTLY ONCE with:
  ImageName: {tag}
  AspectRatio: {ar}
  ImagePaths: {refs}
  Prompt: the text between <PROMPT> and </PROMPT> below, verbatim, character for character.
Do not rewrite, shorten, translate or extend the prompt. Do not open the reference files, do not judge the result,
do not regenerate or retry. After the one call, reply with the saved file path and stop.

<PROMPT>
{prompt}
</PROMPT>

When the subagent replies, answer with only the saved file path. Do nothing else: no other tools, no files."""


def nearest_ratio(w, h):
    t = math.log(w / h)
    return min(RATIOS, key=lambda r: abs(math.log(int(r.split(":")[0]) / int(r.split(":")[1])) - t))


def find(tag):
    fs = [p for p in glob.glob(os.path.join(BRAIN, "*", "*.*"))
          if os.path.basename(p).lower().startswith(tag.lower() + "_")
          and os.path.splitext(p)[1].lower() in (".jpg", ".jpeg", ".png", ".webp")]
    return sorted(fs, key=os.path.getmtime)


def main():
    ap = argparse.ArgumentParser(description="ref2game generator on the Antigravity CLI (agy) subscription")
    ap.add_argument("--prompt-file", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--size", default="1024x1024")
    ap.add_argument("--name", default="img")
    ap.add_argument("--model", default="", help="agy --model for the calling agent (agy models)")
    ap.add_argument("--timeout", type=float, default=600)
    ap.add_argument("refs", nargs="*")
    a = ap.parse_args()

    if not shutil.which("agy"):
        sys.exit("agy (Antigravity CLI) is not on PATH")
    w, h = (int(v) for v in a.size.lower().split("x"))
    ar = nearest_ratio(w, h)
    refs = [os.path.abspath(r) for r in a.refs]
    for r in refs:
        if not os.path.isfile(r):
            sys.exit(f"no such reference: {r}")
    prompt = open(a.prompt_file, encoding="utf-8").read().strip()
    # agy lowercases the saved file name, so the tag is lowercase and matched case-insensitively
    tag = ("r2g_" + re.sub(r"[^A-Za-z0-9]+", "_", a.name).strip("_")[:40] + "_" + secrets.token_hex(4)).lower()
    msg = MSG.format(tag=tag, ar=ar, refs=json.dumps(refs), prompt=prompt)

    cmd = ["agy", "-p", msg, "--print-timeout", f"{int(a.timeout)}s"]
    if a.model:
        cmd += ["--model", a.model]
    t0 = time.time()
    print(f"agy_gen: {a.name} -> {tag}, aspect {ar} for {w}x{h}, {len(refs)} ref(s)", flush=True)
    work = tempfile.mkdtemp(prefix="agy_gen_")                   # agy's workspace: nothing of the project in it
    try:
        p = subprocess.run(cmd, cwd=work, capture_output=True, text=True, timeout=a.timeout + 30)
        print(p.stdout.strip()[-1500:], flush=True)
        if p.stderr.strip():
            print(p.stderr.strip()[-1500:], file=sys.stderr, flush=True)
    except subprocess.TimeoutExpired:
        print("agy_gen: agy print mode timed out; still looking for the file", flush=True)
    finally:
        shutil.rmtree(work, ignore_errors=True)

    # print mode can return while the subagent is still drawing: wait for the file by its tag
    deadline, last = t0 + a.timeout, None
    while True:
        fs = find(tag)
        if fs:
            size = os.path.getsize(fs[0])
            if size and size == last:
                break
            last = size
        elif time.time() > deadline:
            sys.exit(f"agy_gen: no image named {tag}_* in {BRAIN} after {a.timeout:.0f}s")
        time.sleep(2)
    if len(fs) > 1:
        print(f"agy_gen: the subagent made {len(fs)} images; using the first", flush=True)
    out = os.path.splitext(a.out)[0] + ".png"
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    im = Image.open(fs[0])
    im.convert("RGBA" if "A" in im.getbands() else "RGB").save(out)
    print(f"agy_gen: {fs[0]} -> {out} {im.size} in {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
