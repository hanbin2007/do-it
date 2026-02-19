"""Modern CustomTkinter UI with real-time controls."""

from __future__ import annotations

import sys
import tkinter as tk
from typing import Optional

import cv2
import numpy as np

try:
    import customtkinter as ctk
    from PIL import Image, ImageDraw, ImageFont, ImageTk
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Install with: pip install customtkinter Pillow")
    sys.exit(1)

from .camera import CameraInfo, format_camera_option, list_available_cameras
from .config import (
    DEFAULT_THRESHOLDS,
    EXERCISE_CHOICES,
    EXERCISE_LABELS,
    METRIC_LABELS,
    RunConfig,
)
from .engine import MotionEngine

# ---------------------------------------------------------------------------
# Color palette
# ---------------------------------------------------------------------------
_C = {
    "bg": "#1a1a2e",
    "card": "#16213e",
    "card_border": "#0f3460",
    "accent": "#e94560",
    "accent_hover": "#ff6b81",
    "green": "#00e676",
    "yellow": "#ffd600",
    "blue": "#448aff",
    "text": "#e0e0e0",
    "text_dim": "#8892b0",
    "up_phase": "#00e676",
    "down_phase": "#ff6b81",
}

REFRESH_MS = 33  # ~30 fps UI refresh


class MotionCounterApp(ctk.CTk):
    """Main application window."""

    def __init__(self, cameras: list[CameraInfo]) -> None:
        super().__init__()

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.title("Do-It 运动计数器")
        self.configure(fg_color=_C["bg"])
        self.minsize(1100, 680)
        self.geometry("1200x720")

        self._cameras = cameras
        self._camera_map = {format_camera_option(c): c[0] for c in cameras}
        self._engine: Optional[MotionEngine] = None
        self._ctk_image: Optional[ctk.CTkImage] = None  # prevent GC
        self._running = False

        self._build_layout()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.bind("<space>", lambda _: self._toggle_pause())
        self.bind("<Escape>", lambda _: self._on_close())

    # =======================================================================
    # Layout
    # =======================================================================

    def _build_layout(self) -> None:
        # Main grid: video left, controls right
        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=1, minsize=340)
        self.grid_rowconfigure(0, weight=1)

        # ----- Left: video area -------------------------------------------
        self._video_frame = ctk.CTkFrame(self, fg_color=_C["card"], corner_radius=16,
                                         border_width=1, border_color=_C["card_border"])
        self._video_frame.grid(row=0, column=0, padx=(16, 8), pady=16, sticky="nsew")
        self._video_frame.grid_rowconfigure(0, weight=1)
        self._video_frame.grid_columnconfigure(0, weight=1)

        self._video_label = ctk.CTkLabel(self._video_frame, text="📷 选择摄像头并点击开始",
                                         font=ctk.CTkFont(size=20),
                                         text_color=_C["text_dim"])
        self._video_label.grid(row=0, column=0, sticky="nsew")

        # ----- Right: control panel ----------------------------------------
        self._panel = ctk.CTkScrollableFrame(self, fg_color=_C["bg"], corner_radius=0,
                                             label_text="", scrollbar_button_color=_C["card_border"])
        self._panel.grid(row=0, column=1, padx=(8, 16), pady=16, sticky="nsew")
        self._panel.grid_columnconfigure(0, weight=1)

        row = 0

        # -- Title
        ctk.CTkLabel(self._panel, text="⚡ 控制面板",
                      font=ctk.CTkFont(size=22, weight="bold"),
                      text_color=_C["accent"]).grid(row=row, column=0, pady=(4, 16), sticky="w")
        row += 1

        # -- Camera selector
        row = self._add_section(row, "📹 摄像头")
        cam_options = list(self._camera_map.keys()) or ["无摄像头"]
        self._cam_var = ctk.StringVar(value=cam_options[0] if cam_options else "")
        self._cam_combo = ctk.CTkComboBox(
            self._panel, variable=self._cam_var, values=cam_options,
            state="readonly", width=280,
            fg_color=_C["card"], border_color=_C["card_border"],
            button_color=_C["accent"], button_hover_color=_C["accent_hover"],
            dropdown_fg_color=_C["card"], dropdown_hover_color=_C["card_border"])
        self._cam_combo.grid(row=row, column=0, pady=(0, 12), sticky="ew")
        row += 1

        # -- Exercise selector
        row = self._add_section(row, "🏋️ 运动项目")
        ex_labels = [EXERCISE_LABELS[e] for e in EXERCISE_CHOICES]
        self._ex_var = ctk.StringVar(value=ex_labels[0])
        self._ex_combo = ctk.CTkComboBox(
            self._panel, variable=self._ex_var, values=ex_labels,
            state="readonly", width=280, command=self._on_exercise_change,
            fg_color=_C["card"], border_color=_C["card_border"],
            button_color=_C["accent"], button_hover_color=_C["accent_hover"],
            dropdown_fg_color=_C["card"], dropdown_hover_color=_C["card_border"])
        self._ex_combo.grid(row=row, column=0, pady=(0, 12), sticky="ew")
        row += 1

        # -- Big counter display
        self._count_card = ctk.CTkFrame(self._panel, fg_color=_C["card"], corner_radius=16,
                                        border_width=1, border_color=_C["card_border"])
        self._count_card.grid(row=row, column=0, pady=(4, 12), sticky="ew", ipady=10)
        self._count_card.grid_columnconfigure(0, weight=1)
        self._count_card.grid_columnconfigure(1, weight=1)

        self._count_label = ctk.CTkLabel(self._count_card, text="0",
                                         font=ctk.CTkFont(size=56, weight="bold"),
                                         text_color=_C["accent"])
        self._count_label.grid(row=0, column=0, padx=16, pady=(8, 0))

        self._phase_label = ctk.CTkLabel(self._count_card, text="UP",
                                         font=ctk.CTkFont(size=28, weight="bold"),
                                         text_color=_C["up_phase"])
        self._phase_label.grid(row=0, column=1, padx=16, pady=(8, 0))

        self._angle_label = ctk.CTkLabel(self._count_card, text="角度: —",
                                         font=ctk.CTkFont(size=14),
                                         text_color=_C["text_dim"])
        self._angle_label.grid(row=1, column=0, columnspan=2, pady=(0, 8))
        row += 1

        # -- FPS
        self._fps_label = ctk.CTkLabel(self._panel, text="FPS: —",
                                       font=ctk.CTkFont(size=13),
                                       text_color=_C["text_dim"])
        self._fps_label.grid(row=row, column=0, sticky="w", pady=(0, 8))
        row += 1

        # -- Threshold sliders
        row = self._add_section(row, "🎚️ 阈值调节（实时生效）")

        self._down_var = tk.DoubleVar(value=95.0)
        self._down_label = ctk.CTkLabel(self._panel, text="Down ≤ 95.0°",
                                        font=ctk.CTkFont(size=13), text_color=_C["text"])
        self._down_label.grid(row=row, column=0, sticky="w")
        row += 1
        self._down_slider = ctk.CTkSlider(
            self._panel, from_=40, to=180, variable=self._down_var,
            command=self._on_threshold_change, number_of_steps=140,
            progress_color=_C["blue"], button_color=_C["accent"],
            button_hover_color=_C["accent_hover"])
        self._down_slider.grid(row=row, column=0, sticky="ew", pady=(0, 8))
        row += 1

        self._up_var = tk.DoubleVar(value=160.0)
        self._up_label = ctk.CTkLabel(self._panel, text="Up ≥ 160.0°",
                                      font=ctk.CTkFont(size=13), text_color=_C["text"])
        self._up_label.grid(row=row, column=0, sticky="w")
        row += 1
        self._up_slider = ctk.CTkSlider(
            self._panel, from_=40, to=180, variable=self._up_var,
            command=self._on_threshold_change, number_of_steps=140,
            progress_color=_C["blue"], button_color=_C["accent"],
            button_hover_color=_C["accent_hover"])
        self._up_slider.grid(row=row, column=0, sticky="ew", pady=(0, 12))
        row += 1

        # -- Voice every
        row = self._add_section(row, "🔊 语音播报")
        self._voice_var = tk.StringVar(value="0")
        voice_frame = ctk.CTkFrame(self._panel, fg_color="transparent")
        voice_frame.grid(row=row, column=0, sticky="ew", pady=(0, 12))
        voice_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(voice_frame, text="每 N 次播报:", font=ctk.CTkFont(size=13),
                      text_color=_C["text"]).grid(row=0, column=0, padx=(0, 8))
        self._voice_entry = ctk.CTkEntry(voice_frame, textvariable=self._voice_var,
                                         width=60, fg_color=_C["card"],
                                         border_color=_C["card_border"])
        self._voice_entry.grid(row=0, column=1, sticky="w")
        self._voice_entry.bind("<Return>", lambda _: self._on_voice_change())
        self._voice_entry.bind("<FocusOut>", lambda _: self._on_voice_change())
        ctk.CTkLabel(voice_frame, text="(0 = 关闭)", font=ctk.CTkFont(size=11),
                      text_color=_C["text_dim"]).grid(row=0, column=2, padx=(8, 0))
        row += 1

        # -- Action buttons
        row = self._add_section(row, "")
        btn_frame = ctk.CTkFrame(self._panel, fg_color="transparent")
        btn_frame.grid(row=row, column=0, sticky="ew", pady=(0, 8))
        btn_frame.grid_columnconfigure((0, 1), weight=1)

        self._start_btn = ctk.CTkButton(
            btn_frame, text="▶ 开始", command=self._on_start,
            font=ctk.CTkFont(size=15, weight="bold"), height=44,
            fg_color=_C["green"], hover_color="#00c853", text_color="#1a1a2e",
            corner_radius=12)
        self._start_btn.grid(row=0, column=0, padx=(0, 4), sticky="ew")

        self._pause_btn = ctk.CTkButton(
            btn_frame, text="⏸ 暂停", command=self._toggle_pause,
            font=ctk.CTkFont(size=15, weight="bold"), height=44,
            fg_color=_C["yellow"], hover_color="#ffab00", text_color="#1a1a2e",
            corner_radius=12, state="disabled")
        self._pause_btn.grid(row=0, column=1, padx=(4, 0), sticky="ew")
        row += 1

        btn_frame2 = ctk.CTkFrame(self._panel, fg_color="transparent")
        btn_frame2.grid(row=row, column=0, sticky="ew", pady=(0, 8))
        btn_frame2.grid_columnconfigure((0, 1), weight=1)

        self._reset_btn = ctk.CTkButton(
            btn_frame2, text="🔄 重置", command=self._on_reset,
            font=ctk.CTkFont(size=14), height=40,
            fg_color=_C["card"], hover_color=_C["card_border"],
            border_width=1, border_color=_C["card_border"],
            text_color=_C["text"], corner_radius=12)
        self._reset_btn.grid(row=0, column=0, padx=(0, 4), sticky="ew")

        self._quit_btn = ctk.CTkButton(
            btn_frame2, text="✖ 退出", command=self._on_close,
            font=ctk.CTkFont(size=14), height=40,
            fg_color=_C["accent"], hover_color=_C["accent_hover"],
            text_color="#ffffff", corner_radius=12)
        self._quit_btn.grid(row=0, column=1, padx=(4, 0), sticky="ew")
        row += 1

        # -- Keyboard hints
        ctk.CTkLabel(self._panel, text="快捷键: Space 暂停/继续 · Esc 退出",
                      font=ctk.CTkFont(size=11), text_color=_C["text_dim"]).grid(
            row=row, column=0, pady=(8, 4), sticky="w")

    def _add_section(self, row: int, title: str) -> int:
        if title:
            ctk.CTkLabel(self._panel, text=title,
                          font=ctk.CTkFont(size=14, weight="bold"),
                          text_color=_C["text"]).grid(row=row, column=0, pady=(8, 4), sticky="w")
        return row + 1

    # =======================================================================
    # Event handlers
    # =======================================================================

    def _current_exercise_key(self) -> str:
        label = self._ex_var.get()
        for key, val in EXERCISE_LABELS.items():
            if val == label:
                return key
        return "squat"

    def _on_exercise_change(self, _=None) -> None:
        ex = self._current_exercise_key()
        down, up = DEFAULT_THRESHOLDS[ex]
        self._down_var.set(down)
        self._up_var.set(up)
        self._down_label.configure(text=f"Down ≤ {down:.1f}°")
        self._up_label.configure(text=f"Up ≥ {up:.1f}°")
        if self._engine:
            self._engine.switch_exercise(ex)
            self._engine.update_thresholds(down, up)

    def _on_threshold_change(self, _=None) -> None:
        down = round(self._down_var.get(), 1)
        up = round(self._up_var.get(), 1)
        self._down_label.configure(text=f"Down ≤ {down:.1f}°")
        self._up_label.configure(text=f"Up ≥ {up:.1f}°")
        if self._engine and up > down:
            self._engine.update_thresholds(down, up)

    def _on_voice_change(self) -> None:
        raw = self._voice_var.get().strip()
        try:
            val = int(raw) if raw else 0
        except ValueError:
            val = 0
        if self._engine:
            self._engine.update_voice_every(max(0, val))

    def _on_start(self) -> None:
        if self._running:
            return

        cam_key = self._cam_var.get()
        cam_index = self._camera_map.get(cam_key, 0)
        ex = self._current_exercise_key()
        down = round(self._down_var.get(), 1)
        up = round(self._up_var.get(), 1)
        raw_voice = self._voice_var.get().strip()
        try:
            voice_every = max(0, int(raw_voice)) if raw_voice else 0
        except ValueError:
            voice_every = 0

        if up <= down:
            from tkinter import messagebox
            messagebox.showerror("阈值错误", "Up Angle 必须大于 Down Angle")
            return

        config = RunConfig(
            camera_index=cam_index,
            exercise=ex,
            down_angle=down,
            up_angle=up,
            voice_every=voice_every,
        )

        self._engine = MotionEngine(config)
        self._engine.start()
        self._running = True

        self._start_btn.configure(state="disabled", text="● 运行中")
        self._pause_btn.configure(state="normal")
        self._cam_combo.configure(state="disabled")

        self._refresh_loop()

    def _toggle_pause(self) -> None:
        if not self._engine or not self._running:
            return
        paused = self._engine.toggle_pause()
        if paused:
            self._pause_btn.configure(text="▶ 继续", fg_color=_C["green"],
                                      hover_color="#00c853")
        else:
            self._pause_btn.configure(text="⏸ 暂停", fg_color=_C["yellow"],
                                      hover_color="#ffab00")

    def _on_reset(self) -> None:
        if self._engine:
            self._engine.reset_count()

    def _on_close(self) -> None:
        if self._engine:
            self._engine.stop()
        self.destroy()

    # =======================================================================
    # Refresh loop
    # =======================================================================

    def _refresh_loop(self) -> None:
        if not self._running or not self._engine:
            return

        snap = self._engine.get_snapshot()

        # -- Update video
        if snap.frame is not None:
            frame_rgb = cv2.cvtColor(snap.frame, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(frame_rgb)

            # Overlay pause badge
            if snap.paused:
                draw = ImageDraw.Draw(pil_img)
                pw, ph = pil_img.size
                badge_text = "PAUSED"
                try:
                    font = ImageFont.truetype("arial.ttf", 40)
                except Exception:
                    font = ImageFont.load_default()
                bbox = draw.textbbox((0, 0), badge_text, font=font)
                tw = bbox[2] - bbox[0]
                th = bbox[3] - bbox[1]
                x = (pw - tw) // 2
                y = (ph - th) // 2
                pad = 16
                draw.rounded_rectangle(
                    [x - pad, y - pad, x + tw + pad, y + th + pad],
                    radius=14, fill=(0, 0, 0, 180))
                draw.text((x, y), badge_text, fill=(255, 214, 0), font=font)

            # Fit to label size
            lw = self._video_label.winfo_width()
            lh = self._video_label.winfo_height()
            if lw > 10 and lh > 10:
                pil_img = self._fit_image(pil_img, lw, lh)

            # Use CTkImage for proper HighDPI scaling
            self._ctk_image = ctk.CTkImage(light_image=pil_img, dark_image=pil_img,
                                           size=pil_img.size)
            self._video_label.configure(image=self._ctk_image, text="")

        # -- Update stats
        cs = snap.counter
        self._count_label.configure(text=str(cs.count))
        self._phase_label.configure(
            text=cs.phase,
            text_color=_C["up_phase"] if cs.phase == "UP" else _C["down_phase"])

        if cs.smoothed_angle is not None:
            metric = METRIC_LABELS.get(self._current_exercise_key(), "角度")
            self._angle_label.configure(text=f"{metric}: {cs.smoothed_angle:.1f}°")
        else:
            self._angle_label.configure(text="角度: —")

        self._fps_label.configure(text=f"FPS: {snap.fps:.0f}")

        # Schedule next refresh
        self.after(REFRESH_MS, self._refresh_loop)

    @staticmethod
    def _fit_image(img: Image.Image, max_w: int, max_h: int) -> Image.Image:
        w, h = img.size
        scale = min(max_w / w, max_h / h, 1.0)
        if scale < 1.0:
            new_w = max(1, int(w * scale))
            new_h = max(1, int(h * scale))
            img = img.resize((new_w, new_h), Image.LANCZOS)
        return img


# ---------------------------------------------------------------------------
# Public launcher
# ---------------------------------------------------------------------------

def launch_ui(cameras: list[CameraInfo] | None = None) -> None:
    """Create and run the modern UI."""
    if cameras is None:
        cameras = list_available_cameras()
    app = MotionCounterApp(cameras)
    app.mainloop()
