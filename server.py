#!/usr/bin/env python3
"""
LAN offline STT HTTP server for fw-mini-sdk watches.

  POST /transcribe
    body: audio/wav  OR  raw 16 kHz mono s16le PCM
    OR multipart form field "file" / "audio"
  -> {"text": "...", "ok": true}

  GET /health -> {"ok": true, "model": "..."}
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import urlparse

from app_paths import app_dir, default_model_dir
from asr_engine import load_recognizer, transcribe_bytes
from download_model import ensure_model


class State:
    recognizer = None
    model_dir: Path = default_model_dir()


def _json_response(handler: BaseHTTPRequestHandler, code: int, obj: dict) -> None:
    body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    handler.send_response(code)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.end_headers()
    handler.wfile.write(body)


def _parse_multipart(body: bytes, content_type: str) -> Optional[bytes]:
    m = re.search(r"boundary=([^;]+)", content_type, flags=re.I)
    if not m:
        return None
    boundary = m.group(1).strip().strip('"').encode("ascii", "ignore")
    if not boundary:
        return None
    parts = body.split(b"--" + boundary)
    for part in parts:
        if b"Content-Disposition:" not in part:
            continue
        # Prefer named file/audio fields; otherwise first file part
        head, _, data = part.partition(b"\r\n\r\n")
        if not data:
            continue
        if data.endswith(b"\r\n"):
            data = data[:-2]
        if b"filename=" in head or b'name="file"' in head or b'name="audio"' in head:
            return data
    return None


class Handler(BaseHTTPRequestHandler):
    server_version = "fw-mini-pc-stt/1.0"

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path in ("/", "/health"):
            _json_response(
                self,
                200,
                {
                    "ok": True,
                    "service": "pc_stt",
                    "mode": "offline_utterance",
                    "model": str(State.model_dir.name),
                    "endpoints": {"health": "GET /health", "transcribe": "POST /transcribe"},
                },
            )
            return
        _json_response(self, 404, {"ok": False, "error": "not found"})

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path != "/transcribe":
            _json_response(self, 404, {"ok": False, "error": "not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        if length <= 0:
            _json_response(self, 400, {"ok": False, "error": "empty body"})
            return
        if length > 16 * 1024 * 1024:
            _json_response(self, 413, {"ok": False, "error": "body too large (>16MB)"})
            return
        body = self.rfile.read(length)
        ctype = (self.headers.get("Content-Type") or "").lower()
        audio = body
        if "multipart/form-data" in ctype:
            parsed = _parse_multipart(body, ctype)
            if not parsed:
                _json_response(self, 400, {"ok": False, "error": "no file in multipart"})
                return
            audio = parsed
        t0 = time.time()
        try:
            text = transcribe_bytes(State.recognizer, audio)
        except Exception as e:
            _json_response(self, 500, {"ok": False, "error": str(e)})
            return
        ms = int((time.time() - t0) * 1000)
        _json_response(
            self,
            200,
            {"ok": True, "text": text, "bytes": len(audio), "ms": ms},
        )


def main(argv: Optional[list] = None) -> int:
    ap = argparse.ArgumentParser(description="Offline utterance STT HTTP server")
    ap.add_argument("--host", default="0.0.0.0", help="Bind address (LAN: 0.0.0.0)")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--model-dir", type=Path, default=None)
    ap.add_argument("--threads", type=int, default=2)
    ap.add_argument("--provider", default="cpu", choices=("cpu", "cuda", "directml"))
    ap.add_argument(
        "--auto-download",
        action="store_true",
        default=True,
        help="Download model next to the exe if missing (default: on)",
    )
    ap.add_argument(
        "--no-auto-download",
        action="store_true",
        help="Do not download model automatically",
    )
    args = ap.parse_args(argv)

    State.model_dir = Path(args.model_dir) if args.model_dir else default_model_dir()
    if args.no_auto_download:
        args.auto_download = False
    if args.auto_download and not (
        (State.model_dir / "tokens.txt").is_file()
        and list(State.model_dir.glob("model*.onnx"))
    ):
        print("Model missing; downloading (~200MB, one-time) ...", flush=True)
        try:
            State.model_dir = ensure_model(app_dir() / "models")
        except Exception as e:
            print(f"Auto-download failed: {e}", file=sys.stderr)
            return 1

    print(f"App dir: {app_dir()}", flush=True)
    print(f"Loading model from {State.model_dir} ...", flush=True)
    try:
        State.recognizer = load_recognizer(
            State.model_dir, num_threads=args.threads, provider=args.provider
        )
    except Exception as e:
        print(f"Failed to load model: {e}", file=sys.stderr)
        print("Copy models/ next to the exe, or run with --auto-download.", file=sys.stderr)
        return 1

    httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Listening on http://{args.host}:{args.port}", flush=True)
    print("  GET  /health", flush=True)
    print("  POST /transcribe  (WAV or raw 16k mono s16le)", flush=True)
    print("Press Ctrl+C to stop.", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
