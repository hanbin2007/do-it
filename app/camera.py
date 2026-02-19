"""Camera discovery and access utilities."""

from __future__ import annotations

import os
from typing import Optional

import cv2

# (index, device_name, resolution)
CameraInfo = tuple[int, Optional[str], Optional[tuple[int, int]]]


def open_camera(index: int) -> cv2.VideoCapture:
    """Open a camera by index; use DirectShow on Windows."""
    if os.name == "nt" and hasattr(cv2, "CAP_DSHOW"):
        return cv2.VideoCapture(index, cv2.CAP_DSHOW)
    return cv2.VideoCapture(index)


def list_camera_device_names() -> list[str]:
    """Return device names on Windows via pygrabber; empty list on others."""
    if os.name != "nt":
        return []
    try:
        from pygrabber.dshow_graph import FilterGraph
    except Exception:
        return []
    try:
        names = FilterGraph().get_input_devices()
    except Exception:
        return []
    return [str(n).strip() for n in names if str(n).strip()]


def list_available_cameras(max_index: int = 5) -> list[CameraInfo]:
    """Probe camera indices 0..max_index and return those that open."""
    available: list[CameraInfo] = []
    names = list_camera_device_names()

    for index in range(max_index + 1):
        cap = open_camera(index)
        if not cap.isOpened():
            cap.release()
            continue
        ok, frame = cap.read()
        resolution = None
        if ok and frame is not None:
            h, w = frame.shape[:2]
            resolution = (w, h)
        device_name = names[index] if index < len(names) else None
        available.append((index, device_name, resolution))
        cap.release()

    return available


def format_camera_option(info: CameraInfo) -> str:
    """Human-readable string for a camera entry."""
    index, device_name, resolution = info
    text = f"[{index}]"
    if device_name:
        text += f" {device_name}"
    if resolution is not None:
        text += f" ({resolution[0]}×{resolution[1]})"
    return text
