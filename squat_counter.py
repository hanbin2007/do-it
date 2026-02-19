import argparse
import os
import queue
import threading
import time
from collections import deque
from dataclasses import dataclass

import cv2
import mediapipe as mp
import numpy as np


CameraInfo = tuple[int, str | None, tuple[int, int] | None]
EXERCISE_CHOICES = ("squat", "half_pushup")
EXERCISE_LABELS = {
    "squat": "Squat",
    "half_pushup": "Half Push-Up",
}
DEFAULT_THRESHOLDS = {
    "squat": (95.0, 160.0),
    "half_pushup": (120.0, 160.0),
}


@dataclass
class RunConfig:
    camera_index: int
    camera_name: str | None
    exercise: str
    down_angle: float
    up_angle: float
    window_size: int
    min_detection_confidence: float
    min_tracking_confidence: float
    voice_every: int


class VoiceAnnouncer:
    def __init__(self, every: int) -> None:
        self.every = max(0, every)
        self.enabled = self.every > 0
        self._queue: queue.Queue[str | None] = queue.Queue()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._pyttsx3 = None

        if not self.enabled:
            return

        try:
            import pyttsx3

            self._pyttsx3 = pyttsx3
        except Exception as exc:
            print(f"Voice disabled: failed to import pyttsx3 ({exc})")
            self.enabled = False
            return

        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()

    def _worker(self) -> None:
        try:
            engine = self._pyttsx3.init()
        except Exception as exc:
            print(f"Voice disabled: cannot initialize TTS engine ({exc})")
            self.enabled = False
            return

        while not self._stop_event.is_set():
            try:
                text = self._queue.get(timeout=0.2)
            except queue.Empty:
                continue
            if text is None:
                break

            try:
                engine.say(text)
                engine.runAndWait()
            except Exception:
                pass

        try:
            engine.stop()
        except Exception:
            pass

    def maybe_announce(self, count: int) -> None:
        if not self.enabled or self.every <= 0 or count <= 0:
            return
        if count % self.every != 0:
            return
        self._queue.put(f"{count}")

    def close(self) -> None:
        if not self.enabled:
            return
        self._stop_event.set()
        self._queue.put(None)
        if self._thread is not None:
            self._thread.join(timeout=1.0)


def calculate_angle(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
    """Return angle ABC in degrees."""
    ba = a - b
    bc = c - b

    norm_ba = np.linalg.norm(ba)
    norm_bc = np.linalg.norm(bc)
    if norm_ba == 0 or norm_bc == 0:
        return 180.0

    cosine = np.dot(ba, bc) / (norm_ba * norm_bc)
    cosine = np.clip(cosine, -1.0, 1.0)
    return float(np.degrees(np.arccos(cosine)))


def lm_to_xy(landmark, width: int, height: int) -> np.ndarray:
    return np.array([landmark.x * width, landmark.y * height], dtype=np.float32)


def open_camera(index: int) -> cv2.VideoCapture:
    if os.name == "nt" and hasattr(cv2, "CAP_DSHOW"):
        return cv2.VideoCapture(index, cv2.CAP_DSHOW)
    return cv2.VideoCapture(index)


def list_camera_device_names() -> list[str]:
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

    cleaned: list[str] = []
    for name in names:
        text = str(name).strip()
        if text:
            cleaned.append(text)
    return cleaned


def list_available_cameras(max_index: int) -> list[CameraInfo]:
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
            height, width = frame.shape[:2]
            resolution = (width, height)

        device_name = names[index] if index < len(names) else None
        available.append((index, device_name, resolution))
        cap.release()

    return available


def format_camera_option(camera_info: CameraInfo) -> str:
    index, device_name, resolution = camera_info
    text = f"[{index}]"
    if device_name:
        text += f" {device_name}"
    if resolution is not None:
        text += f" ({resolution[0]}x{resolution[1]})"
    return text


def print_camera_list(available: list[CameraInfo]) -> None:
    if not available:
        print("No camera detected.")
        return

    print("Available cameras:")
    for info in available:
        print(f"  - {format_camera_option(info)}")


def choose_camera_index_cli(available: list[CameraInfo]) -> int:
    print_camera_list(available)
    default_index = available[0][0]

    while True:
        try:
            raw = input(f"Select camera index [{default_index}]: ").strip()
        except EOFError:
            print(f"No interactive input detected, using camera [{default_index}].")
            return default_index

        if raw == "":
            return default_index
        if raw.isdigit():
            selected = int(raw)
            if any(index == selected for index, _, _ in available):
                return selected
        print("Invalid camera index, please choose one from the list.")


def launch_start_gui(
    available_cameras: list[CameraInfo],
    default_camera_index: int,
    default_exercise: str,
    default_down_angle: float,
    default_up_angle: float,
    default_window_size: int,
    default_voice_every: int,
) -> tuple[str, dict[str, object] | None]:
    try:
        import tkinter as tk
        from tkinter import messagebox, ttk
    except Exception as exc:
        print(f"GUI unavailable: {exc}")
        return ("unavailable", None)

    if not available_cameras:
        return ("cancel", None)

    selected: dict[str, object] = {}
    cancelled = {"value": True}

    camera_options = [format_camera_option(info) for info in available_cameras]
    camera_option_to_index = {format_camera_option(info): info[0] for info in available_cameras}
    default_camera_option = camera_options[0]
    for option in camera_options:
        if option.startswith(f"[{default_camera_index}]"):
            default_camera_option = option
            break

    exercise_display_to_value = {
        "Squat": "squat",
        "Half Push-Up": "half_pushup",
    }
    exercise_value_to_display = {v: k for k, v in exercise_display_to_value.items()}

    root = tk.Tk()
    root.title("Motion Counter Launcher")
    root.resizable(False, False)
    root.configure(padx=14, pady=12)

    camera_var = tk.StringVar(value=default_camera_option)
    exercise_var = tk.StringVar(value=exercise_value_to_display.get(default_exercise, "Squat"))
    down_var = tk.StringVar(value=f"{default_down_angle:.1f}")
    up_var = tk.StringVar(value=f"{default_up_angle:.1f}")
    window_var = tk.StringVar(value=str(default_window_size))
    voice_var = tk.StringVar(value=str(default_voice_every))

    ttk.Label(root, text="Camera").grid(row=0, column=0, sticky="w", pady=4)
    camera_combo = ttk.Combobox(
        root,
        textvariable=camera_var,
        values=camera_options,
        state="readonly",
        width=42,
    )
    camera_combo.grid(row=0, column=1, sticky="we", pady=4)

    ttk.Label(root, text="Exercise").grid(row=1, column=0, sticky="w", pady=4)
    exercise_combo = ttk.Combobox(
        root,
        textvariable=exercise_var,
        values=list(exercise_display_to_value.keys()),
        state="readonly",
        width=42,
    )
    exercise_combo.grid(row=1, column=1, sticky="we", pady=4)

    ttk.Label(root, text="Down Angle").grid(row=2, column=0, sticky="w", pady=4)
    down_entry = ttk.Entry(root, textvariable=down_var, width=16)
    down_entry.grid(row=2, column=1, sticky="w", pady=4)

    ttk.Label(root, text="Up Angle").grid(row=3, column=0, sticky="w", pady=4)
    up_entry = ttk.Entry(root, textvariable=up_var, width=16)
    up_entry.grid(row=3, column=1, sticky="w", pady=4)

    ttk.Label(root, text="Smooth Window").grid(row=4, column=0, sticky="w", pady=4)
    window_spin = ttk.Spinbox(root, from_=1, to=30, textvariable=window_var, width=14)
    window_spin.grid(row=4, column=1, sticky="w", pady=4)

    ttk.Label(root, text="Voice Every N Reps").grid(row=5, column=0, sticky="w", pady=4)
    voice_spin = ttk.Spinbox(root, from_=0, to=50, textvariable=voice_var, width=14)
    voice_spin.grid(row=5, column=1, sticky="w", pady=4)

    hint = "Voice: set 0 to disable, set 1/2/5... to announce every N reps."
    ttk.Label(root, text=hint).grid(row=6, column=0, columnspan=2, sticky="w", pady=(2, 8))

    def on_exercise_change(_: object = None) -> None:
        exercise_value = exercise_display_to_value[exercise_var.get()]
        default_down, default_up = DEFAULT_THRESHOLDS[exercise_value]
        down_var.set(f"{default_down:.1f}")
        up_var.set(f"{default_up:.1f}")

    def on_start() -> None:
        try:
            camera_index = camera_option_to_index[camera_var.get()]
            exercise_value = exercise_display_to_value[exercise_var.get()]
            down_angle = float(down_var.get().strip())
            up_angle = float(up_var.get().strip())
            window_size = int(window_var.get().strip())
            voice_every = int(voice_var.get().strip())
        except Exception:
            messagebox.showerror("Invalid Input", "Please check numeric fields.")
            return

        if up_angle <= down_angle:
            messagebox.showerror("Invalid Threshold", "Up Angle must be larger than Down Angle.")
            return
        if window_size < 1:
            messagebox.showerror("Invalid Window", "Smooth Window must be >= 1.")
            return
        if voice_every < 0:
            messagebox.showerror("Invalid Voice Setting", "Voice Every N must be >= 0.")
            return

        selected.update(
            {
                "camera_index": camera_index,
                "exercise": exercise_value,
                "down_angle": down_angle,
                "up_angle": up_angle,
                "window_size": window_size,
                "voice_every": voice_every,
            }
        )
        cancelled["value"] = False
        root.destroy()

    def on_cancel() -> None:
        root.destroy()

    exercise_combo.bind("<<ComboboxSelected>>", on_exercise_change)

    button_row = ttk.Frame(root)
    button_row.grid(row=7, column=0, columnspan=2, sticky="e", pady=(4, 0))
    ttk.Button(button_row, text="Cancel", command=on_cancel).grid(row=0, column=0, padx=(0, 8))
    ttk.Button(button_row, text="Start", command=on_start).grid(row=0, column=1)

    root.protocol("WM_DELETE_WINDOW", on_cancel)
    root.mainloop()

    if cancelled["value"]:
        return ("cancel", None)
    return ("ok", selected)


def joint_angle_and_visibility(
    landmarks,
    width: int,
    height: int,
    first_point,
    middle_point,
    third_point,
) -> tuple[float, float]:
    first = lm_to_xy(landmarks[first_point], width, height)
    middle = lm_to_xy(landmarks[middle_point], width, height)
    third = lm_to_xy(landmarks[third_point], width, height)
    angle = calculate_angle(first, middle, third)
    visibility = (
        landmarks[first_point].visibility
        + landmarks[middle_point].visibility
        + landmarks[third_point].visibility
    ) / 3.0
    return angle, visibility


def pick_reliable_angle(
    left_angle: float,
    left_vis: float,
    right_angle: float,
    right_vis: float,
    min_visibility: float = 0.5,
) -> float | None:
    if left_vis > min_visibility and right_vis > min_visibility:
        return (left_angle + right_angle) / 2.0
    if left_vis > min_visibility:
        return left_angle
    if right_vis > min_visibility:
        return right_angle
    return None


def extract_squat_angle(landmarks, width: int, height: int, mp_pose_module) -> float | None:
    left_angle, left_vis = joint_angle_and_visibility(
        landmarks,
        width,
        height,
        mp_pose_module.PoseLandmark.LEFT_HIP,
        mp_pose_module.PoseLandmark.LEFT_KNEE,
        mp_pose_module.PoseLandmark.LEFT_ANKLE,
    )
    right_angle, right_vis = joint_angle_and_visibility(
        landmarks,
        width,
        height,
        mp_pose_module.PoseLandmark.RIGHT_HIP,
        mp_pose_module.PoseLandmark.RIGHT_KNEE,
        mp_pose_module.PoseLandmark.RIGHT_ANKLE,
    )
    return pick_reliable_angle(left_angle, left_vis, right_angle, right_vis)


def extract_half_pushup_angle(landmarks, width: int, height: int, mp_pose_module) -> float | None:
    left_angle, left_vis = joint_angle_and_visibility(
        landmarks,
        width,
        height,
        mp_pose_module.PoseLandmark.LEFT_SHOULDER,
        mp_pose_module.PoseLandmark.LEFT_ELBOW,
        mp_pose_module.PoseLandmark.LEFT_WRIST,
    )
    right_angle, right_vis = joint_angle_and_visibility(
        landmarks,
        width,
        height,
        mp_pose_module.PoseLandmark.RIGHT_SHOULDER,
        mp_pose_module.PoseLandmark.RIGHT_ELBOW,
        mp_pose_module.PoseLandmark.RIGHT_WRIST,
    )
    return pick_reliable_angle(left_angle, left_vis, right_angle, right_vis)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Webcam motion counter.")
    parser.add_argument("--camera", type=int, default=None, help="Camera index.")
    parser.add_argument("--list-cameras", action="store_true", help="List available cameras and exit.")
    parser.add_argument(
        "--max-camera-index",
        type=int,
        default=5,
        help="Max camera index to probe when listing/selecting (default: 5).",
    )
    parser.add_argument(
        "--exercise",
        type=str,
        choices=list(EXERCISE_CHOICES),
        default=None,
        help="Exercise type: squat or half_pushup.",
    )
    parser.add_argument("--down-angle", type=float, default=None, help="Down threshold angle.")
    parser.add_argument("--up-angle", type=float, default=None, help="Up threshold angle.")
    parser.add_argument("--window-size", type=int, default=5, help="Smoothing window size.")
    parser.add_argument(
        "--voice-every",
        type=int,
        default=None,
        help="Announce every N reps. Set 0 to disable.",
    )
    parser.add_argument("--no-gui", action="store_true", help="Use CLI selection instead of start GUI.")
    parser.add_argument(
        "--min-detection-confidence",
        type=float,
        default=0.5,
        help="Pose detector minimum confidence (default: 0.5)",
    )
    parser.add_argument(
        "--min-tracking-confidence",
        type=float,
        default=0.5,
        help="Pose tracker minimum confidence (default: 0.5)",
    )
    return parser.parse_args()


def find_camera_name(available_cameras: list[CameraInfo], camera_index: int) -> str | None:
    for index, name, _ in available_cameras:
        if index == camera_index:
            return name
    return None


def build_run_config(args: argparse.Namespace, available_cameras: list[CameraInfo]) -> RunConfig | None:
    if args.max_camera_index < 0:
        raise ValueError("--max-camera-index must be >= 0")
    if args.window_size < 1:
        raise ValueError("--window-size must be >= 1")
    if args.voice_every is not None and args.voice_every < 0:
        raise ValueError("--voice-every must be >= 0")

    default_exercise = args.exercise or "squat"
    default_down, default_up = DEFAULT_THRESHOLDS[default_exercise]
    default_voice_every = args.voice_every if args.voice_every is not None else 0

    run_without_gui = (
        args.no_gui
        or args.camera is not None
        or args.exercise is not None
        or args.down_angle is not None
        or args.up_angle is not None
        or args.voice_every is not None
    )

    if not available_cameras and args.camera is None:
        raise RuntimeError(
            f"No camera detected between index 0 and {args.max_camera_index}. "
            "Try increasing --max-camera-index or check camera permissions."
        )

    if not run_without_gui and available_cameras:
        gui_status, gui_result = launch_start_gui(
            available_cameras=available_cameras,
            default_camera_index=available_cameras[0][0],
            default_exercise=default_exercise,
            default_down_angle=args.down_angle if args.down_angle is not None else default_down,
            default_up_angle=args.up_angle if args.up_angle is not None else default_up,
            default_window_size=args.window_size,
            default_voice_every=default_voice_every,
        )
        if gui_status == "ok" and gui_result is not None:
            camera_index = int(gui_result["camera_index"])
            exercise = str(gui_result["exercise"])
            down_angle = float(gui_result["down_angle"])
            up_angle = float(gui_result["up_angle"])
            window_size = int(gui_result["window_size"])
            voice_every = int(gui_result["voice_every"])
            camera_name = find_camera_name(available_cameras, camera_index)
            return RunConfig(
                camera_index=camera_index,
                camera_name=camera_name,
                exercise=exercise,
                down_angle=down_angle,
                up_angle=up_angle,
                window_size=window_size,
                min_detection_confidence=args.min_detection_confidence,
                min_tracking_confidence=args.min_tracking_confidence,
                voice_every=voice_every,
            )
        if gui_status == "cancel":
            print("Canceled by user.")
            return None
        print("Falling back to CLI selection because GUI is unavailable.")

    available_indices = {index for index, _, _ in available_cameras}
    if args.camera is not None:
        camera_index = args.camera
        if available_cameras and camera_index not in available_indices:
            print(f"Warning: camera index {camera_index} not found in probed list, trying to open anyway.")
    else:
        if len(available_cameras) == 1:
            camera_index = available_cameras[0][0]
        else:
            camera_index = choose_camera_index_cli(available_cameras)

    exercise = default_exercise
    down_angle = args.down_angle if args.down_angle is not None else DEFAULT_THRESHOLDS[exercise][0]
    up_angle = args.up_angle if args.up_angle is not None else DEFAULT_THRESHOLDS[exercise][1]
    if up_angle <= down_angle:
        raise ValueError("--up-angle must be larger than --down-angle")

    camera_name = find_camera_name(available_cameras, camera_index)
    return RunConfig(
        camera_index=camera_index,
        camera_name=camera_name,
        exercise=exercise,
        down_angle=down_angle,
        up_angle=up_angle,
        window_size=args.window_size,
        min_detection_confidence=args.min_detection_confidence,
        min_tracking_confidence=args.min_tracking_confidence,
        voice_every=default_voice_every,
    )


def build_status_panel(lines: list[str], phase: str) -> np.ndarray:
    width = 600
    top = 22
    line_h = 34
    height = top + line_h * len(lines) + 18
    panel = np.full((height, width, 3), 26, dtype=np.uint8)

    cv2.rectangle(panel, (0, 0), (width - 1, height - 1), (70, 70, 70), 1)
    for i, text in enumerate(lines):
        y = top + i * line_h
        color = (238, 238, 238)
        if text.startswith("Phase:"):
            color = (100, 245, 100) if phase == "UP" else (50, 160, 255)
        elif text.startswith("Exercise:"):
            color = (120, 220, 255)
        cv2.putText(
            panel,
            text,
            (16, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.76,
            color,
            2,
            cv2.LINE_AA,
        )

    return panel


def run_counter(config: RunConfig) -> None:
    mp_pose = mp.solutions.pose
    mp_draw = mp.solutions.drawing_utils

    cap = open_camera(config.camera_index)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open camera index {config.camera_index}")

    exercise_label = EXERCISE_LABELS[config.exercise]
    metric_label = "Knee Angle" if config.exercise == "squat" else "Elbow Angle"
    camera_label = f"[{config.camera_index}] {config.camera_name}" if config.camera_name else f"[{config.camera_index}]"
    if len(camera_label) > 42:
        camera_label = camera_label[:39] + "..."
    voice_label = "off" if config.voice_every <= 0 else f"every {config.voice_every} reps"

    count = 0
    phase = "UP"
    angle_window: deque[float] = deque(maxlen=config.window_size)
    prev_time = time.time()
    announcer = VoiceAnnouncer(config.voice_every)
    video_window_title = f"{exercise_label} Camera"
    status_window_title = "Motion Status"
    windows_positioned = False

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
                height, width = frame.shape[:2]

                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                result = pose.process(rgb)

                measured_angle = None
                smoothed_angle = None

                if result.pose_landmarks:
                    landmarks = result.pose_landmarks.landmark
                    if config.exercise == "squat":
                        measured_angle = extract_squat_angle(landmarks, width, height, mp_pose)
                    else:
                        measured_angle = extract_half_pushup_angle(landmarks, width, height, mp_pose)

                    if measured_angle is not None:
                        angle_window.append(measured_angle)
                        smoothed_angle = float(np.mean(angle_window))

                        if phase == "UP" and smoothed_angle <= config.down_angle:
                            phase = "DOWN"
                        elif phase == "DOWN" and smoothed_angle >= config.up_angle:
                            phase = "UP"
                            count += 1
                            announcer.maybe_announce(count)

                    mp_draw.draw_landmarks(
                        frame,
                        result.pose_landmarks,
                        mp_pose.POSE_CONNECTIONS,
                        mp_draw.DrawingSpec(color=(50, 220, 255), thickness=2, circle_radius=2),
                        mp_draw.DrawingSpec(color=(255, 170, 40), thickness=2, circle_radius=2),
                    )
                else:
                    angle_window.clear()

                now = time.time()
                fps = 1.0 / max(1e-6, now - prev_time)
                prev_time = now

                lines = [
                    f"Exercise: {exercise_label}",
                    f"Count: {count}",
                    f"Phase: {phase}",
                    f"{metric_label}: {smoothed_angle:.1f}" if smoothed_angle is not None else f"{metric_label}: N/A",
                    f"Threshold: down<={config.down_angle:.1f}, up>={config.up_angle:.1f}",
                    f"FPS: {fps:.1f}",
                    f"Camera: {camera_label}",
                    f"Voice: {voice_label}",
                    "Keys: q quit, r reset",
                ]
                status_panel = build_status_panel(lines, phase)

                cv2.imshow(video_window_title, frame)
                cv2.imshow(status_window_title, status_panel)
                if not windows_positioned:
                    try:
                        cv2.moveWindow(video_window_title, 48, 48)
                        cv2.moveWindow(status_window_title, 96 + frame.shape[1], 48)
                    except cv2.error:
                        pass
                    windows_positioned = True

                key = cv2.waitKey(1) & 0xFF
                if key == ord("q"):
                    break
                if key == ord("r"):
                    count = 0
                    phase = "UP"
                    angle_window.clear()

                try:
                    video_visible = cv2.getWindowProperty(video_window_title, cv2.WND_PROP_VISIBLE)
                    status_visible = cv2.getWindowProperty(status_window_title, cv2.WND_PROP_VISIBLE)
                    if video_visible < 1 or status_visible < 1:
                        break
                except cv2.error:
                    break

    finally:
        announcer.close()
        cap.release()
        cv2.destroyAllWindows()


def main() -> None:
    args = parse_args()
    available_cameras = list_available_cameras(args.max_camera_index)

    if args.list_cameras:
        print_camera_list(available_cameras)
        return

    config = build_run_config(args, available_cameras)
    if config is None:
        return

    print(
        f"Starting {EXERCISE_LABELS[config.exercise]} | "
        f"camera [{config.camera_index}] | "
        f"down={config.down_angle:.1f} up={config.up_angle:.1f} | "
        f"voice_every={config.voice_every}"
    )
    run_counter(config)


if __name__ == "__main__":
    main()
