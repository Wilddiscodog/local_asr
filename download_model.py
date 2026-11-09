#!/usr/bin/env python3
"""Download sherpa-onnx Chinese Paraformer offline model (+ test wavs)."""
from __future__ import annotations

import argparse
import sys
import tarfile
import urllib.request
from pathlib import Path

DEFAULT_URL = (
    "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/"
    "sherpa-onnx-paraformer-zh-2023-09-14.tar.bz2"
)
# HuggingFace / ModelScope mirrors often work better in CN; override with --url
MIRROR_HF = (
    "https://huggingface.co/csukuangfj/sherpa-onnx-paraformer-zh-2023-09-14/"
    "resolve/main/model.tar.bz2"
)


def _download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading:\n  {url}\n  -> {dest}")
    req = urllib.request.Request(url, headers={"User-Agent": "fw-mini-sdk-pc-stt/1.0"})
    with urllib.request.urlopen(req, timeout=600) as resp, open(dest, "wb") as out:
        total = resp.headers.get("Content-Length")
        total_n = int(total) if total and total.isdigit() else None
        done = 0
        while True:
            chunk = resp.read(1024 * 256)
            if not chunk:
                break
            out.write(chunk)
            done += len(chunk)
            if total_n:
                pct = 100.0 * done / total_n
                print(f"\r  {done / 1e6:.1f}/{total_n / 1e6:.1f} MB ({pct:.0f}%)", end="")
            else:
                print(f"\r  {done / 1e6:.1f} MB", end="")
        print()


def _extract(archive: Path, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"Extracting to {out_dir} ...")
    with tarfile.open(archive, "r:bz2") as tf:
        tf.extractall(out_dir)
    # Prefer the known folder name; else first dir containing model*.onnx
    known = out_dir / "sherpa-onnx-paraformer-zh-2023-09-14"
    if known.is_dir():
        return known
    for p in sorted(out_dir.iterdir()):
        if p.is_dir() and list(p.glob("model*.onnx")):
            return p
    raise SystemExit(f"Could not find model folder under {out_dir}")


def ensure_model(
    models_root: Path,
    url: str = DEFAULT_URL,
    keep_archive: bool = False,
) -> Path:
    """Ensure Paraformer model exists under models_root; return model dir."""
    models_root = Path(models_root)
    models_root.mkdir(parents=True, exist_ok=True)
    archive = models_root / "sherpa-onnx-paraformer-zh-2023-09-14.tar.bz2"
    model_dir = models_root / "sherpa-onnx-paraformer-zh-2023-09-14"
    if (model_dir / "tokens.txt").is_file() and list(model_dir.glob("model*.onnx")):
        print(f"Model already present: {model_dir}", flush=True)
        return model_dir

    try:
        _download(url, archive)
    except Exception as e1:
        print(f"Primary URL failed: {e1}", flush=True)
        if url != DEFAULT_URL:
            raise
        print("Trying HuggingFace mirror ...", flush=True)
        _download(MIRROR_HF, archive)

    found = _extract(archive, models_root)
    if not keep_archive:
        try:
            archive.unlink()
        except OSError:
            pass
    print(f"OK: {found}", flush=True)
    for name in ("model.int8.onnx", "model.onnx", "tokens.txt"):
        p = found / name
        print(f"  {'+' if p.is_file() else '-'} {name}", flush=True)
    tw = found / "test_wavs"
    if tw.is_dir():
        print(f"  + test_wavs/ ({len(list(tw.glob('*.wav')))} wav)", flush=True)
    return found


def main() -> int:
    from app_paths import app_dir

    ap = argparse.ArgumentParser(description="Download offline Chinese ASR model")
    ap.add_argument(
        "--dir",
        type=Path,
        default=None,
        help="Extract root (default: <app>/models)",
    )
    ap.add_argument("--url", default=DEFAULT_URL, help="Model archive URL")
    ap.add_argument(
        "--keep-archive",
        action="store_true",
        help="Keep .tar.bz2 after extract",
    )
    args = ap.parse_args()
    models_root = Path(args.dir) if args.dir else (app_dir() / "models")
    try:
        ensure_model(models_root, url=args.url, keep_archive=args.keep_archive)
    except Exception as e:
        print(f"Download failed: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
