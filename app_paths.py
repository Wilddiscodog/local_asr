#!/usr/bin/env python3
"""Resolve install / model dirs for source run and frozen exe."""
from __future__ import annotations

import sys
from pathlib import Path


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False)) and hasattr(sys, "_MEIPASS")


def app_dir() -> Path:
    """Writable install root: next to the .exe, or tools/pc_stt in source."""
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def bundle_dir() -> Path:
    """PyInstaller extract dir (read-only resources); same as app_dir in source."""
    if is_frozen():
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent


def default_model_dir() -> Path:
    return app_dir() / "models" / "sherpa-onnx-paraformer-zh-2023-09-14"
