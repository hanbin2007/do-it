"""Shared configuration, constants, and data classes."""

from __future__ import annotations

from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Exercise definitions
# ---------------------------------------------------------------------------

EXERCISE_CHOICES = ("squat", "half_pushup")

EXERCISE_LABELS: dict[str, str] = {
    "squat": "深蹲 Squat",
    "half_pushup": "半俯卧撑 Half Push-Up",
}

DEFAULT_THRESHOLDS: dict[str, tuple[float, float]] = {
    "squat": (95.0, 160.0),
    "half_pushup": (120.0, 160.0),
}

METRIC_LABELS: dict[str, str] = {
    "squat": "膝关节角度",
    "half_pushup": "肘关节角度",
}


# ---------------------------------------------------------------------------
# Run configuration
# ---------------------------------------------------------------------------

@dataclass
class RunConfig:
    """All parameters needed to run a counting session."""

    camera_index: int = 0
    camera_name: str | None = None
    exercise: str = "squat"
    down_angle: float = 95.0
    up_angle: float = 160.0
    window_size: int = 5
    min_detection_confidence: float = 0.5
    min_tracking_confidence: float = 0.5
    voice_every: int = 0
