#!/usr/bin/env python3
"""POST a WAV to the local STT server (curl alternative on Windows)."""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("wav", type=Path, help="Path to WAV or raw PCM file")
    ap.add_argument("--url", default="http://127.0.0.1:8765/transcribe")
    ap.add_argument(
        "--raw",
        action="store_true",
        help="Send as application/octet-stream (raw PCM) instead of audio/wav",
    )
    args = ap.parse_args()
    if not args.wav.is_file():
        print(f"File not found: {args.wav}", file=sys.stderr)
        return 1

    data = args.wav.read_bytes()
    ctype = "application/octet-stream" if args.raw else "audio/wav"
    req = urllib.request.Request(
        args.url,
        data=data,
        method="POST",
        headers={"Content-Type": ctype},
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        print(e.read().decode("utf-8", errors="replace"), file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Request failed: {e}", file=sys.stderr)
        print("Is the server running?  python server.py", file=sys.stderr)
        return 1

    try:
        obj = json.loads(body)
    except json.JSONDecodeError:
        print(body)
        return 1
    print(json.dumps(obj, ensure_ascii=False, indent=2))
    return 0 if obj.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
