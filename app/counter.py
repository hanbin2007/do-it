"""Exercise counting state machine."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

import numpy as np


@dataclass
class CounterState:
    """Snapshot of counter state, safe to read from another thread."""

    count: int = 0
    phase: str = "UP"
    smoothed_angle: float | None = None


class ExerciseCounter:
    """Tracks rep count through an UP/DOWN state machine on smoothed angle."""

    def __init__(self, down_angle: float, up_angle: float, window_size: int = 5) -> None:
        self.down_angle = down_angle
        self.up_angle = up_angle
        self._window: deque[float] = deque(maxlen=window_size)
        self._count = 0
        self._phase = "UP"  # "UP" or "DOWN"
        self._smoothed: float | None = None

    # ----- mutators --------------------------------------------------------

    def update(self, measured_angle: float) -> bool:
        """Feed a new measured angle. Returns *True* when a rep is completed."""
        self._window.append(measured_angle)
        self._smoothed = float(np.mean(self._window))
        completed = False

        if self._phase == "UP" and self._smoothed <= self.down_angle:
            self._phase = "DOWN"
        elif self._phase == "DOWN" and self._smoothed >= self.up_angle:
            self._phase = "UP"
            self._count += 1
            completed = True

        return completed

    def reset(self) -> None:
        self._count = 0
        self._phase = "UP"
        self._window.clear()
        self._smoothed = None

    def clear_window(self) -> None:
        self._window.clear()
        self._smoothed = None

    # ----- accessors -------------------------------------------------------

    @property
    def state(self) -> CounterState:
        return CounterState(
            count=self._count,
            phase=self._phase,
            smoothed_angle=self._smoothed,
        )

    # Allow external live adjustment of thresholds
    def set_thresholds(self, down: float, up: float) -> None:
        self.down_angle = down
        self.up_angle = up

    def set_window_size(self, size: int) -> None:
        new_window: deque[float] = deque(self._window, maxlen=max(1, size))
        self._window = new_window
