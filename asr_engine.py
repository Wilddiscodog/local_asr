#!/usr/bin/env python3
"""Offline Chinese ASR wrapper (sherpa-onnx Paraformer)."""
from __future__ import annotations

import wave
from io import BytesIO
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
import sherpa_onnx

from app_paths import default_model_dir  # noqa: F401 — re-export


def resolve_paraformer(model_dir: Path) -> Tuple[Path, Path]:
    tokens = model_dir / "tokens.txt"
    for name in ("model.int8.onnx", "model.onnx"):
        p = model_dir / name
        if p.is_file() and tokens.is_file():
            return p, tokens
    raise FileNotFoundError(
        f"Paraformer model not found under {model_dir}. "
        f"Place model next to the exe, or run download_model / --auto-download."
    )


def load_recognizer(
    model_dir: Optional[Path] = None,
    num_threads: int = 2,
    provider: str = "cpu",
) -> sherpa_onnx.OfflineRecognizer:
    model_dir = Path(model_dir) if model_dir else default_model_dir()
    paraformer, tokens = resolve_paraformer(model_dir)
    return sherpa_onnx.OfflineRecognizer.from_paraformer(
        paraformer=str(paraformer),
        tokens=str(tokens),
        num_threads=num_threads,
        sample_rate=16000,
        feature_dim=80,
        decoding_method="greedy_search",
        provider=provider,
    )


def pcm16_mono_to_float(pcm: bytes, sample_rate: int) -> Tuple[np.ndarray, int]:
    if len(pcm) < 2:
        return np.zeros(0, dtype=np.float32), sample_rate
    samples = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0
    return samples, sample_rate


def wav_bytes_to_float(data: bytes) -> Tuple[np.ndarray, int]:
    """Decode WAV (or fall back to raw 16 kHz s16le PCM)."""
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WAVE":
        with wave.open(BytesIO(data), "rb") as wf:
            ch = wf.getnchannels()
            sw = wf.getsampwidth()
            sr = wf.getframerate()
            n = wf.getnframes()
            raw = wf.readframes(n)
        if sw != 2:
            raise ValueError(f"Only 16-bit PCM WAV supported, got sampwidth={sw}")
        samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
        if ch > 1:
            samples = samples.reshape(-1, ch).mean(axis=1)
        return samples, int(sr)
    # Raw body: assume 16 kHz mono s16le (watch / walkie format)
    return pcm16_mono_to_float(data, 16000)


def resample_if_needed(samples: np.ndarray, sr: int, target: int = 16000) -> np.ndarray:
    if sr == target or samples.size == 0:
        return samples
    # Linear resample; good enough for ASR smoke / short utterances
    duration = samples.shape[0] / float(sr)
    n_out = max(1, int(round(duration * target)))
    x_old = np.linspace(0.0, 1.0, num=samples.shape[0], endpoint=False)
    x_new = np.linspace(0.0, 1.0, num=n_out, endpoint=False)
    return np.interp(x_new, x_old, samples).astype(np.float32)


def transcribe_samples(
    recognizer: sherpa_onnx.OfflineRecognizer,
    samples: np.ndarray,
    sample_rate: int,
) -> str:
    samples = resample_if_needed(np.asarray(samples, dtype=np.float32), sample_rate, 16000)
    if samples.size == 0:
        return ""
    stream = recognizer.create_stream()
    stream.accept_waveform(16000, samples)
    recognizer.decode_stream(stream)
    return (stream.result.text or "").strip()


def transcribe_bytes(
    recognizer: sherpa_onnx.OfflineRecognizer,
    data: bytes,
) -> str:
    samples, sr = wav_bytes_to_float(data)
    return transcribe_samples(recognizer, samples, sr)


def transcribe_file(
    recognizer: sherpa_onnx.OfflineRecognizer,
    path: Path,
) -> str:
    return transcribe_bytes(recognizer, Path(path).read_bytes())
