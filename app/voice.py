"""Background thread voice announcer using pyttsx3."""

from __future__ import annotations

import queue
import threading


class VoiceAnnouncer:
    """Speaks rep counts in a background thread.  Set *every=0* to disable."""

    def __init__(self, every: int = 0) -> None:
        self.every = max(0, every)
        self.enabled = self.every > 0
        self._queue: queue.Queue[str | None] = queue.Queue()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._pyttsx3 = None

        if not self.enabled:
            return
        try:
            import pyttsx3
            self._pyttsx3 = pyttsx3
        except Exception as exc:
            print(f"Voice disabled: {exc}")
            self.enabled = False
            return

        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()

    # ---- internal ---------------------------------------------------------

    def _worker(self) -> None:
        try:
            engine = self._pyttsx3.init()
        except Exception as exc:
            print(f"Voice disabled: cannot init TTS ({exc})")
            self.enabled = False
            return

        while not self._stop.is_set():
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

    # ---- public -----------------------------------------------------------

    def maybe_announce(self, count: int) -> None:
        if not self.enabled or self.every <= 0 or count <= 0:
            return
        if count % self.every != 0:
            return
        self._queue.put(f"{count}")

    def set_every(self, every: int) -> None:
        self.every = max(0, every)

    def close(self) -> None:
        if not self.enabled:
            return
        self._stop.set()
        self._queue.put(None)
        if self._thread:
            self._thread.join(timeout=1.0)
