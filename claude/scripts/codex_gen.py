#!/usr/bin/env python3
"""
codex_gen.py -- concept generator that draws with the Codex CLI's built-in image_gen tool, i.e. on the user's ChatGPT
plan instead of an image API key. Same flags as agy_gen.py and gemini_image.py.

  python3 codex_gen.py --prompt-file F --out concept/v1a.png --size 1920x1080 [--name NAME]
                       [--model MODEL] [--timeout 600] [REF ...]

How it works. The script runs `codex exec` in an empty temp workspace and asks the agent to pass the prompt to
image_gen verbatim, exactly once, with the REF files as referenced images, then copy the result into the workspace.
If the agent forgets to copy, the image is taken from $CODEX_HOME/generated_images/<session id>/. The result is written
to --out as PNG at the size the tool chose (never upscaled).

Limits: the tool picks the exact size, the script only asks for the orientation and aspect (16:9 comes out about
1672x941); your Codex limits; ~2-3 min per image. --model sets the calling agent's model, not the image model.
"""
import argparse
import glob
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

from PIL import Image

CODEX_HOME = os.environ.get("CODEX_HOME", os.path.expanduser("~/.codex"))
RATIOS = ["1:1", "3:2", "2:3", "4:3", "3:4", "16:9", "9:16", "21:9"]

MSG = """Use your built-in image_gen tool (not a CLI, script or API call) to generate ONE image, {shape}. \
Pass the prompt below to the tool verbatim, without rewording, shortening or adding anything.{refs} \
Call the tool exactly once: do not judge the result, do not regenerate or retry. Then copy the generated PNG file \
into this workspace as {target}. Do not write any code or edit other files.

{prompt}"""


def nearest_ratio(w, h):
    t = math.log(w / h)
    return min(RATIOS, key=lambda r: abs(math.log(int(r.split(":")[0]) / int(r.split(":")[1])) - t))


def shape(w, h):
    ar = nearest_ratio(w, h)
    if w > h:
        return f"landscape {ar} (the widest landscape size the tool supports)"
    if h > w:
        return f"portrait {ar} (the tallest portrait size the tool supports)"
    return "square 1:1"


def main():
    ap = argparse.ArgumentParser(description="concept generator on the Codex CLI built-in image_gen")
    ap.add_argument("--prompt-file", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--size", default="1920x1080")
    ap.add_argument("--name", default="img")
    ap.add_argument("--model", default="", help="codex -m for the calling agent (the image model is the tool's own)")
    ap.add_argument("--timeout", type=float, default=600)
    ap.add_argument("refs", nargs="*")
    a = ap.parse_args()

    exe = shutil.which("codex")
    if not exe:
        sys.exit("codex CLI is not on PATH (npm i -g @openai/codex, then codex login)")
    st = subprocess.run([exe, "login", "status"], capture_output=True, text=True, timeout=30)
    if st.returncode != 0:
        sys.exit(f"codex is not logged in: {(st.stdout + st.stderr).strip()[-200:]} (run: codex login)")
    w, h = (int(v) for v in a.size.lower().split("x"))
    refs = [os.path.abspath(r) for r in a.refs]
    for r in refs:
        if not os.path.isfile(r):
            sys.exit(f"no such reference: {r}")
    prompt = open(a.prompt_file, encoding="utf-8").read().strip()
    ref_line = ""
    if refs:
        listed = "; ".join(f"Image {i + 1} = {r}" for i, r in enumerate(refs))
        ref_line = f" Give the tool these files as referenced images, in this order: {listed}."
    target = "out.png"
    msg = MSG.format(shape=shape(w, h), refs=ref_line, target=target, prompt=prompt)

    work = tempfile.mkdtemp(prefix="codex_gen_")                  # codex's workspace: nothing of the project in it
    cmd = [exe, "exec", "--skip-git-repo-check", "-s", "workspace-write", "-C", work,
           "-c", 'model_reasoning_effort="low"']
    if a.model:
        cmd += ["-m", a.model]
    for r in refs:
        cmd += ["-i", r]
    cmd += ["--", "-"]
    print(f"codex_gen: {a.name}, {shape(w, h)} for {w}x{h}, {len(refs)} ref(s)", flush=True)
    t0 = time.time()
    try:
        try:
            p = subprocess.run(cmd, input=msg, capture_output=True, text=True, timeout=a.timeout)
            text = p.stdout + "\n" + p.stderr
        except subprocess.TimeoutExpired as e:
            text = (e.stdout or b"").decode(errors="replace") if isinstance(e.stdout, bytes) else (e.stdout or "")
            print(f"codex_gen: codex timed out after {a.timeout:.0f}s; still looking for the image", flush=True)
        sid = (re.search(r"session id:\s*([0-9a-f-]{8,})", text) or [None, None])[1]
        src = os.path.join(work, target)
        if not (os.path.isfile(src) and os.path.getsize(src)):
            # the agent did not copy: take the newest image of this session (or named in the log)
            cands = [c for c in re.findall(r"(/[^\s'\"`]*generated_images/[^\s'\"`]+?\.(?:png|webp|jpg))", text)
                     if os.path.isfile(c) and os.path.getmtime(c) >= t0 - 1]
            if not cands and sid:
                cands = sorted(glob.glob(os.path.join(CODEX_HOME, "generated_images", sid, "*")), key=os.path.getmtime)
            if not cands:
                tail = "\n".join(text.strip().splitlines()[-12:])
                sys.exit(f"codex_gen: codex finished without an image (session {sid})\n--- tail ---\n{tail}")
            src = cands[-1]
            print(f"codex_gen: codex did not copy the file; using {src}", flush=True)
        out = os.path.splitext(a.out)[0] + ".png"
        os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
        im = Image.open(src)
        im.convert("RGBA" if "A" in im.getbands() else "RGB").save(out)
        print(f"codex_gen: session {sid} -> {out} {im.size} in {time.time() - t0:.0f}s", flush=True)
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()
