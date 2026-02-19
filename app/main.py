"""Application entry point — supports both GUI and CLI modes."""

from __future__ import annotations

import argparse
import sys

from .camera import list_available_cameras, format_camera_option
from .config import DEFAULT_THRESHOLDS, EXERCISE_CHOICES, EXERCISE_LABELS, RunConfig


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Do-It 运动计数器")
    p.add_argument("--camera", type=int, default=None, help="Camera index")
    p.add_argument("--list-cameras", action="store_true", help="List cameras and exit")
    p.add_argument("--max-camera-index", type=int, default=5)
    p.add_argument("--exercise", choices=list(EXERCISE_CHOICES), default=None)
    p.add_argument("--down-angle", type=float, default=None)
    p.add_argument("--up-angle", type=float, default=None)
    p.add_argument("--window-size", type=int, default=5)
    p.add_argument("--voice-every", type=int, default=None)
    p.add_argument("--no-gui", action="store_true", help="Run headless OpenCV mode")
    p.add_argument("--min-detection-confidence", type=float, default=0.5)
    p.add_argument("--min-tracking-confidence", type=float, default=0.5)
    return p.parse_args()


def _run_cli(config: RunConfig) -> None:
    """Fallback: OpenCV-window mode (no CustomTkinter required)."""
    import cv2
    import mediapipe as mp_lib
    import numpy as np
    import time

    from .camera import open_camera
    from .counter import ExerciseCounter
    from .pose import EXTRACTORS
    from .voice import VoiceAnnouncer

    mp_pose = mp_lib.solutions.pose
    mp_draw = mp_lib.solutions.drawing_utils

    cap = open_camera(config.camera_index)
    if not cap.isOpened():
        print(f"Cannot open camera {config.camera_index}")
        return

    counter = ExerciseCounter(config.down_angle, config.up_angle, config.window_size)
    voice = VoiceAnnouncer(config.voice_every)
    extract = EXTRACTORS[config.exercise]
    label = EXERCISE_LABELS[config.exercise]
    prev_time = time.time()

    try:
        with mp_pose.Pose(
            model_complexity=1,
            smooth_landmarks=True,
            min_detection_confidence=config.min_detection_confidence,
            min_tracking_confidence=config.min_tracking_confidence,
        ) as pose:
            while True:
                ok, frame = cap.read()
                if not ok:
                    break
                frame = cv2.flip(frame, 1)
                h, w = frame.shape[:2]
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                result = pose.process(rgb)

                if result.pose_landmarks:
                    lm = result.pose_landmarks.landmark
                    measured = extract(lm, w, h)
                    if measured is not None:
                        done = counter.update(measured)
                        if done:
                            voice.maybe_announce(counter.state.count)
                    mp_draw.draw_landmarks(
                        frame, result.pose_landmarks, mp_pose.POSE_CONNECTIONS,
                        mp_draw.DrawingSpec(color=(50, 220, 255), thickness=2, circle_radius=2),
                        mp_draw.DrawingSpec(color=(255, 170, 40), thickness=2, circle_radius=2),
                    )
                else:
                    counter.clear_window()

                now = time.time()
                fps = 1.0 / max(1e-6, now - prev_time)
                prev_time = now

                cs = counter.state
                info = f"{label} | Count: {cs.count} | {cs.phase} | FPS: {fps:.0f}"
                cv2.putText(frame, info, (16, 36), cv2.FONT_HERSHEY_SIMPLEX,
                            0.8, (0, 255, 0), 2, cv2.LINE_AA)
                cv2.imshow(f"{label} - Do-It", frame)

                key = cv2.waitKey(1) & 0xFF
                if key == ord("q"):
                    break
                if key == ord("r"):
                    counter.reset()
    finally:
        voice.close()
        cap.release()
        cv2.destroyAllWindows()


def main() -> None:
    args = _parse_args()
    cameras = list_available_cameras(args.max_camera_index)

    if args.list_cameras:
        if not cameras:
            print("No camera detected.")
        else:
            for info in cameras:
                print(f"  {format_camera_option(info)}")
        return

    # Decide GUI vs CLI
    use_cli = (
        args.no_gui
        or args.camera is not None
        or args.exercise is not None
        or args.down_angle is not None
        or args.up_angle is not None
        or args.voice_every is not None
    )

    if use_cli:
        ex = args.exercise or "squat"
        dd, du = DEFAULT_THRESHOLDS[ex]
        config = RunConfig(
            camera_index=args.camera or (cameras[0][0] if cameras else 0),
            exercise=ex,
            down_angle=args.down_angle if args.down_angle is not None else dd,
            up_angle=args.up_angle if args.up_angle is not None else du,
            window_size=args.window_size,
            voice_every=args.voice_every if args.voice_every is not None else 0,
            min_detection_confidence=args.min_detection_confidence,
            min_tracking_confidence=args.min_tracking_confidence,
        )
        _run_cli(config)
    else:
        from .ui import launch_ui
        launch_ui(cameras)
