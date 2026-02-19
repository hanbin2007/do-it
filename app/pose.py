"""Pose-landmark angle extraction using MediaPipe."""

from __future__ import annotations

from typing import Optional

import mediapipe as mp
import numpy as np

_mp_pose = mp.solutions.pose


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------

def calculate_angle(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
    """Return angle ABC in degrees (0–180)."""
    ba = a - b
    bc = c - b
    norm_ba = np.linalg.norm(ba)
    norm_bc = np.linalg.norm(bc)
    if norm_ba == 0 or norm_bc == 0:
        return 180.0
    cosine = np.clip(np.dot(ba, bc) / (norm_ba * norm_bc), -1.0, 1.0)
    return float(np.degrees(np.arccos(cosine)))


def _lm_xy(landmark, w: int, h: int) -> np.ndarray:
    return np.array([landmark.x * w, landmark.y * h], dtype=np.float32)


# ---------------------------------------------------------------------------
# Joint helpers
# ---------------------------------------------------------------------------

def _joint_angle_vis(
    landmarks, w: int, h: int, p1, p2, p3
) -> tuple[float, float]:
    """Angle at *p2* formed by p1-p2-p3, plus average visibility."""
    angle = calculate_angle(
        _lm_xy(landmarks[p1], w, h),
        _lm_xy(landmarks[p2], w, h),
        _lm_xy(landmarks[p3], w, h),
    )
    vis = (landmarks[p1].visibility + landmarks[p2].visibility + landmarks[p3].visibility) / 3.0
    return angle, vis


def _pick_reliable(
    left_angle: float, left_vis: float,
    right_angle: float, right_vis: float,
    min_vis: float = 0.5,
) -> Optional[float]:
    l_ok = left_vis > min_vis
    r_ok = right_vis > min_vis
    if l_ok and r_ok:
        return (left_angle + right_angle) / 2.0
    if l_ok:
        return left_angle
    if r_ok:
        return right_angle
    return None


# ---------------------------------------------------------------------------
# Public extractors
# ---------------------------------------------------------------------------

def extract_squat_angle(landmarks, w: int, h: int) -> Optional[float]:
    PL = _mp_pose.PoseLandmark
    la, lv = _joint_angle_vis(landmarks, w, h, PL.LEFT_HIP, PL.LEFT_KNEE, PL.LEFT_ANKLE)
    ra, rv = _joint_angle_vis(landmarks, w, h, PL.RIGHT_HIP, PL.RIGHT_KNEE, PL.RIGHT_ANKLE)
    return _pick_reliable(la, lv, ra, rv)


def extract_half_pushup_angle(landmarks, w: int, h: int) -> Optional[float]:
    PL = _mp_pose.PoseLandmark
    la, lv = _joint_angle_vis(landmarks, w, h, PL.LEFT_SHOULDER, PL.LEFT_ELBOW, PL.LEFT_WRIST)
    ra, rv = _joint_angle_vis(landmarks, w, h, PL.RIGHT_SHOULDER, PL.RIGHT_ELBOW, PL.RIGHT_WRIST)
    return _pick_reliable(la, lv, ra, rv)


EXTRACTORS: dict[str, callable] = {
    "squat": extract_squat_angle,
    "half_pushup": extract_half_pushup_angle,
}
