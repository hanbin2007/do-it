"""Threaded video-processing engine with pause/resume support."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Optional

import cv2
import mediapipe as mp
import numpy as np

from .camera import open_camera
from .config import RunConfig
from .counter import CounterState, ExerciseCounter
from .pose import EXTRACTORS
from .voice import VoiceAnnouncer


@dataclass
class EngineSnapshot:
    """Latest state readable by the UI (thread-safe copy)."""

    frame: np.ndarray | None = None
    counter: CounterState = field(default_factory=CounterState)
    fps: float = 0.0
    paused: bool = False
    running: bool = False


class MotionEngine:
    """Background thread: camera → MediaPipe → counter → snapshot.

    The UI reads ``get_snapshot()`` at its own refresh rate.
    """

    def __init__(self, config: RunConfig) -> None:
        self._config = config
        self._counter = ExerciseCounter(
            config.down_angle, config.up_angle, config.window_size
        )
        self._voice = VoiceAnnouncer(config.voice_every)
        self._extract = EXTRACTORS[config.exercise]

        # Threading primitives
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()  # SET = paused
        self._thread: threading.Thread | None = None

        # Latest snapshot (guarded by _lock)
        self._snapshot = EngineSnapshot()

    # ---- lifecycle --------------------------------------------------------

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._pause_event.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        self._pause_event.clear()  # unblock if paused
        if self._thread:
            self._thread.join(timeout=3.0)
        self._voice.close()

    def pause(self) -> None:
        self._pause_event.set()

    def resume(self) -> None:
        self._pause_event.clear()

    @property
    def is_paused(self) -> bool:
        return self._pause_event.is_set()

    def toggle_pause(self) -> bool:
        """Toggle pause. Returns *True* if now paused."""
        if self._pause_event.is_set():
            self._pause_event.clear()
            return False
        self._pause_event.set()
        return True

    def reset_count(self) -> None:
        self._counter.reset()

    # ---- live config updates (called from UI thread) ----------------------

    def update_thresholds(self, down: float, up: float) -> None:
        self._counter.set_thresholds(down, up)

    def update_voice_every(self, every: int) -> None:
        self._voice.set_every(every)

    def switch_exercise(self, exercise: str) -> None:
        """Change exercise type at runtime."""
        self._extract = EXTRACTORS[exercise]
        self._config.exercise = exercise
        self._counter.reset()

    # ---- snapshot reader --------------------------------------------------

    def get_snapshot(self) -> EngineSnapshot:
        with self._lock:
            return EngineSnapshot(
                frame=self._snapshot.frame.copy() if self._snapshot.frame is not None else None,
                counter=self._snapshot.counter,
                fps=self._snapshot.fps,
                paused=self._pause_event.is_set(),
                running=not self._stop_event.is_set(),
            )

    # ---- internal loop ----------------------------------------------------

    def _loop(self) -> None:
        mp_pose = mp.solutions.pose
        mp_draw = mp.solutions.drawing_utils

        cap = open_camera(self._config.camera_index)
        if not cap.isOpened():
            print(f"[Engine] Cannot open camera {self._config.camera_index}")
            return

        prev_time = time.time()

        try:
            with mp_pose.Pose(
                model_complexity=1,
                smooth_landmarks=True,
                min_detection_confidence=self._config.min_detection_confidence,
                min_tracking_confidence=self._config.min_tracking_confidence,
            ) as pose:
                while not self._stop_event.is_set():
                    # While paused, keep camera alive but skip processing
                    if self._pause_event.is_set():
                        time.sleep(0.05)
                        continue

                    ok, frame = cap.read()
                    if not ok:
                        time.sleep(0.01)
                        continue

                    frame = cv2.flip(frame, 1)
                    h, w = frame.shape[:2]
                    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    result = pose.process(rgb)

                    measured = None
                    if result.pose_landmarks:
                        landmarks = result.pose_landmarks.landmark
                        measured = self._extract(landmarks, w, h)

                        if measured is not None:
                            completed = self._counter.update(measured)
                            if completed:
                                self._voice.maybe_announce(self._counter.state.count)
                        # Draw skeleton
                        mp_draw.draw_landmarks(
                            frame,
                            result.pose_landmarks,
                            mp_pose.POSE_CONNECTIONS,
                            mp_draw.DrawingSpec(color=(50, 220, 255), thickness=2, circle_radius=2),
                            mp_draw.DrawingSpec(color=(255, 170, 40), thickness=2, circle_radius=2),
                        )
                    else:
                        self._counter.clear_window()

                    now = time.time()
                    fps = 1.0 / max(1e-6, now - prev_time)
                    prev_time = now

                    with self._lock:
                        self._snapshot.frame = frame
                        self._snapshot.counter = self._counter.state
                        self._snapshot.fps = fps
                        self._snapshot.paused = False
                        self._snapshot.running = True
        finally:
            cap.release()
            with self._lock:
                self._snapshot.running = False
