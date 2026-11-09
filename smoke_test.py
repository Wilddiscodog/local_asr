#!/usr/bin/env python3
"""Decode one local WAV with the offline model (no HTTP)."""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from asr_engine import default_model_dir, load_recognizer, transcribe_file


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "wav",
        nargs="?",
        type=Path,
        help="WAV path (default: model test_wavs/0.wav)",
    )
    ap.add_argument("--model-dir", type=Path, default=None)
    ap.add_argument("--threads", type=int, default=2)
    args = ap.parse_args()

    model_dir = Path(args.model_dir) if args.model_dir else default_model_dir()
    wav = args.wav
    if wav is None:
        wav = model_dir / "test_wavs" / "0.wav"
    if not wav.is_file():
        print(f"WAV not found: {wav}", file=sys.stderr)
        print("Run download_model.py first, or pass a WAV path.", file=sys.stderr)
        return 1

    print(f"Model: {model_dir}")
    print(f"WAV:   {wav}")
    t0 = time.time()
    rec = load_recognizer(model_dir, num_threads=args.threads)
    text = transcribe_file(rec, wav)
    ms = int((time.time() - t0) * 1000)
    print(f"Text:  {text}")
    print(f"Time:  {ms} ms (incl. model load)")
    return 0 if text else 2


if __name__ == "__main__":
    raise SystemExit(main())
